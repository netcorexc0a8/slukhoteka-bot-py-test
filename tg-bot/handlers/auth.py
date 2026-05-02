from aiogram import Router, F
from aiogram.types import Message, Contact
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import StateFilter
from aiogram.fsm.state import StatesGroup, State
from typing import TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from services.api_client import BackendAPIClient

router = Router()
logger = logging.getLogger(__name__)

class AuthState(StatesGroup):
    waiting_for_phone = State()
    waiting_for_invite_code = State()
    authorized = State()


ROLE_DISPLAY = {
    "specialist": "Специалист",
    "admin": "Администратор",
    "methodist": "Методист",
}


async def _finalize_auth(message: Message, state: FSMContext, result: dict, phone: str):
    """Завершает авторизацию: сохраняет данные в state, показывает одно приветственное сообщение с меню."""
    await state.update_data(
        global_user_id=result["global_user_id"],
        role=result["role"],
        platform_user_id=result["platform_user_id"],
        phone=phone,
    )
    await state.set_state(AuthState.authorized)

    from handlers.menu import _build_keyboard
    user_name = result.get("name") or message.from_user.first_name
    role_display = ROLE_DISPLAY.get(result["role"], result["role"].capitalize())
    keyboard = _build_keyboard(result["role"])

    await message.answer(
        f"👋 Привет, {user_name}!\n\n"
        f"Добро пожаловать в систему «Слухотека»\n\n"
        f"🎭 Ваша роль: {role_display}",
        reply_markup=keyboard,
    )

@router.message(F.text == "/start")
async def cmd_start(message: Message, state: FSMContext, api_client: "BackendAPIClient"):
    await state.clear()

    auth_result = await api_client.auth_check(
        platform="telegram",
        external_id=str(message.from_user.id)
    )

    if auth_result:
        # Пользователь уже авторизован
        await _finalize_auth(message, state, auth_result, auth_result.get("phone", ""))
    else:
        # Пользователь не авторизован - запрашиваем номер телефона
        contact_button = KeyboardButton(text="📱 Поделиться номером", request_contact=True)
        keyboard = ReplyKeyboardMarkup(keyboard=[[contact_button]], resize_keyboard=True)

        await message.answer(
            "Добро пожаловать в систему управления расписанием специалистов \"Слухотека\"!\n\n"
            "Нажмите кнопку ниже, чтобы автоматически поделиться номером телефона для авторизации:",
            reply_markup=keyboard
        )
        await state.set_state(AuthState.waiting_for_phone)

@router.message(StateFilter(AuthState.waiting_for_phone))
async def process_phone_input(message: Message, state: FSMContext, api_client: "BackendAPIClient"):
    logger.info(f"Processing message in waiting_for_phone state. Has contact: {message.contact is not None}")

    # Удаляем сообщение с контактом, если оно есть
    if message.contact:
        await message.delete()

    user_name = None
    if message.contact:
        contact: Contact = message.contact
        phone = contact.phone_number
        # Получаем имя из контакта
        if contact.first_name:
            user_name = contact.first_name
            if contact.last_name:
                user_name += f" {contact.last_name}"
        logger.info(f"Received phone from contact: {phone}, name: {user_name}")
    else:
        phone = message.text
        logger.info(f"Received phone from text: {phone}")

    from utils.phone_normalizer import normalize_phone

    try:
        phone = normalize_phone(phone)
        logger.info(f"Normalized phone: {phone}")
    except ValueError as e:
        logger.error(f"Phone normalization error: {e}")
        await message.answer("Пожалуйста, используйте кнопку '📱 Поделиться номером' для автоматической авторизации или введите номер в формате +7XXXXXXXXXX")
        return

    try:
        # Сохраняем временные данные
        await state.update_data(temp_phone=phone, temp_name=user_name)

        # Проверяем, существует ли пользователь
        phone_check = await api_client.auth_check_phone(phone)

        if phone_check:
            # Пользователь существует - авторизуем
            logger.info(f"User exists: {phone_check}, authorizing...")
            result = await api_client.auth_login(
                phone=phone,
                platform="telegram",
                external_id=str(message.from_user.id),
                name=user_name
            )
            logger.info(f"Auth successful: {result}")
            await _finalize_auth(message, state, result, phone)
        else:
            # Пользователь не существует - проверяем, является ли номер администраторским
            from config import settings
            if phone in settings.admin_phones:
                # Админ - создаём пользователя с ролью admin без кода приглашения
                logger.info(f"Admin phone detected: {phone}, creating admin user")
                result = await api_client.auth_login_with_role(
                    phone=phone,
                    platform="telegram",
                    external_id=str(message.from_user.id),
                    name=user_name,
                    role="admin"
                )
                await _finalize_auth(message, state, result, phone)
            else:
                # Обычный пользователь - запрашиваем invite code
                logger.info(f"User not found for phone {phone}, requesting invite code")
                await message.answer(
                    "🔑 Для завершения регистрации введите пригласительный код:\n\n"
                    "Код должен быть предоставлен администратором или методистом.",
                    reply_markup=None
                )
                await state.set_state(AuthState.waiting_for_invite_code)

    except Exception as e:
        from utils.errors import friendly_error
        await message.answer(friendly_error(e, "auth"))

@router.message(StateFilter(AuthState.waiting_for_invite_code))
async def process_invite_code(message: Message, state: FSMContext, api_client: "BackendAPIClient"):
    invite_code = message.text.strip()

    if not invite_code:
        await message.answer("Код не может быть пустым. Пожалуйста, введите код:")
        return

    try:
        user_data = await state.get_data()
        phone = user_data.get("temp_phone")
        user_name = user_data.get("temp_name")

        # Сначала проверяем код
        code_check = await api_client.invite_check(invite_code)

        if not code_check:
            await message.answer("❌ Неверный или уже использованный код. Пожалуйста, попробуйте снова:")
            return

        role = code_check["role"]
        logger.info(f"Invite code valid: {invite_code}, role: {role}")

        # Создаём пользователя с указанной ролью
        result = await api_client.auth_login_with_role(
            phone=phone,
            platform="telegram",
            external_id=str(message.from_user.id),
            name=user_name,
            role=role
        )

        # Помечаем код как использованный
        await api_client.invite_use(invite_code, result["global_user_id"])

        logger.info(f"User created with role: {role}")
        await _finalize_auth(message, state, result, phone)

    except Exception as e:
        from utils.errors import friendly_error
        await message.answer(f"❌ {friendly_error(e, 'invite_code')}\n\nПожалуйста, попробуйте снова:")