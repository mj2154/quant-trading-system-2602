"""Strategy registry for managing available trading strategies."""
import json
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ..db.database import Database

if TYPE_CHECKING:
    from ..db.database import Database

logger = logging.getLogger(__name__)


@dataclass
class StrategyParam:
    """Strategy parameter definition."""
    name: str  # Parameter name (used in API)
    type: str  # Parameter type: int, float, bool
    default: Any  # Default value
    description: str = ""  # Parameter description
    min: float | None = None  # Minimum value (optional)
    max: float | None = None  # Maximum value (optional)


@dataclass
class StrategyMetadata:
    """Strategy metadata."""
    type: str  # Strategy type identifier (e.g., MACDResonanceStrategyV5)
    name: str  # Display name
    description: str  # Strategy description
    params: list[StrategyParam] = field(default_factory=list)  # Parameter list

    def to_dict(self) -> dict:
        """Convert to dictionary for database storage."""
        return {
            "type": self.type,
            "name": self.name,
            "description": self.description,
            "params": [
                {
                    "name": p.name,
                    "type": p.type,
                    "default": p.default,
                    "description": p.description,
                    "min": p.min,
                    "max": p.max,
                }
                for p in self.params
            ],
        }


class StrategyRegistry:
    """Strategy registry for managing available strategies.

    Supports automatic discovery of strategies through class attributes.
    Each strategy class must declare:
    - type: str = "StrategyClassName" (must match class name)
    - name: str = "Strategy Display Name"
    - description: str = "Strategy description"
    - params: list[StrategyParam] = [...]
    """

    _registry: dict[str, StrategyMetadata] = {}
    _discovered: bool = False

    @classmethod
    def register(cls, strategy_class: type) -> None:
        """Register a strategy class by reading its class attributes.

        Args:
            strategy_class: Strategy class (not instance) to register.
        """
        # Check if class has required metadata attributes
        if not hasattr(strategy_class, 'type') or not strategy_class.type:
            logger.warning(f"Strategy class {strategy_class.__name__} missing 'type' attribute, skipping")
            return

        if not hasattr(strategy_class, 'name') or not strategy_class.name:
            logger.warning(f"Strategy class {strategy_class.__name__} missing 'name' attribute, skipping")
            return

        # Create metadata from class attributes
        type_id = strategy_class.type
        params = []
        if hasattr(strategy_class, 'params'):
            params = strategy_class.params or []

        metadata = StrategyMetadata(
            type=type_id,
            name=strategy_class.name,
            description=getattr(strategy_class, 'description', ''),
            params=params,
        )

        cls._registry[type_id] = metadata
        logger.info(f"Registered strategy: {type_id}")

    @classmethod
    def discover_strategies(cls) -> None:
        """Automatically discover and register all strategies.

        Scans all strategy modules and registers classes that inherit from BaseStrategy
        and have required metadata attributes.
        """
        if cls._discovered:
            return

        logger.info("Starting strategy auto-discovery")

        # Import all strategy modules to trigger class definitions
        try:
            from . import macd_resonance_strategy  # noqa: F401
        except ImportError as e:
            logger.warning(f"Failed to import macd_resonance_strategy: {e}")

        try:
            from . import alpha_01_strategy  # noqa: F401
        except ImportError as e:
            logger.warning(f"Failed to import alpha_01_strategy: {e}")

        try:
            from . import random_strategy  # noqa: F401
        except ImportError as e:
            logger.warning(f"Failed to import random_strategy: {e}")

        # Scan for classes with 'type' attribute in all imported strategy modules
        import sys
        strategy_modules = [
            "strategies.macd_resonance_strategy",
            "strategies.alpha_01_strategy",
            "strategies.random_strategy",
        ]

        for module_name in strategy_modules:
            full_module_name = f"src.{module_name}" if not module_name.startswith("src.") else module_name
            if full_module_name in sys.modules:
                module = sys.modules[full_module_name]
                for name in dir(module):
                    obj = getattr(module, name, None)
                    if isinstance(obj, type) and hasattr(obj, 'type'):
                        # Skip the base classes
                        if obj.__name__ in ('BaseStrategy', 'Strategy'):
                            continue
                        cls.register(obj)

        cls._discovered = True
        logger.info(f"Strategy auto-discovery complete. Registered {len(cls._registry)} strategies")

    @classmethod
    async def sync_to_database(cls, db: Database) -> None:
        """Synchronize strategy metadata to database.

        Args:
            db: Database instance.
        """
        # Ensure table exists
        create_table_sql = """
            CREATE TABLE IF NOT EXISTS alert_strategy_metadata (
                type VARCHAR(100) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                params JSONB NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """
        await db.execute(create_table_sql)

        # Upsert each strategy metadata
        for metadata in cls._registry.values():
            params_json = json.dumps(metadata.to_dict()["params"])
            await db.execute(
                """
                INSERT INTO alert_strategy_metadata (type, name, description, params, updated_at)
                VALUES ($1, $2, $3, $4, NOW())
                ON CONFLICT (type) DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    params = EXCLUDED.params,
                    updated_at = NOW()
                """,
                metadata.type,
                metadata.name,
                metadata.description,
                params_json,
            )
        logger.info(f"Synced {len(cls._registry)} strategies to database")

    @classmethod
    def get_all(cls) -> list[StrategyMetadata]:
        """Get all registered strategies.

        Returns:
            List of strategy metadata.
        """
        cls.discover_strategies()
        return list(cls._registry.values())

    @classmethod
    def get(cls, strategy_type: str) -> StrategyMetadata | None:
        """Get metadata for a specific strategy.

        Args:
            strategy_type: Strategy type identifier.

        Returns:
            Strategy metadata or None if not found.
        """
        cls.discover_strategies()
        return cls._registry.get(strategy_type)
