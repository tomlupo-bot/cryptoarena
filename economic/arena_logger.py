"""
ArenaLogger — JSONL output writer for CryptoArena.

Produces four files per team:
  equity_curve.jsonl   — one line per trading interval
  trade_log.jsonl      — one line per executed trade
  token_costs.jsonl    — one line per LLM call  (handled by EconomicTracker)
  decisions.jsonl      — agent reasoning + tool calls per step
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional


class ArenaLogger:
    """Structured JSONL logger for a single team."""

    def __init__(self, base_path: str, team_signature: str):
        self.team_dir = os.path.join(base_path, team_signature)
        os.makedirs(self.team_dir, exist_ok=True)

        self._trade_log_path = os.path.join(self.team_dir, "trade_log.jsonl")
        self._decisions_path = os.path.join(self.team_dir, "decisions.jsonl")

    # ── trade logging ───────────────────────────────────────────────

    def log_trade(
        self,
        timestamp: str,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        fee: float = 0.0,
        reasoning: str = "",
        equity_before: float = 0.0,
        equity_after: float = 0.0,
        token_cost_this_step: float = 0.0,
    ) -> None:
        entry = {
            "timestamp": timestamp,
            "symbol": symbol,
            "side": side,
            "quantity": round(quantity, 8),
            "price": round(price, 4),
            "value_usdt": round(quantity * price, 4),
            "fee": round(fee, 6),
            "reasoning": reasoning,
            "equity_before": round(equity_before, 4),
            "equity_after": round(equity_after, 4),
            "token_cost_this_step": round(token_cost_this_step, 8),
        }
        self._append(self._trade_log_path, entry)

    # ── decision logging ────────────────────────────────────────────

    def log_decision(
        self,
        timestamp: str,
        step_num: int,
        agent_message: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        token_cost: float = 0.0,
    ) -> None:
        entry = {
            "timestamp": timestamp,
            "step": step_num,
            "agent_message": agent_message,
            "tool_calls": tool_calls or [],
            "token_cost": round(token_cost, 8),
        }
        self._append(self._decisions_path, entry)

    # ── helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _append(path: str, data: Dict[str, Any]) -> None:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")
