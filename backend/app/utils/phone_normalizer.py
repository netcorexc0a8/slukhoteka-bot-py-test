import re

def normalize_phone(phone: str) -> str:
    phone = re.sub(r'[^\d+]', '', phone)
    if phone.startswith('8'):
        phone = '+7' + phone[1:]
    if phone.startswith('7') and not phone.startswith('+'):
        phone = '+' + phone
    if not re.match(r'^\+7\d{10}$', phone):
        raise ValueError(f"Неверный формат телефона: {phone}")
    return phone
