"""Symbol parsing and conversion utilities.

This module provides utilities for working with semantic symbol formats
used throughout the quantitative trading system.

Semantic Symbol Format:
    {EXCHANGE}:{RAW_SYMBOL}[.{CONTRACT_TYPE}]

Examples:
    - Spot:           BINANCE:BTCUSDT
    - Perpetual:      BINANCE:BTCUSDT.PERP
    - Quarterly:      BINANCE:BTCUSDT.20260327
    - OKX Spot:       OKX:BTC-USDT
"""

from dataclasses import dataclass
from typing import Optional


# Known contract types
CONTRACT_TYPE_PERPETUAL = "PERP"

# Known exchanges
EXCHANGE_BINANCE = "BINANCE"
EXCHANGE_OKX = "OKX"


@dataclass
class SemanticSymbol:
    """Parsed semantic symbol representation.

    Attributes:
        exchange: Exchange identifier (e.g., "BINANCE", "OKX")
        raw_symbol: Raw trading pair symbol (e.g., "BTCUSDT")
        contract_type: Contract type suffix (e.g., "PERP", "20260327") or None for spot
        original: Original semantic symbol string
    """
    exchange: str
    raw_symbol: str
    contract_type: Optional[str]
    original: str

    @property
    def is_futures(self) -> bool:
        """Check if this is a futures contract."""
        return self.contract_type is not None

    @property
    def is_perpetual(self) -> bool:
        """Check if this is a perpetual contract."""
        return self.contract_type == CONTRACT_TYPE_PERPETUAL

    @property
    def is_spot(self) -> bool:
        """Check if this is a spot market symbol."""
        return self.contract_type is None


def parse_semantic_symbol(symbol: str) -> SemanticSymbol:
    """Parse a semantic symbol string into its components.

    Args:
        symbol: Semantic symbol string (e.g., "BINANCE:BTCUSDT.PERP")

    Returns:
        SemanticSymbol: Parsed symbol components

    Raises:
        ValueError: If the symbol format is invalid

    Examples:
        >>> parse_semantic_symbol("BINANCE:BTCUSDT")
        SemanticSymbol(exchange='BINANCE', raw_symbol='BTCUSDT', contract_type=None, original='BINANCE:BTCUSDT')

        >>> parse_semantic_symbol("BINANCE:BTCUSDT.PERP")
        SemanticSymbol(exchange='BINANCE', raw_symbol='BTCUSDT', contract_type='PERP', original='BINANCE:BTCUSDT.PERP')
    """
    if not symbol or not isinstance(symbol, str):
        raise ValueError(f"Invalid symbol: {symbol}")

    # Split exchange and symbol part
    if ":" not in symbol:
        raise ValueError(
            f"Invalid semantic symbol format: '{symbol}'. "
            f"Expected format: EXCHANGE:SYMBOL[.CONTRACT_TYPE]"
        )

    parts = symbol.split(":", 1)
    exchange = parts[0].upper()
    symbol_part = parts[1]

    if not exchange:
        raise ValueError(f"Missing exchange in symbol: '{symbol}'")

    if not symbol_part:
        raise ValueError(f"Missing symbol part in: '{symbol}'")

    # Split symbol and contract type
    if "." in symbol_part:
        raw_symbol, contract_type = symbol_part.rsplit(".", 1)
        contract_type = contract_type.upper()
    else:
        raw_symbol = symbol_part
        contract_type = None

    return SemanticSymbol(
        exchange=exchange,
        raw_symbol=raw_symbol.upper(),
        contract_type=contract_type,
        original=symbol,
    )


def to_binance_api_symbol(symbol: str) -> str:
    """Convert a semantic symbol to Binance API format.

    Extracts the raw symbol part that Binance API expects.

    Args:
        symbol: Semantic symbol string (e.g., "BINANCE:BTCUSDT.PERP")

    Returns:
        str: Raw symbol for Binance API (e.g., "BTCUSDT")

    Examples:
        >>> to_binance_api_symbol("BINANCE:BTCUSDT")
        'BTCUSDT'

        >>> to_binance_api_symbol("BINANCE:BTCUSDT.PERP")
        'BTCUSDT'
    """
    parsed = parse_semantic_symbol(symbol)
    return parsed.raw_symbol


def build_semantic_symbol(
    exchange: str,
    raw_symbol: str,
    contract_type: Optional[str] = None,
) -> str:
    """Build a semantic symbol from components.

    Args:
        exchange: Exchange identifier (e.g., "BINANCE")
        raw_symbol: Raw trading pair symbol (e.g., "BTCUSDT")
        contract_type: Optional contract type (e.g., "PERP", "20260327")

    Returns:
        str: Semantic symbol string

    Examples:
        >>> build_semantic_symbol("BINANCE", "BTCUSDT")
        'BINANCE:BTCUSDT'

        >>> build_semantic_symbol("BINANCE", "BTCUSDT", "PERP")
        'BINANCE:BTCUSDT.PERP'
    """
    exchange = exchange.upper()
    raw_symbol = raw_symbol.upper()

    if contract_type:
        return f"{exchange}:{raw_symbol}.{contract_type.upper()}"
    else:
        return f"{exchange}:{raw_symbol}"


def is_valid_semantic_symbol(symbol: str) -> bool:
    """Check if a string is a valid semantic symbol.

    Args:
        symbol: Symbol string to validate

    Returns:
        bool: True if valid, False otherwise
    """
    try:
        parse_semantic_symbol(symbol)
        return True
    except (ValueError, TypeError):
        return False
