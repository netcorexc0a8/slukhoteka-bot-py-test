"""
Утилиты для обработки ошибок.

Скрывают технические детали от пользователя и логируют полный traceback.
"""
import logging
import httpx

logger = logging.getLogger(__name__)


def friendly_error(e: Exception, context: str = "") -> str:
    """
    Возвращает понятное пользователю сообщение об ошибке.

    Технические детали (URL, stacktrace, статус-коды) не раскрываются.
    Полная информация пишется в лог.
    """
    prefix = f"[{context}] " if context else ""

    if isinstance(e, httpx.ConnectError):
        logger.error(f"{prefix}Backend недоступен: {e}")
        return "Сервис временно недоступен. Попробуйте через несколько секунд."

    if isinstance(e, httpx.TimeoutException):
        logger.error(f"{prefix}Таймаут запроса: {e}")
        return "Сервис не отвечает. Попробуйте позже."

    if isinstance(e, httpx.HTTPStatusError):
        status = e.response.status_code
        detail = ""
        try:
            detail = e.response.json().get("detail", "")
        except Exception:
            pass
        logger.error(f"{prefix}HTTP {status}: {detail or e}")

        if status == 400 and detail:
            return f"Ошибка: {detail}"
        if status == 403:
            return "Недостаточно прав для выполнения операции."
        if status == 404:
            return "Запись не найдена."
        if status == 409 and detail:
            return f"Конфликт: {detail}"
        if status == 422 and detail:
            return f"Некорректные данные: {detail}"
        return "Произошла ошибка на сервере. Попробуйте позже."

    logger.exception(f"{prefix}Неожиданная ошибка: {e}")
    return "Произошла непредвиденная ошибка. Попробуйте позже."