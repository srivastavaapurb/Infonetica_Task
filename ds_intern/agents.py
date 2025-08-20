import json
import random
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .client import AzureOpenAIClient
from .prompts import AGENT_A_V0, AGENT_A_V1, AGENT_A_V2, AGENT_J_SYSTEM
from .tools import ToolRegistry


@dataclass
class TurnRecord:
	role: str
	content: str
	latency_ms: float
	tags: Dict[str, Any]


class AgentA:
	def __init__(self, client: AzureOpenAIClient, version: str = "v0") -> None:
		self.client = client
		self.prompt = {"v0": AGENT_A_V0, "v1": AGENT_A_V1, "v2": AGENT_A_V2}[version]
		self.version = version

	def respond(self, conversation: List[Dict[str, str]], max_tokens: int = 200) -> Tuple[str, Dict[str, Any], float]:
		messages = [{"role": "system", "content": self.prompt.content}] + conversation
		text, usage, latency = self.client.chat(messages=messages, max_tokens=max_tokens, temperature=0.2)
		return text, usage, latency


class AgentJ:
	"""Proctor agent: generates user messages and evaluates Agent A adherence."""

	INTENTS = [
		"refund_status",
		"delivery_delay",
		"product_damage",
		"payment_failure",
		"store_locator",
		"delivery_instructions_update",
		"product_availability",
		"warranty_inquiry",
		"return_window_expired",
		"refund_policy",
		"delivery_timelines",
		"offers_discounts",
	]

	LANGS = ["en", "hi", "hinglish"]

	def __init__(self, rng: Optional[random.Random] = None) -> None:
		self.rng = rng or random.Random(42)

	def start_message(self) -> str:
		return "Hi, how can I check my refund status?"

	def generate_turn(self, last_intent: Optional[str] = None) -> Tuple[str, str]:
		intent = last_intent or self.rng.choice(self.INTENTS)
		lang = self.rng.choice(self.LANGS)
		msg = self._intent_to_message(intent, lang)
		return msg, intent

	def maybe_end(self) -> Optional[str]:
		if self.rng.random() < 0.3:
			return self.rng.choice([
				"thanks, bye",
				"no, that's all",
				"nahi, bas itna hi",
				"theek hai, bye",
			])
		return None

	def _intent_to_message(self, intent: str, lang: str) -> str:
		if intent == "refund_status":
			return {"en": "I want my refund status. Ticket is 102938.", "hi": "Mera refund status kya hai? Ticket 102938.", "hinglish": "Refund status chahiye, ticket 102938."}[lang]
		if intent == "delivery_delay":
			return {"en": "Order 12345 is delayed, what's the ETA?", "hi": "Order 12345 late hai, kab aayega?", "hinglish": "Order 12345 delay hai, ETA kya hai?"}[lang]
		if intent == "product_damage":
			return {"en": "My item from order 888 was damaged.", "hi": "Order 888 ka item damaged aaya.", "hinglish": "Order 888 ka product toot gaya tha."}[lang]
		if intent == "payment_failure":
			return {"en": "Payment failed, txn 777.", "hi": "Payment fail ho gaya, txn 777.", "hinglish": "Payment failure hua, transaction 777."}[lang]
		if intent == "store_locator":
			return {"en": "Nearest store in Bangalore? Area Koramangala.", "hi": "Bangalore mein Koramangala ke paas store?", "hinglish": "Bangalore Koramangala ke paas store kaha hai?"}[lang]
		if intent == "delivery_instructions_update":
			return {"en": "Update delivery instructions for order 222: leave at gate.", "hi": "Order 222 ke liye nayi instruction: gate par chhod dena.", "hinglish": "Order 222 instructions update karo: gate pe rakh dena."}[lang]
		if intent == "product_availability":
			return {"en": "Is AirPro Mixer in stock?", "hi": "AirPro Mixer stock me hai?", "hinglish": "AirPro Mixer available hai?"}[lang]
		if intent == "warranty_inquiry":
			return {"en": "Does AirPro Mixer have warranty?", "hi": "AirPro Mixer me warranty hai?", "hinglish": "AirPro Mixer ki warranty?"}[lang]
		if intent == "return_window_expired":
			return {"en": "My return window is over, what can I do?", "hi": "Return window khatam ho gaya, ab kya?", "hinglish": "Return period over, help?"}[lang]
		if intent == "refund_policy":
			return {"en": "What is your refund policy?", "hi": "Refund policy kya hai?", "hinglish": "Refund policy batao."}[lang]
		if intent == "delivery_timelines":
			return {"en": "What are your standard delivery timelines?", "hi": "Delivery timelines kya hoti hain?", "hinglish": "Delivery kitne din me aati hai?"}[lang]
		if intent == "offers_discounts":
			return {"en": "Any offers or discounts now?", "hi": "Abhi koi offer ya discount?", "hinglish": "Koi discount chal raha hai?"}[lang]
		return "Hello"

	def evaluate(self, user_msg: str, agent_reply: str) -> Dict[str, Any]:
		"""Simple rule-based evaluation of adherence."""
		violations = []
		# Language check: simplistic heuristics
		is_hi = any(tok in user_msg for tok in ["hai", "kya", "theek", "nahi", "aayega", "mein"]) or re.search(r"[\u0900-\u097F]", user_msg)
		is_en = re.search(r"[A-Za-z]", user_msg) is not None and not is_hi

		if is_hi and re.search(r"[\u0900-\u097F]", agent_reply) is None and not any(x in agent_reply.lower() for x in ["hai", "kya", "theek", "nahi", "aayega", "mein", "aap", "aapka"]):
			violations.append("wrong_language")

		if agent_reply.strip().startswith("<END_CALL>"):
			violations.append("bad_end_call")
		if agent_reply.count("<END_CALL>") > 1:
			violations.append("bad_end_call")

		tool_calls = re.findall(r"<CALL_TOOL=([a-zA-Z_]+)>?\s*(\{.*?\})", agent_reply)
		if len(tool_calls) > 1:
			violations.append("extra_tool_calls")

		verbosity = len(agent_reply.split())
		over_verbosity = verbosity > 80
		if over_verbosity:
			violations.append("over_verbosity")

		# Offer more help presence
		offer_help = any(kw in agent_reply.lower() for kw in ["anything else", "more help", "aur kuch", "kuch aur", "help you with"])
		# If reply appears to close without offering more help
		if ("bye" in agent_reply.lower() or "thank you" in agent_reply.lower()) and not offer_help and "<END_CALL>" not in agent_reply:
			violations.append("missing_offer_help")

		# Heuristic hallucination: claims of action completion without IDs present
		if any(p in agent_reply.lower() for p in ["updated", "processed", "approved", "located"]):
			if not any(x in user_msg.lower() for x in ["ticket", "order", "txn", "transaction", "area", "koramangala", "bangalore"]):
				violations.append("hallucination")

		return {
			"violations": violations,
			"num_tool_calls": len(tool_calls),
			"verbosity": verbosity,
		}