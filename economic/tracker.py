"""
EconomicTracker — Adapted from ClawWork for CryptoArena.

Tracks the full economic picture per team:
- Token costs (deducted from trading capital)
- Trading PnL (realized + unrealized)
- Total equity = cash + unrealized PnL  (token costs already subtracted from cash)
- Survival tiers and kill conditions
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional


class EconomicTracker:
    """Per-team economic state tracker."""

    SURVIVAL_TIERS = {
        "thriving":   (0.50, float("inf")),
        "stable":     (0.20, 0.50),
        "struggling": (0.05, 0.20),
        "critical":   (0.00, 0.05),
        "dead":       (float("-inf"), 0.00),
    }

    def __init__(
        self,
        initial_balance: float,
        token_pricing: Dict[str, float],
        data_path: Optional[str] = None,
    ):
        self.initial_balance = initial_balance
        self.token_pricing = token_pricing
        self.cumulative_token_cost = 0.0
        self.peak_equity = initial_balance

        # Per-call tracking
        self.token_cost_log: List[Dict[str, Any]] = []
        # Per-interval equity snapshots
        self.equity_curve: List[Dict[str, Any]] = []

        # Realized PnL from closed trades
        self.realized_pnl = 0.0

        self.data_path = data_path
        if data_path:
            os.makedirs(data_path, exist_ok=True)

    # ── token cost recording ────────────────────────────────────────

    def record_token_usage(
        self,
        input_tokens: int,
        output_tokens: int,
        thinking_tokens: int = 0,
        cost_override: Optional[float] = None,
    ) -> float:
        """Calculate and record token cost. Returns cost in USD."""
        if cost_override is not None:
            total = cost_override
        else:
            input_cost = (input_tokens / 1_000_000) * self.token_pricing["input_per_1m"]
            output_cost = (output_tokens / 1_000_000) * self.token_pricing["output_per_1m"]
            thinking_rate = self.token_pricing.get(
                "thinking_per_1m", self.token_pricing["output_per_1m"]
            )
            thinking_cost = (thinking_tokens / 1_000_000) * thinking_rate
            total = input_cost + output_cost + thinking_cost

        self.cumulative_token_cost += total
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "thinking_tokens": thinking_tokens,
            "cost_usd": round(total, 8),
            "cumulative_cost": round(self.cumulative_token_cost, 8),
        }
        self.token_cost_log.append(entry)

        # Append to JSONL if data_path set
        if self.data_path:
            with open(os.path.join(self.data_path, "token_costs.jsonl"), "a") as f:
                f.write(json.dumps(entry) + "\n")

        return total

    # ── equity curve ────────────────────────────────────────────────

    def record_equity_snapshot(
        self,
        timestamp: str,
        cash: float,
        unrealized_pnl: float,
        positions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Record an equity curve data point."""
        equity = cash + unrealized_pnl
        self.peak_equity = max(self.peak_equity, equity)
        drawdown = (
            (self.peak_equity - equity) / self.peak_equity * 100
            if self.peak_equity > 0
            else 0.0
        )

        snapshot = {
            "timestamp": timestamp,
            "cash": round(cash, 4),
            "unrealized_pnl": round(unrealized_pnl, 4),
            "equity": round(equity, 4),
            "peak_equity": round(self.peak_equity, 4),
            "drawdown_pct": round(drawdown, 4),
            "cumulative_token_cost": round(self.cumulative_token_cost, 8),
            "survival_tier": self.get_survival_tier(equity),
            "num_positions": len(positions),
            "positions": positions,
        }
        self.equity_curve.append(snapshot)

        if self.data_path:
            with open(os.path.join(self.data_path, "equity_curve.jsonl"), "a") as f:
                f.write(json.dumps(snapshot) + "\n")

        return snapshot

    # ── survival ────────────────────────────────────────────────────

    def get_survival_tier(self, current_equity: float) -> str:
        ratio = current_equity / self.initial_balance if self.initial_balance > 0 else 0
        for tier, (low, high) in self.SURVIVAL_TIERS.items():
            if low <= ratio < high:
                return tier
        return "dead"

    # ── summary ─────────────────────────────────────────────────────

    def get_summary(self, cash: float, unrealized_pnl: float) -> Dict[str, Any]:
        equity = cash + unrealized_pnl
        return {
            "initial_balance": self.initial_balance,
            "current_equity": round(equity, 4),
            "total_return_pct": round(
                ((equity - self.initial_balance) / self.initial_balance) * 100, 4
            ),
            "cumulative_token_cost": round(self.cumulative_token_cost, 8),
            "token_cost_as_pct_of_initial": round(
                (self.cumulative_token_cost / self.initial_balance) * 100, 6
            ),
            "realized_pnl": round(self.realized_pnl, 4),
            "peak_equity": round(self.peak_equity, 4),
            "max_drawdown_pct": round(
                ((self.peak_equity - equity) / self.peak_equity * 100)
                if self.peak_equity > 0
                else 0,
                4,
            ),
            "survival_tier": self.get_survival_tier(equity),
            "total_llm_calls": len(self.token_cost_log),
            "avg_cost_per_call": round(
                (self.cumulative_token_cost / len(self.token_cost_log))
                if self.token_cost_log
                else 0,
                8,
            ),
        }
