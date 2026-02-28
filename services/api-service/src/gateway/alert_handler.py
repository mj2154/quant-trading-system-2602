"""
WebSocket Alert Config Handler

Handles alert config related WebSocket message types:
- create_alert_config - Create alert
- list_alert_configs - List alerts (with pagination/filtering)
- update_alert_config - Update alert
- delete_alert_config - Delete alert
- enable_alert_config - Enable/disable alert
- list_signals - Query historical signals

Author: Claude Code
Version: v2.0.0
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from ..db.alert_signal_repository import AlertSignalRepository
from ..db.strategy_signals_repository import StrategySignalsRepository
from ..models.db.alert_config_models import (
    AlertSignalCreate,
    AlertSignalUpdate,
)
from .protocol import format_success_response, format_error_response

logger = logging.getLogger(__name__)


class AlertHandler:
    """WebSocket handler for alert signal operations."""

    def __init__(
        self,
        alert_repo: AlertSignalRepository,
        signals_repo: StrategySignalsRepository | None = None,
    ) -> None:
        """Initialize alert handler.

        Args:
            alert_repo: Alert signal repository instance.
            signals_repo: Optional strategy signals repository instance.
        """
        self._alert_repo = alert_repo
        self._signals_repo = signals_repo

    async def handle_create_alert_config(
        self,
        data: dict[str, Any],
        request_id: str | None = None,
    ) -> dict[str, Any]:
        """Handle create_alert_config request.

        Args:
            data: Request data.
            request_id: Request ID for response correlation.

        Returns:
            Response message dictionary.
        """
        try:
            # DEBUG: Log received data
            logger.info("[DEBUG] handle_create_alert_config received data: %s", data)

            # Parse and validate request data
            create_data = AlertSignalCreate.model_validate(data)

            # Handle threshold field: if sent by frontend, merge it into params
            # According to design docs, threshold should be stored in params JSON field
            params = create_data.params.copy() if create_data.params else {}
            if "threshold" in data and data["threshold"] is not None:
                params["threshold"] = data["threshold"]

            # Create alert signal and get the full alert object
            alert_result = await self._alert_repo.create(
                alert_id=create_data.id,
                name=create_data.name,
                strategy_type=create_data.strategy_type,
                symbol=create_data.symbol,
                interval=create_data.interval,
                trigger_type=create_data.trigger_type,
                params=params if params else None,
                description=create_data.description,
                is_enabled=create_data.is_enabled,
                created_by=create_data.created_by,
            )

            logger.info(
                "Alert signal created: id=%s name=%s",
                alert_result.get("id"),
                create_data.name,
            )

            # Return full alert config as per API spec
            return format_success_response(
                request_id=request_id,
                response_type="ALERT_CONFIG_DATA",
                data={
                    "type": "create_alert_config",
                    "id": str(alert_result.get("id")),
                    "name": alert_result.get("name"),
                    "description": alert_result.get("description"),
                    "strategy_type": alert_result.get("strategy_type"),
                    "symbol": alert_result.get("symbol"),
                    "interval": alert_result.get("interval"),
                    "trigger_type": alert_result.get("trigger_type"),
                    "params": alert_result.get("params"),
                    "is_enabled": alert_result.get("is_enabled"),
                    "created_at": alert_result.get("created_at"),
                    "created_by": alert_result.get("created_by"),
                },
            )

        except Exception as e:
            logger.exception("Failed to create alert signal: %s", e)
            return format_error_response(
                request_id=request_id,
                error_code="CREATE_ALERT_FAILED",
                error_message=f"Failed to create alert signal: {str(e)}",
            )

    async def handle_list_alert_configs(
        self,
        data: dict[str, Any],
        request_id: str | None = None,
    ) -> dict[str, Any]:
        """Handle list_alert_configs request.

        Args:
            data: Request data with pagination/filtering parameters.
            request_id: Request ID for response correlation.

        Returns:
            Response message dictionary.
        """
        try:
            # Parse request data
            limit = data.get("limit", 100)
            offset = data.get("offset", 0)
            is_enabled = data.get("is_enabled")
            symbol = data.get("symbol")
            strategy_type = data.get("strategy_type")

            # Convert is_enabled from string if needed
            if is_enabled is not None and isinstance(is_enabled, str):
                is_enabled = is_enabled.lower() in ("true", "1", "yes")

            # Query alert signals
            alerts, total = await self._alert_repo.find_all(
                limit=limit,
                offset=offset,
                is_enabled=is_enabled,
                symbol=symbol,
                strategy_type=strategy_type,
            )

            # Calculate page info
            page = offset // limit + 1 if limit > 0 else 1
            page_size = limit

            return format_success_response(
                request_id=request_id,
                response_type="ALERT_CONFIG_DATA",
                data={
                    "type": "list_alert_configs",
                    "items": alerts,
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                },
            )

        except Exception as e:
            logger.exception("Failed to list alert signals: %s", e)
            return format_error_response(
                request_id=request_id,
                error_code="LIST_ALERTS_FAILED",
                error_message=f"Failed to list alert signals: {str(e)}",
            )

    async def handle_update_alert_config(
        self,
        data: dict[str, Any],
        request_id: str | None = None,
    ) -> dict[str, Any]:
        """Handle update_alert_config request.

        Args:
            data: Request data with alert ID and update fields.
            request_id: Request ID for response correlation.

        Returns:
            Response message dictionary.
        """
        try:
            # DEBUG: Log received data
            logger.info("[DEBUG] handle_update_alert_config received data: %s", data)

            # Parse alert ID
            alert_id = data.get("id")
            if not alert_id:
                return format_error_response(
                    request_id=request_id,
                    error_code="INVALID_PARAMETERS",
                    error_message="Missing required field: id",
                )

            # Validate UUID format
            try:
                UUID(alert_id)
            except (ValueError, AttributeError):
                return format_error_response(
                    request_id=request_id,
                    error_code="INVALID_PARAMETERS",
                    error_message="Invalid alert ID format",
                )

            # Parse update data
            update_data = AlertSignalUpdate.model_validate(data)

            # Handle threshold field: if sent by frontend, merge it into params
            # According to design docs, threshold should be stored in params JSON field
            params = update_data.params.copy() if update_data.params else {}
            if "threshold" in data and data["threshold"] is not None:
                params["threshold"] = data["threshold"]

            # Perform update (pass string, not UUID, since DB field is VARCHAR)
            success = await self._alert_repo.update(
                alert_id=alert_id,
                name=update_data.name,
                description=update_data.description,
                strategy_type=update_data.strategy_type,
                symbol=update_data.symbol,
                interval=update_data.interval,
                trigger_type=update_data.trigger_type,
                params=params if params else None,
                is_enabled=update_data.is_enabled,
            )

            if not success:
                return format_error_response(
                    request_id=request_id,
                    error_code="ALERT_NOT_FOUND",
                    error_message="Alert signal not found or no changes made",
                )

            # Fetch updated alert config to return full data (per API spec)
            updated_alert = await self._alert_repo.find_by_id(alert_id)

            logger.info("Alert signal updated: id=%s", alert_id)

            return format_success_response(
                request_id=request_id,
                response_type="ALERT_CONFIG_DATA",
                data={
                    "type": "update_alert_config",
                    "id": str(updated_alert.get("id")),
                    "name": updated_alert.get("name"),
                    "description": updated_alert.get("description"),
                    "strategy_type": updated_alert.get("strategy_type"),
                    "symbol": updated_alert.get("symbol"),
                    "interval": updated_alert.get("interval"),
                    "trigger_type": updated_alert.get("trigger_type"),
                    "params": updated_alert.get("params"),
                    "is_enabled": updated_alert.get("is_enabled"),
                    "created_at": updated_alert.get("created_at"),
                    "updated_at": updated_alert.get("updated_at"),
                    "created_by": updated_alert.get("created_by"),
                },
            )

        except Exception as e:
            logger.exception("Failed to update alert signal: %s", e)
            return format_error_response(
                request_id=request_id,
                error_code="UPDATE_ALERT_FAILED",
                error_message=f"Failed to update alert signal: {str(e)}",
            )

    async def handle_delete_alert_config(
        self,
        data: dict[str, Any],
        request_id: str | None = None,
    ) -> dict[str, Any]:
        """Handle delete_alert_config request.

        Args:
            data: Request data with alert ID.
            request_id: Request ID for response correlation.

        Returns:
            Response message dictionary.
        """
        try:
            # DEBUG: Log received data
            logger.info("[DEBUG] handle_delete_alert_config received data: %s", data)

            # Parse alert ID
            alert_id_str = data.get("id")
            if not alert_id_str:
                return format_error_response(
                    request_id=request_id,
                    error_code="INVALID_PARAMETERS",
                    error_message="Missing required field: id",
                )

            # Validate UUID format but pass string to repository (DB field is VARCHAR)
            try:
                UUID(alert_id_str)
            except (ValueError, AttributeError):
                return format_error_response(
                    request_id=request_id,
                    error_code="INVALID_PARAMETERS",
                    error_message="Invalid alert ID format",
                )

            # Delete alert signal (pass string, not UUID, since DB field is VARCHAR)
            success = await self._alert_repo.delete(alert_id_str)

            if not success:
                return format_error_response(
                    request_id=request_id,
                    error_code="ALERT_NOT_FOUND",
                    error_message="Alert signal not found",
                )

            logger.info("Alert signal deleted: id=%s", alert_id_str)

            return format_success_response(
                request_id=request_id,
                response_type="ALERT_CONFIG_DATA",
                data={
                    "type": "delete_alert_config",
                    "id": alert_id_str,
                    "message": "Alert signal deleted successfully",
                },
            )

        except Exception as e:
            logger.exception("Failed to delete alert signal: %s", e)
            return format_error_response(
                request_id=request_id,
                error_code="DELETE_ALERT_FAILED",
                error_message=f"Failed to delete alert signal: {str(e)}",
            )

    async def handle_enable_alert_config(
        self,
        data: dict[str, Any],
        request_id: str | None = None,
    ) -> dict[str, Any]:
        """Handle enable_alert_config request.

        Args:
            data: Request data with alert ID and enabled status.
            request_id: Request ID for response correlation.

        Returns:
            Response message dictionary.
        """
        try:
            # DEBUG: Log received data
            logger.info("[DEBUG] handle_enable_alert_config received data: %s", data)

            # Parse alert ID
            alert_id = data.get("id")
            if not alert_id:
                return format_error_response(
                    request_id=request_id,
                    error_code="INVALID_PARAMETERS",
                    error_message="Missing required field: id",
                )

            # Validate UUID format
            try:
                UUID(alert_id)
            except (ValueError, AttributeError):
                return format_error_response(
                    request_id=request_id,
                    error_code="INVALID_PARAMETERS",
                    error_message="Invalid alert ID format",
                )

            # Parse enabled status
            is_enabled = data.get("is_enabled")
            if is_enabled is None:
                return format_error_response(
                    request_id=request_id,
                    error_code="INVALID_PARAMETERS",
                    error_message="Missing required field: is_enabled",
                )

            # Convert from string if needed
            if isinstance(is_enabled, str):
                is_enabled = is_enabled.lower() in ("true", "1", "yes")

            # Enable/disable alert signal (pass string, not UUID, since DB field is VARCHAR)
            success = await self._alert_repo.enable(alert_id) if is_enabled else await self._alert_repo.disable(alert_id)

            if not success:
                return format_error_response(
                    request_id=request_id,
                    error_code="ALERT_NOT_FOUND",
                    error_message="Alert signal not found",
                )

            action = "enabled" if is_enabled else "disabled"
            logger.info("Alert signal %s: id=%s", action, alert_id)

            return format_success_response(
                request_id=request_id,
                response_type="ALERT_CONFIG_DATA",
                data={
                    "type": "enable_alert_config",
                    "id": str(alert_id),
                    "is_enabled": is_enabled,
                    "message": f"Alert signal {action} successfully",
                },
            )

        except Exception as e:
            logger.exception("Failed to enable/disable alert signal: %s", e)
            return format_error_response(
                request_id=request_id,
                error_code="ENABLE_ALERT_FAILED",
                error_message=f"Failed to enable/disable alert signal: {str(e)}",
            )

    async def handle_list_signals(
        self,
        data: dict[str, Any],
        request_id: str | None = None,
    ) -> dict[str, Any]:
        """Handle list_signals request.

        Queries historical signals from strategy_signals table.

        Args:
            data: Request data with filtering parameters.
            request_id: Request ID for response correlation.

        Returns:
            Response message dictionary.
        """
        try:
            # Check if signals repo is available
            if self._signals_repo is None:
                return format_error_response(
                    request_id=request_id,
                    error_code="REPOSITORY_NOT_INITIALIZED",
                    error_message="Strategy signals repository not initialized",
                )

            # Parse parameters
            symbol = data.get("symbol")
            strategy_type = data.get("strategy_type")
            interval = data.get("interval")
            signal_value = data.get("signal_value")
            start_time = data.get("start_time")
            end_time = data.get("end_time")
            page = data.get("page", 1)
            page_size = data.get("page_size", 20)

            # Convert signal_value from string if needed
            if signal_value is not None and isinstance(signal_value, str):
                signal_value = signal_value.lower() in ("true", "1", "yes")

            # Convert start_time/end_time from milliseconds to datetime if needed
            if start_time and isinstance(start_time, int):
                start_time = datetime.fromtimestamp(start_time / 1000)
            if end_time and isinstance(end_time, int):
                end_time = datetime.fromtimestamp(end_time / 1000)

            signals, total = await self._signals_repo.find_all(
                page=page,
                page_size=page_size,
                symbol=symbol,
                strategy_type=strategy_type,
                interval=interval,
                signal_value=signal_value,
                start_time=start_time,
                end_time=end_time,
            )

            # Convert SignalRecord objects to dicts
            items = []
            for signal in signals:
                items.append({
                    "id": signal.id,
                    "alert_id": signal.alert_id,
                    "strategy_type": signal.strategy_type,
                    "symbol": signal.symbol,
                    "interval": signal.interval,
                    "trigger_type": signal.trigger_type,
                    "signal_value": signal.signal_value,
                    "computed_at": signal.computed_at.isoformat() if signal.computed_at else None,
                    "source_subscription_key": signal.source_subscription_key,
                    "metadata": signal.metadata,
                })

            return format_success_response(
                request_id=request_id,
                response_type="SIGNAL_DATA",
                data={
                    "type": "list_signals",
                    "items": items,
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                },
            )

        except Exception as e:
            logger.exception("Failed to list signals: %s", e)
            return format_error_response(
                request_id=request_id,
                error_code="LIST_SIGNALS_FAILED",
                error_message=f"Failed to list signals: {str(e)}",
            )
