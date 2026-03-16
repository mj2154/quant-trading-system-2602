"""Strategy registry for managing available trading strategies."""
import inspect
import json
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, get_origin, get_args

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

    Parameters are automatically extracted from generate_signals method signature.
    """

    _registry: dict[str, StrategyMetadata] = {}
    _discovered: bool = False

    @classmethod
    def _extract_params_from_signature(cls, strategy_class: type) -> list[StrategyParam]:
        """Automatically extract parameters from generate_signals method signature.

        Uses inspect.signature to extract parameter names, types, and default values
        from the generate_signals method. Skips 'self' and 'ohlv' parameters.

        Args:
            strategy_class: Strategy class to extract parameters from.

        Returns:
            List of StrategyParam objects extracted from method signature.
        """
        params = []

        # Get generate_signals method
        if not hasattr(strategy_class, 'generate_signals'):
            logger.warning(f"Strategy {strategy_class.__name__} has no generate_signals method")
            return params

        try:
            # Get method signature
            sig = inspect.signature(strategy_class.generate_signals)

            for param_name, param in sig.parameters.items():
                # Skip 'self', 'ohlcv', and **kwargs parameters
                if param_name in ('self', 'ohlcv', 'ohlcv'):
                    continue
                # Skip **kwargs and *args
                if param.kind in (inspect.Parameter.VAR_KEYWORD, inspect.Parameter.VAR_POSITIONAL):
                    continue

                # Determine parameter type from annotation
                param_type = 'int'  # default type
                if param.annotation is not inspect.Parameter.empty:
                    annotation = param.annotation
                    # Handle Union types like int | np.ndarray
                    origin = get_origin(annotation)
                    if origin is not None:
                        # Get the first non-None type from Union
                        args = get_args(annotation)
                        for arg in args:
                            if arg is not type(None):
                                annotation = arg
                                break

                    # Map Python types to string types
                    type_map = {
                        int: 'int',
                        float: 'float',
                        bool: 'bool',
                        str: 'str',
                    }
                    if annotation in type_map:
                        param_type = type_map[annotation]

                # Get default value - must have a valid default, not None
                default = None
                if param.default is not inspect.Parameter.empty and param.default is not None:
                    default = param.default
                    # If default is a numpy type, convert to Python type
                    if hasattr(default, 'item'):  # numpy scalar
                        default = default.item()
                else:
                    # Set sensible defaults based on type
                    if param_type == 'int':
                        default = 1
                    elif param_type == 'float':
                        default = 0.0
                    elif param_type == 'bool':
                        default = False

                # Generate description from parameter name
                description = cls._generate_param_description(param_name)

                strategy_param = StrategyParam(
                    name=param_name,
                    type=param_type,
                    default=default,
                    description=description,
                    min=None,
                    max=None,
                )
                params.append(strategy_param)

        except Exception as e:
            logger.warning(f"Failed to extract parameters from {strategy_class.__name__}: {e}")

        return params

    @classmethod
    def _generate_param_description(cls, param_name: str) -> str:
        """Generate human-readable description from parameter name.

        Args:
            param_name: Parameter name in snake_case.

        Returns:
            Human-readable description.
        """
        # Convert snake_case to Title Case with spaces
        # e.g., "macd1_fastperiod" -> "Macd1 Fastperiod"
        words = param_name.replace('_', ' ')
        # Handle numbers: "macd1_fastperiod" -> "MACD1 Fastperiod"
        result = []
        for word in words.split():
            if word.isdigit():
                result.append(word)
            else:
                result.append(word.capitalize())
        return ' '.join(result)

    @classmethod
    def register(cls, strategy_or_metadata: type | StrategyMetadata) -> None:
        """Register a strategy class or metadata by reading its class attributes.

        Parameters are automatically extracted from generate_signals method signature.

        Args:
            strategy_or_metadata: Strategy class (not instance) or StrategyMetadata instance to register.
        """
        # Handle StrategyMetadata instance (manual registration with explicit params)
        if isinstance(strategy_or_metadata, StrategyMetadata):
            cls._registry[strategy_or_metadata.type] = strategy_or_metadata
            logger.info(f"Registered strategy: {strategy_or_metadata.type} with {len(strategy_or_metadata.params)} parameters (manual)")
            return

        # Handle strategy class (auto-extract params from generate_signals method signature)
        strategy_class = strategy_or_metadata

        # Check if class has required metadata attributes
        if not hasattr(strategy_class, 'type') or not strategy_class.type:
            logger.warning(f"Strategy class {strategy_class.__name__} missing 'type' attribute, skipping")
            return

        if not hasattr(strategy_class, 'name') or not strategy_class.name:
            logger.warning(f"Strategy class {strategy_class.__name__} missing 'name' attribute, skipping")
            return

        # Auto-extract parameters from generate_signals method signature
        params = cls._extract_params_from_signature(strategy_class)

        metadata = StrategyMetadata(
            type=strategy_class.type,
            name=strategy_class.name,
            description=getattr(strategy_class, 'description', ''),
            params=params,
        )

        cls._registry[strategy_class.type] = metadata
        logger.info(f"Registered strategy: {strategy_class.type} with {len(params)} parameters (auto-extracted)")

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
