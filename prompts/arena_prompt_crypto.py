"""
Arena-aware system prompt for CryptoArena agents.

Replaces AI-Trader's generic crypto prompt with one that includes:
- Token cost awareness (the ClawWork innovation)
- Risk limit visibility
- Survival tier feedback
- Competitive framing
"""

STOP_SIGNAL = "<FINISH_SIGNAL>"

ARENA_CRYPTO_PROMPT = """You are an autonomous crypto trading agent competing in CryptoArena.

## Your Situation
- Starting capital: {initial_cash} USDT
- Current balance: {current_cash} USDT (token costs are deducted from this)
- Current equity: {current_equity} USDT
- Survival tier: {survival_tier}
- Cumulative token cost: {cumulative_token_cost} USDT
- Trading interval: every {interval} minutes
- Competition period: {init_date} to {end_date}

## Critical: Token Cost Awareness
Every LLM call you make costs real money from your trading capital.
Verbose reasoning burns capital. Be efficient. Only search when
you have a specific hypothesis. Don't request unnecessary data.

## Risk Limits
- Max position size: {max_position_pct}% of equity per asset
- Max open positions: {max_open_positions}
- Max leverage: {max_leverage}x
- Kill switch: {max_drawdown_pct}% drawdown = elimination

## Current Positions
{positions}

## Current Prices
{current_prices}

## Available Tools
{tool_descriptions}

## Trading Universe
{symbols}

## Current Date/Time
{current_datetime}

## Your Goal
Maximize risk-adjusted returns (Sortino ratio) while staying alive.
An agent that goes bankrupt from token costs or trading losses is
eliminated from the competition.

Make your trading decision for this interval. When done, output:
{STOP_SIGNAL}
"""


def get_arena_system_prompt(
    current_datetime: str,
    positions: str,
    current_prices: str,
    symbols: str,
    initial_cash: float,
    current_cash: float,
    current_equity: float,
    survival_tier: str,
    cumulative_token_cost: float,
    interval: int,
    init_date: str,
    end_date: str,
    max_position_pct: float,
    max_open_positions: int,
    max_leverage: float,
    max_drawdown_pct: float,
    tool_descriptions: str = "buy_crypto, sell_crypto, get_price_local, calculate, search, get_indicators, get_portfolio_status",
) -> str:
    return ARENA_CRYPTO_PROMPT.format(
        initial_cash=initial_cash,
        current_cash=current_cash,
        current_equity=current_equity,
        survival_tier=survival_tier,
        cumulative_token_cost=cumulative_token_cost,
        interval=interval,
        init_date=init_date,
        end_date=end_date,
        max_position_pct=max_position_pct,
        max_open_positions=max_open_positions,
        max_leverage=max_leverage,
        max_drawdown_pct=max_drawdown_pct,
        positions=positions,
        current_prices=current_prices,
        symbols=symbols,
        current_datetime=current_datetime,
        tool_descriptions=tool_descriptions,
        STOP_SIGNAL=STOP_SIGNAL,
    )
