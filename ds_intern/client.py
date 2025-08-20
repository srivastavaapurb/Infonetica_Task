import os
import time
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


class AzureOpenAIError(Exception):
	pass


class AzureOpenAIClient:
	"""Minimal Azure OpenAI Chat Completions client.

	- Reads configuration from environment variables by default.
	- Provides retry with exponential backoff for transient HTTP errors.
	- Returns response text, usage, and latency.
	"""

	def __init__(
		self,
		endpoint: Optional[str] = None,
		api_key: Optional[str] = None,
		deployment: Optional[str] = None,
		api_version: Optional[str] = None,
		timeout_seconds: Optional[int] = None,
	) -> None:
		load_dotenv(override=False)
		self.endpoint = endpoint or os.getenv("AZURE_OPENAI_ENDPOINT", "https://reasearch-interns.openai.azure.com")
		self.api_key = api_key or os.getenv("AZURE_OPENAI_API_KEY", "")
		self.deployment = deployment or os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
		self.api_version = api_version or os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
		self.timeout_seconds = int(timeout_seconds or os.getenv("REQUEST_TIMEOUT_SECONDS", "60"))

		if not self.api_key:
			raise AzureOpenAIError("AZURE_OPENAI_API_KEY is not set. Put it in .env or environment.")

		self._base_url = f"{self.endpoint}/openai/deployments/{self.deployment}/chat/completions?api-version={self.api_version}"

	@retry(
		retry=retry_if_exception_type((requests.RequestException, AzureOpenAIError)),
		wait=wait_exponential(multiplier=1, min=1, max=8),
		stop=stop_after_attempt(3),
		reraise=True,
	)
	def chat(
		self,
		messages: List[Dict[str, str]],
		max_tokens: int = 256,
		temperature: float = 0.2,
		top_p: float = 1.0,
	) -> Tuple[str, Dict[str, Any], float]:
		"""Send a chat completion request.

		Returns: (text, usage, latency_seconds)
		"""
		headers = {
			"Content-Type": "application/json",
			"api-key": self.api_key,
		}
		payload = {
			"messages": messages,
			"max_tokens": max_tokens,
			"temperature": temperature,
			"top_p": top_p,
		}
		start = time.perf_counter()
		resp = requests.post(self._base_url, headers=headers, json=payload, timeout=self.timeout_seconds)
		latency = time.perf_counter() - start
		if resp.status_code != 200:
			raise AzureOpenAIError(f"HTTP {resp.status_code}: {resp.text}")
		data = resp.json()
		try:
			text = data["choices"][0]["message"]["content"].strip()
			usage = data.get("usage", {})
		except Exception as exc:
			raise AzureOpenAIError(f"Malformed response: {data}") from exc
		return text, usage, latency