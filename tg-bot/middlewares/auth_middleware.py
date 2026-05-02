from aiogram import BaseMiddleware
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from typing import Callable, Dict, Any, Awaitable
from handlers.auth import AuthState
import logging

logger = logging.getLogger(__name__)

class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        state: FSMContext = data.get("state")
        if not state:
            return await handler(event, data)

        # Пропускаем /start, так как он сам обрабатывает авторизацию
        if event.text and event.text.startswith("/start"):
            return await handler(event, data)

        # Проверяем текущее состояние
        current_state = await state.get_state()
        if current_state == AuthState.authorized:
            # Уже авторизован, пропускаем
            return await handler(event, data)

        # Берём клиент из DI, не создаём новый
        api_client = data.get("api_client")
        if api_client is None:
            # Fallback: на случай если DI не настроен
            from services.api_client import BackendAPIClient
            api_client = BackendAPIClient()

        auth_result = await api_client.auth_check(
            platform="telegram",
            external_id=str(event.from_user.id)
        )

        if auth_result:
            # Пользователь авторизован, обновляем состояние
            logger.info(f"Restoring auth for user {event.from_user.id}")
            await state.update_data(
                global_user_id=auth_result["global_user_id"],
                role=auth_result["role"],
                platform_user_id=auth_result["platform_user_id"],
                phone=auth_result.get("phone", "")
            )
            await state.set_state(AuthState.authorized)
        else:
            logger.info(f"User {event.from_user.id} not authorized, letting /start handle")

        return await handler(event, data)