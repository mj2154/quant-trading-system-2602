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

from ..db.alert_signal_repository import AlertConfigRepository
from ..db.strategy_signals_repository import StrategySignalsRepository
from ..models.db.alert_config_models import (
    AlertConfigCreate,
    AlertConfigData,
    AlertConfigListData,
    AlertConfigUpdate,
    DeleteAlertData,
    ListAlertConfigsRequest,
    ListSignalsRequest,
    SignalData,
    SignalListData,
)
from ..models.protocol.ws_message import MessageSuccess
from .protocol import format_error_response, format_success_response

logger = logging.getLogger(__name__)


class AlertHandler:
    """WebSocket handler for alert signal operations."""

    def __init__(
        self,
        alert_repo: AlertConfigRepository,
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
    ) -> MessageSuccess:
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
            create_data = AlertConfigCreate.model_validate(data)

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

            # 使用 AlertConfigData 数据载荷模型构建响应数据
            alert_data = AlertConfigData(
                id=str(alert_result.get("id")),
                name=alert_result.get("name", ""),
                description=alert_result.get("description"),
                strategy_type=alert_result.get("strategy_type", ""),
                symbol=alert_result.get("symbol", ""),
                interval=alert_result.get("interval", ""),
                trigger_type=alert_result.get("trigger_type", ""),
                params=alert_result.get("params", {}),
                is_enabled=alert_result.get("is_enabled", False),
                created_at=alert_result.get("created_at"),
                updated_at=alert_result.get("updated_at"),
                created_by=alert_result.get("created_by"),
            )

            # Return full alert config using data model
            return format_success_response(
                request_id=request_id,
                response_type="ALERT_CONFIG_DATA",
                data=alert_data,
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
    ) -> MessageSuccess:
        """Handle list_alert_configs request.

        Args:
            data: Request data with pagination/filtering parameters.
            request_id: Request ID for response correlation.

        Returns:
            Response message dictionary.
        """
        try:
            # 使用 Pydantic 模型自动转换 camelCase -> snake_case
            # ListAlertConfigsRequest 使用 SnakeCaseModel 基类
            list_request = ListAlertConfigsRequest.model_validate(data)

            # 分页参数
            page = list_request.page
            page_size = list_request.page_size
            limit = page_size
            offset = (page - 1) * page_size

            # 筛选参数（已自动转换为 snake_case）
            is_enabled = list_request.is_enabled
            symbol = list_request.symbol
            strategy_type = list_request.strategy_type

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

            # 使用 AlertConfigData 数据载荷模型构建列表项
            items = []
            for alert in alerts:
                alert_data = AlertConfigData(
                    id=alert.get("id", ""),
                    name=alert.get("name", ""),
                    description=alert.get("description"),
                    strategy_type=alert.get("strategy_type", ""),
                    symbol=alert.get("symbol", ""),
                    interval=alert.get("interval", ""),
                    trigger_type=alert.get("trigger_type", ""),
                    params=alert.get("params", {}),
                    is_enabled=alert.get("is_enabled", False),
                    created_at=alert.get("created_at"),
                    updated_at=alert.get("updated_at"),
                    created_by=alert.get("created_by"),
                )
                items.append(alert_data)

            # 使用 AlertConfigListData 数据载荷模型构建响应数据
            list_data = AlertConfigListData(
                items=items,
                total=total,
                page=page,
                page_size=page_size,
            )

            return format_success_response(
                request_id=request_id,
                response_type="ALERT_CONFIG_DATA",
                data=list_data,
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
    ) -> MessageSuccess:
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
            update_data = AlertConfigUpdate.model_validate(data)

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

            # 使用 AlertConfigData 数据载荷模型构建响应数据
            alert_data = AlertConfigData(
                id=str(updated_alert.get("id")),
                name=updated_alert.get("name", ""),
                description=updated_alert.get("description"),
                strategy_type=updated_alert.get("strategy_type", ""),
                symbol=updated_alert.get("symbol", ""),
                interval=updated_alert.get("interval", ""),
                trigger_type=updated_alert.get("trigger_type", ""),
                params=updated_alert.get("params", {}),
                is_enabled=updated_alert.get("is_enabled", False),
                created_at=updated_alert.get("created_at"),
                updated_at=updated_alert.get("updated_at"),
                created_by=updated_alert.get("created_by"),
            )

            return format_success_response(
                request_id=request_id,
                response_type="ALERT_CONFIG_DATA",
                data=alert_data,
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
    ) -> MessageSuccess:
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

            # 使用 DeleteAlertData 数据载荷模型构建响应数据
            delete_data = DeleteAlertData(id=alert_id_str)

            return format_success_response(
                request_id=request_id,
                response_type="ALERT_CONFIG_DATA",
                data=delete_data,
            )

        except Exception as e:
            logger.exception("Failed to delete alert signal: %s", e)
            return format_error_response(
                request_id=request_id,
                error_code="DELETE_ALERT_FAILED",
                error_message=f"Failed to delete alert signal: {str(e)}",
            )

    # 注意：启用/禁用告警已合并到 handle_update_alert_config 中
    # 使用 UPDATE_ALERT_CONFIG 并在 data 中包含 isEnabled 字段来启用/禁用告警

    async def handle_list_signals(
        self,
        data: dict[str, Any],
        request_id: str | None = None,
    ) -> MessageSuccess:
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

            # 使用 Pydantic 模型自动转换 camelCase -> snake_case
            # ListSignalsRequest 使用 SnakeCaseModel 基类
            list_request = ListSignalsRequest.model_validate(data)

            # 分页参数
            page = list_request.page
            page_size = list_request.page_size
            # 筛选参数（已自动转换并类型校验）
            symbol = list_request.symbol
            strategy_type = list_request.strategy_type
            interval = list_request.interval
            signal_value = list_request.signal_value
            start_time = list_request.start_time
            end_time = list_request.end_time

            # 如果 start_time/end_time 是毫秒时间戳，转换为 datetime
            # Pydantic 会尝试解析，但前端可能直接传数字
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

            # 使用 SignalData 数据载荷模型构建列表项
            items = []
            for signal in signals:
                signal_data = SignalData(
                    id=signal.id,
                    alert_id=signal.alert_id or "",
                    name=signal.name or "",
                    strategy_type=signal.strategy_type,
                    symbol=signal.symbol,
                    interval=signal.interval,
                    trigger_type=signal.trigger_type,
                    signal_value=signal.signal_value,
                    signal_reason=signal.signal_reason,
                    computed_at=signal.computed_at,
                    source_subscription_key=signal.source_subscription_key,
                    metadata=signal.metadata,
                    created_by=None,  # SignalRecord 没有 created_by 字段
                )
                items.append(signal_data)

            # 使用 SignalListData 数据载荷模型构建响应数据
            list_data = SignalListData(
                items=items,
                total=total,
                page=page,
                page_size=page_size,
            )

            return format_success_response(
                request_id=request_id,
                response_type="SIGNAL_DATA",
                data=list_data,
            )

        except Exception as e:
            logger.exception("Failed to list signals: %s", e)
            return format_error_response(
                request_id=request_id,
                error_code="LIST_SIGNALS_FAILED",
                error_message=f"Failed to list signals: {str(e)}",
            )
