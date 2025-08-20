import json
import os
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

import pandas as pd

from .agents import AgentA, AgentJ, TurnRecord
from .client import AzureOpenAIClient
from .tools import build_default_registry
import re


@dataclass
class ConversationLog:
	conversation_id: int
	agent_a_version: str
	turns: List[TurnRecord]
	per_metrics: Dict[str, Any]


class ConversationSimulator:
	def __init__(self, client: AzureOpenAIClient, agent_a_version: str = "v0") -> None:
		self.client = client
		self.agent_a = AgentA(client, version=agent_a_version)
		self.agent_j = AgentJ()
		self.tools = build_default_registry()

	def run_one(self, max_turns: int = 8, conversation_id: int = 0) -> ConversationLog:
		conversation: List[Dict[str, str]] = []
		turns: List[TurnRecord] = []
		user_msg = self.agent_j.start_message()

		conversation.append({"role": "user", "content": user_msg})
		turns.append(TurnRecord(role="user", content=user_msg, latency_ms=0.0, tags={"intent": "refund_status"}))

		reply, usage, latency = self.agent_a.respond(conversation)
		tags = self._evaluate_and_execute_tools(user_msg, reply)
		turns.append(TurnRecord(role="assistant", content=reply, latency_ms=latency * 1000.0, tags=tags))
		self._maybe_tool_followup(conversation, turns, user_msg, reply)

		intent = None
		for _ in range(max_turns - 1):
			maybe_end = self.agent_j.maybe_end()
			if maybe_end:
				conversation.append({"role": "user", "content": maybe_end})
				turns.append(TurnRecord(role="user", content=maybe_end, latency_ms=0.0, tags={"end": True}))
				reply, usage, latency = self.agent_a.respond(conversation)
				tags = self._evaluate_and_execute_tools(maybe_end, reply)
				turns.append(TurnRecord(role="assistant", content=reply, latency_ms=latency * 1000.0, tags=tags))
				self._maybe_tool_followup(conversation, turns, maybe_end, reply)
				break

			user_msg, intent = self.agent_j.generate_turn(intent)
			conversation.append({"role": "user", "content": user_msg})
			turns.append(TurnRecord(role="user", content=user_msg, latency_ms=0.0, tags={"intent": intent}))

			reply, usage, latency = self.agent_a.respond(conversation)
			tags = self._evaluate_and_execute_tools(user_msg, reply)
			turns.append(TurnRecord(role="assistant", content=reply, latency_ms=latency * 1000.0, tags=tags))
			self._maybe_tool_followup(conversation, turns, user_msg, reply)

		per_metrics = self._compute_metrics(turns)
		return ConversationLog(conversation_id=conversation_id, agent_a_version=self.agent_a.version, turns=turns, per_metrics=per_metrics)

	def run_many(self, n: int = 20, max_turns: int = 8, version: str = "v0") -> List[ConversationLog]:
		self.agent_a = AgentA(self.client, version=version)
		logs: List[ConversationLog] = []
		for i in range(n):
			logs.append(self.run_one(max_turns=max_turns, conversation_id=i))
		return logs

	def _compute_metrics(self, turns: List[TurnRecord]) -> Dict[str, Any]:
		assistant_turns = [t for t in turns if t.role == "assistant"]
		latencies = [t.latency_ms for t in assistant_turns]
		avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
		total_tool_calls = sum(t.tags.get("num_tool_calls", 0) for t in assistant_turns)
		total_violations = sum(len(t.tags.get("violations", [])) for t in assistant_turns)
		avg_verbosity = sum(t.tags.get("verbosity", 0) for t in assistant_turns) / len(assistant_turns) if assistant_turns else 0

		# Heuristic flow adherence
		first_assistant = assistant_turns[0].content.lower() if assistant_turns else ""
		greet_present = any(g in first_assistant for g in ["hi", "hello", "namaste", "hey"])
		gather_present = any(
			any(kw in t.content.lower() for kw in ["ticket", "order", "transaction", "area", "id", "instruction", "provide", "tell me"])
			for t in assistant_turns
		)
		tool_flow_ok = any(t.tags.get("tool_result_followup", False) for t in assistant_turns) or total_tool_calls == 0
		offer_help_present = any(
			any(kw in t.content.lower() for kw in ["anything else", "more help", "aur kuch", "kuch aur", "help you with"])
			for t in assistant_turns
		)
		flow_adherence_score = sum([greet_present, gather_present, tool_flow_ok, offer_help_present]) / 4.0

		tool_call_correct_rate = _safe_div(
			 sum(1 for t in assistant_turns if t.tags.get("tool_call_correct", 0) == 1),
			 max(1, sum(t.tags.get("num_tool_calls", 0) for t in assistant_turns)),
		)

		return {
			"avg_latency_ms": avg_latency,
			"total_tool_calls": total_tool_calls,
			"total_violations": total_violations,
			"avg_verbosity": avg_verbosity,
			"flow_adherence": flow_adherence_score,
			"tool_call_correct_rate": tool_call_correct_rate,
		}

	def _evaluate_and_execute_tools(self, user_msg: str, agent_reply: str) -> Dict[str, Any]:
		"""Parse tool calls in reply, execute if any, and augment evaluation tags.

		We also append a synthetic 'assistant' result to the prior message content in the conversation logic by
		returning enriched tags only; actual conversation text is left as produced to avoid feedback leakage.
		"""
		# Base evaluation
		tags = self.agent_j.evaluate(user_msg, agent_reply)
		# Detect tool call pattern
		matches = re.findall(r"<CALL_TOOL=([a-zA-Z_]+)>?\s*(\{.*?\})", agent_reply)
		if matches:
			# Take only the first tool call per turn by policy
			action, json_payload = matches[0]
			params: Dict[str, Any] = {}
			try:
				params = json.loads(json_payload)
			except Exception:
				tags.setdefault("violations", []).append("bad_tool_json")
				return {**tags, "num_tool_calls": len(matches)}
			# Execute if tool exists
			if self.tools.has(action):
				try:
					_ = self.tools.execute(action, params)
					# Consider tool-call-correctness as 1 when execution succeeds
					tags["tool_call_correct"] = 1
				except Exception:
					tags.setdefault("violations", []).append("tool_exec_error")
					tags["tool_call_correct"] = 0
			else:
				tags.setdefault("violations", []).append("unknown_tool")
				tags["tool_call_correct"] = 0
			# Ensure num_tool_calls is counted
			tags["num_tool_calls"] = len(matches)
		return tags

	def _parse_tool_call(self, reply: str) -> Optional[tuple]:
		matches = re.findall(r"<CALL_TOOL=([a-zA-Z_]+)>?\s*(\{.*?\})", reply)
		if not matches:
			return None
		action, payload = matches[0]
		try:
			params = json.loads(payload)
		except Exception:
			params = {}
		return action, params

	def _execute_tool_safe(self, action: str, params: Dict[str, Any], tags: Dict[str, Any]) -> Dict[str, Any]:
		try:
			result = self.tools.execute(action, params)
			return {"ok": True, **result}
		except Exception as exc:
			tags.setdefault("violations", []).append("tool_exec_error")
			return {"ok": False, "error": str(exc)}

	def _maybe_tool_followup(self, conversation: List[Dict[str, str]], turns: List[TurnRecord], user_msg: str, reply: str) -> None:
		tool_info = self._parse_tool_call(reply)
		if tool_info is None:
			return
		action, params = tool_info
		tool_result = self._execute_tool_safe(action, params, {})
		conversation.append({"role": "tool", "content": json.dumps({"action": action, "result": tool_result}, ensure_ascii=False)})
		followup_reply, usage, latency2 = self.agent_a.respond(conversation)
		followup_tags = self._evaluate_and_execute_tools(user_msg, followup_reply)
		followup_tags["tool_result_followup"] = True
		turns.append(TurnRecord(role="assistant", content=followup_reply, latency_ms=latency2 * 1000.0, tags=followup_tags))


def _safe_div(a: float, b: float) -> float:
	return a / b if b else 0.0


def export_logs(logs: List[ConversationLog], out_dir: str) -> None:
	os.makedirs(out_dir, exist_ok=True)
	# JSON per conversation
	for log in logs:
		with open(os.path.join(out_dir, f"conversation_{log.conversation_id}.json"), "w", encoding="utf-8") as f:
			json.dump({
				"conversation_id": log.conversation_id,
				"agent_a_version": log.agent_a_version,
				"turns": [asdict(t) for t in log.turns],
				"metrics": log.per_metrics,
			}, f, ensure_ascii=False, indent=2)

	# CSV summary
	rows = []
	for log in logs:
		rows.append({"conversation_id": log.conversation_id, **log.per_metrics, "agent_a_version": log.agent_a_version})
	pd.DataFrame(rows).to_csv(os.path.join(out_dir, "summary.csv"), index=False)