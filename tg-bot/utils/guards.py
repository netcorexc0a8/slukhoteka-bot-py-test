"""
Декораторы для проверки прав доступа в хендлерах.

Использование:
    @router.callback_query(F.data == "users_add")
    @require_role("admin", "methodist")
    async def users_add(callback: CallbackQuery, state: FSMContext):
        ...

Декоратор читает роль из FSM-состояния и отклоняет запрос
до того как хендлер выполнит какую-либо бизнес-логику.
Это защищает от случаев, когда UI-кнопки обходятся через
прямую отправку callback_data.
"""
import functools
import logging
from typing import Callable, Any
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

logger = logging.getLogger(__name__)


def require_role(*allowed_roles: str):
    """
    Декоратор для хендлеров Message и CallbackQuery.
    Отклоняет запрос если роль пользователя не входит в allowed_roles.
    """
    def decorator(handler: Callable) -> Callable:
        @functools.wraps(handler)
        async def wrapper(event: Message | CallbackQuery, *args, **kwargs) -> Any:
            # Достаём state из args или kwargs
            state: FSMContext | None = None
            for arg in args:
                if isinstance(arg, FSMContext):
                    state = arg
                    break
            if state is None:
                state = kwargs.get("state")

            if state is None:
                logger.error(f"require_role: FSMContext not found in handler {handler.__name__}")
                return _deny(event, "Ошибка авторизации. Попробуйте /start")

            data = await state.get_data()
            role = data.get("role", "")

            if role not in allowed_roles:
                logger.warning(
                    f"Access denied: user tried {handler.__name__} "
                    f"with role='{role}', required={allowed_roles}"
                )
                return await _deny(event, "У вас недостаточно прав для этого действия.")

            return await handler(event, *args, **kwargs)

        return wrapper
    return decorator


async def _deny(event: Message | CallbackQuery, text: str) -> None:
    if isinstance(event, CallbackQuery):
        await event.answer(text, show_alert=True)
    else:
        await event.answer(text)