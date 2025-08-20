from typing import Any, Dict, Optional


class ToolExecutionError(Exception):
	pass


class ToolRegistry:
	"""Holds available tools and executes them. Replace mocks with real integrations when needed."""

	def __init__(self) -> None:
		self._tools = {}

	def register(self, action: str, handler) -> None:
		self._tools[action] = handler

	def has(self, action: str) -> bool:
		return action in self._tools

	def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
		if action not in self._tools:
			raise ToolExecutionError(f"Unknown tool action: {action}")
		return self._tools[action](params)


# Mock tool implementations

def mock_refund_status(params: Dict[str, Any]) -> Dict[str, Any]:
	return {"status": "approved", "eta_days": 2, "ticket_id": params.get("ticket_id")}

def mock_delivery_eta(params: Dict[str, Any]) -> Dict[str, Any]:
	return {"order_id": params.get("order_id"), "eta": "2-3 days"}

def mock_store_locator(params: Dict[str, Any]) -> Dict[str, Any]:
	return {"city": params.get("city"), "area": params.get("area"), "address": "5th Block, Koramangala", "hours": "10am–9pm"}

def mock_update_instructions(params: Dict[str, Any]) -> Dict[str, Any]:
	return {"order_id": params.get("order_id"), "updated": True, "instruction": params.get("instruction")}

def build_default_registry() -> ToolRegistry:
	registry = ToolRegistry()
	registry.register("refund_status", mock_refund_status)
	registry.register("delivery_eta", mock_delivery_eta)
	registry.register("store_locator", mock_store_locator)
	registry.register("update_instructions", mock_update_instructions)
	return registry