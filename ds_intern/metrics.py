from collections import Counter
from typing import Any, Dict, List

from .simulator import ConversationLog


def aggregate_metrics(logs: List[ConversationLog]) -> Dict[str, Any]:
	avg_latency = sum(l.per_metrics.get("avg_latency_ms", 0.0) for l in logs) / len(logs) if logs else 0.0
	total_tool_calls = sum(l.per_metrics.get("total_tool_calls", 0) for l in logs)
	total_violations = sum(l.per_metrics.get("total_violations", 0) for l in logs)
	avg_verbosity = sum(l.per_metrics.get("avg_verbosity", 0.0) for l in logs) / len(logs) if logs else 0.0
	return {
		"avg_latency_ms": avg_latency,
		"total_tool_calls": total_tool_calls,
		"total_violations": total_violations,
		"avg_verbosity": avg_verbosity,
	}


def top_failure_modes(logs: List[ConversationLog], top_k: int = 5) -> List:
	counter = Counter()
	for l in logs:
		for t in l.turns:
			if t.role == "assistant":
				for v in t.tags.get("violations", []):
					counter[v] += 1
	return counter.most_common(top_k)