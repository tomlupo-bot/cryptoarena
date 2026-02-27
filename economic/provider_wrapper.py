"""
TrackedLLMProvider — Wraps AI-Trader's LangChain ChatOpenAI to intercept
token usage and feed it into the EconomicTracker.

Works with both LangChain (ChatOpenAI) and LiteLLM response formats.
Supports OpenRouter's direct cost reporting via response headers.
"""

from __future__ import annotations

from typing import Any, Optional

from economic.tracker import EconomicTracker


class TrackedLLMProvider:
    """
    Transparent wrapper around a LangChain ChatOpenAI model that intercepts
    every invoke/ainvoke response to extract token usage and deduct cost
    from the team's trading capital via EconomicTracker.
    """

    def __init__(self, model: Any, economic_tracker: EconomicTracker):
        self._model = model
        self.tracker = economic_tracker

    def bind_tools(self, tools, **kwargs):
        """Pass through to underlying model's bind_tools."""
        bound = self._model.bind_tools(tools, **kwargs)
        # Return a new wrapper around the bound model
        return TrackedLLMProvider(bound, self.tracker)

    async def ainvoke(self, messages, **kwargs):
        response = await self._model.ainvoke(messages, **kwargs)
        self._track_response(response)
        return response

    def invoke(self, messages, **kwargs):
        response = self._model.invoke(messages, **kwargs)
        self._track_response(response)
        return response

    def _track_response(self, response: Any) -> float:
        """Extract token usage from LangChain response and record cost."""
        input_tokens = 0
        output_tokens = 0
        cost_override = None

        # Try response_metadata (raw API response)
        raw = getattr(response, "response_metadata", {}).get("token_usage", {})
        if raw:
            input_tokens = raw.get("prompt_tokens", 0)
            output_tokens = raw.get("completion_tokens", 0)
            # OpenRouter direct cost
            if "cost" in raw:
                cost_override = raw["cost"]
        else:
            # Fallback to LangChain's normalized usage_metadata
            usage = getattr(response, "usage_metadata", {})
            if usage:
                input_tokens = usage.get("input_tokens", 0)
                output_tokens = usage.get("output_tokens", 0)

        if input_tokens or output_tokens:
            return self.tracker.record_token_usage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_override=cost_override,
            )
        return 0.0

    def __getattr__(self, name: str) -> Any:
        """Forward everything else to the underlying model."""
        return getattr(self._model, name)
