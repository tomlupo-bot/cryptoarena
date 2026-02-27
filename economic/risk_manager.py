"""
RiskManager — Pre-trade validation against configured risk limits.
"""

from typing import Any, Dict, List, Tuple


class RiskManager:
    """Validates trades against position limits, leverage, and concentration."""

    def __init__(self, limits: Dict[str, Any], initial_capital: float):
        self.max_position_pct = limits.get("max_position_pct", 30.0)
        self.max_leverage = limits.get("max_leverage", 1.0)
        self.max_open_positions = limits.get("max_open_positions", 5)
        self.stop_loss_pct = limits.get("stop_loss_pct", 10.0)
        self.initial_capital = initial_capital

    def validate_trade(
        self,
        trade: Dict[str, Any],
        current_positions: List[Dict[str, Any]],
        current_cash: float,
        prices: Dict[str, float],
    ) -> Tuple[bool, str]:
        """
        Returns (allowed, reason).

        Checks:
        1. Position size <= max_position_pct of equity
        2. Total exposure <= max_leverage * equity
        3. Number of open positions <= max_open_positions
        4. Sufficient cash
        """
        violations: List[str] = []

        equity = current_cash + sum(
            p["quantity"] * prices.get(p["symbol"], 0) for p in current_positions
        )
        if equity <= 0:
            return False, "Zero or negative equity"

        symbol = trade["symbol"]
        side = trade["side"]
        quantity = trade["quantity"]
        price = prices.get(symbol, 0)
        trade_value = quantity * price

        # Position concentration
        if trade_value / equity * 100 > self.max_position_pct:
            violations.append(
                f"Position {trade_value / equity * 100:.1f}% > limit {self.max_position_pct}%"
            )

        # Open positions count (only for new buys)
        if side == "buy":
            existing_symbols = {p["symbol"] for p in current_positions if p["quantity"] > 0}
            if symbol not in existing_symbols and len(existing_symbols) >= self.max_open_positions:
                violations.append(f"Max {self.max_open_positions} positions reached")

        # Leverage check
        total_exposure = (
            sum(abs(p["quantity"]) * prices.get(p["symbol"], 0) for p in current_positions)
            + trade_value
        )
        if total_exposure / equity > self.max_leverage:
            violations.append(
                f"Leverage {total_exposure / equity:.2f}x > {self.max_leverage}x"
            )

        # Cash check for buys
        if side == "buy" and trade_value > current_cash:
            violations.append(
                f"Insufficient cash: need {trade_value:.2f}, have {current_cash:.2f}"
            )

        if violations:
            return False, "; ".join(violations)
        return True, "OK"
