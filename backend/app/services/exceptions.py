"""
Доменные исключения для логики абонементов и броней.
В API-слое они конвертируются в HTTPException с понятными сообщениями.
"""


class DomainError(Exception):
    """Базовое доменное исключение."""


class SubscriptionNotFound(DomainError):
    pass


class SubscriptionNotActive(DomainError):
    """Абонемент не активен (completed/expired/cancelled или удалён)."""


class SubscriptionExhausted(DomainError):
    """Все сессии абонемента уже использованы."""


class WeeklyLimitExceeded(DomainError):
    """У клиента уже есть бронь по этому абонементу в той же ISO-неделе."""

    def __init__(self, existing_booking_time):
        self.existing_booking_time = existing_booking_time
        super().__init__(
            f"У клиента уже есть занятие по этому абонементу на этой неделе "
            f"({existing_booking_time:%d.%m %H:%M}). "
            f"Перенесите существующее или выберите другую неделю."
        )


class TimeSlotConflict(DomainError):
    """Время специалиста уже занято другой бронью."""


class InvalidSubscriptionConfig(DomainError):
    """Невалидная конфигурация подписки (например, для individual нет специалиста)."""
