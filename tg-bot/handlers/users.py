from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from services.api_client import BackendAPIClient
from utils.guards import require_role
from utils.errors import friendly_error
import logging

router = Router()
logger = logging.getLogger(__name__)

class UsersState(StatesGroup):
    main = State()
    add_select_role = State()
    add_generated = State()
    view_list = State()
    edit_select_user = State()
    edit_name = State()
    delete_select_user = State()
    delete_confirm = State()
    role_select_user = State()
    role_select_role = State()

@router.message(F.text == "👤 Пользователи")
@require_role("admin", "methodist")
async def cmd_users(message: Message, state: FSMContext):

    buttons = [
        [InlineKeyboardButton(text="📋 Список пользователей", callback_data="users_view")],
        [InlineKeyboardButton(text="➕ Добавить пользователя", callback_data="users_add")],
        [InlineKeyboardButton(text="✏️ Изменить имя", callback_data="users_edit_name")],
        [InlineKeyboardButton(text="🔄 Изменить роль", callback_data="users_edit_role")],
        [InlineKeyboardButton(text="🗑️ Удалить пользователя", callback_data="users_delete")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="users_back")]
    ]

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("👤 Управление пользователями", reply_markup=keyboard)
    await state.set_state(UsersState.main)

@router.callback_query(F.data == "users_back")
async def users_back(callback: CallbackQuery, state: FSMContext):
    from handlers.menu import show_main_menu
    await callback.message.delete()
    await show_main_menu(callback.message, state)
    await callback.answer()

@router.callback_query(F.data == "users_add")
@require_role("admin", "methodist")
async def users_add(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    role = data.get("role", "specialist")

    buttons = [
        [InlineKeyboardButton(text="Методист", callback_data="users_invite_role_methodist")],
        [InlineKeyboardButton(text="Специалист", callback_data="users_invite_role_specialist")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="users_back")]
    ]

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text("Выберите роль для нового пользователя:", reply_markup=keyboard)
    await state.set_state(UsersState.add_select_role)
    await callback.answer()

@router.callback_query(F.data.startswith("users_invite_role_"))
async def users_role_selected(callback: CallbackQuery, state: FSMContext):
    role_map = {
        "methodist": "methodist",
        "specialist": "specialist"
    }

    selected_role = callback.data.replace("users_invite_role_", "")
    if selected_role not in role_map:
        await callback.answer("Неверная роль")
        return

    data = await state.get_data()
    global_user_id = data.get("global_user_id")

    try:
        api_client = BackendAPIClient()
        invite = await api_client.invite_create(role_map[selected_role], global_user_id)

        await callback.message.edit_text(
            f"✅ Код приглашения сгенерирован!\n\n"
            f"<code>{invite['code']}</code>\n\n"
            f"Роль: {invite['role']}\n"
            f"Отправьте этот код пользователю для регистрации",
            parse_mode="HTML"
        )
        await state.set_state(UsersState.add_generated)
        await callback.answer()

    except Exception as e:
        logger.error(f"Error creating invite: {e}")
        await callback.message.edit_text(friendly_error(e, "invite_create"))
        await callback.answer()

@router.callback_query(F.data == "users_view")
@require_role("admin", "methodist")
async def users_view(callback: CallbackQuery, state: FSMContext):
    try:
        api_client = BackendAPIClient()
        users = await api_client.users_get_all()

        if not users:
            await callback.message.edit_text("Список пользователей пуст")
            await callback.answer()
            return

        text = "📋 Список пользователей:\n\n"
        for user in users:
            role_emoji = {
                "admin": "👑",
                "methodist": "📚",
                "specialist": "👨‍⚕️"
            }.get(user["role"], "❓")

            name = user.get("name") or "Не указано"
            phone = user.get("phone") or "Не указано"
            role_name = {
                "admin": "Администратор",
                "methodist": "Методист",
                "specialist": "Специалист"
            }.get(user["role"], "Не указано")

            text += f"🆔 ID: {user['id']}\n"
            text += f"👤 Имя: {name}\n"
            text += f"📱 Тел.: {phone}\n"
            text += f"🎭 Роль: {role_name}\n\n"

        buttons = [
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="users_back")]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback.message.edit_text(text, reply_markup=keyboard)
        await state.set_state(UsersState.view_list)
        await callback.answer()

    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        await callback.message.edit_text(friendly_error(e, "users_list"))
        await callback.answer()

@router.callback_query(F.data == "users_edit_name")
@require_role("admin", "methodist")
async def users_edit_name_start(callback: CallbackQuery, state: FSMContext):
    try:
        api_client = BackendAPIClient()
        users = await api_client.users_get_all()

        if not users:
            await callback.message.edit_text("Список пользователей пуст")
            await callback.answer()
            return

        buttons = []
        for user in users:
            name = user.get("name") or "Не указано"
            buttons.append([InlineKeyboardButton(
                text=f"{name} ({user['phone']})",
                callback_data=f"users_edit_name_{user['id']}"
            )])

        buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="users_back")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback.message.edit_text("Выберите пользователя для изменения имени:", reply_markup=keyboard)
        await state.set_state(UsersState.edit_select_user)
        await callback.answer()

    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        await callback.message.edit_text(friendly_error(e, "users_list"))
        await callback.answer()

@router.callback_query(F.data.startswith("users_edit_name_"))
async def users_edit_name_selected(callback: CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split("_")[-1])
    await state.update_data(edit_user_id=user_id)

    await callback.message.edit_text("Введите новое имя пользователя:")
    await state.set_state(UsersState.edit_name)
    await callback.answer()

@router.message(UsersState.edit_name)
async def users_edit_name_input(message: Message, state: FSMContext):
    new_name = message.text.strip()

    if not new_name:
        await message.answer("Имя не может быть пустым")
        return

    data = await state.get_data()
    user_id = data.get("edit_user_id")

    try:
        api_client = BackendAPIClient()
        await api_client.users_update(user_id, name=new_name)

        await message.answer(f"✅ Имя пользователя успешно изменено на '{new_name}'")
        await cmd_users(message, state)

    except Exception as e:
        logger.error(f"Error updating user name: {e}")
        await message.answer(friendly_error(e, "users_edit_name"))

@router.callback_query(F.data == "users_edit_role")
@require_role("admin")
async def users_edit_role_start(callback: CallbackQuery, state: FSMContext):

    try:
        api_client = BackendAPIClient()
        users = await api_client.users_get_all()

        current_user_id = data.get("global_user_id")
        users = [u for u in users if u["id"] != current_user_id]

        if not users:
            await callback.message.edit_text("Нет доступных пользователей для изменения роли")
            await callback.answer()
            return

        buttons = []
        for user in users:
            name = user.get("name") or "Не указано"
            role_emoji = {
                "admin": "👑",
                "methodist": "📚",
                "specialist": "👨‍⚕️"
            }.get(user["role"], "❓")

            buttons.append([InlineKeyboardButton(
                text=f"{role_emoji} {name} ({user['phone']})",
                callback_data=f"users_role_select_{user['id']}"
            )])

        buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="users_back")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback.message.edit_text("Выберите пользователя для изменения роли:", reply_markup=keyboard)
        await state.set_state(UsersState.role_select_user)
        await callback.answer()

    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        await callback.message.edit_text(friendly_error(e, "users_list"))
        await callback.answer()

@router.callback_query(F.data.startswith("users_role_select_"))
async def users_role_select_user(callback: CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split("_")[-1])
    await state.update_data(role_user_id=user_id)

    buttons = [
        [InlineKeyboardButton(text="👑 Администратор", callback_data="users_role_set_admin")],
        [InlineKeyboardButton(text="📚 Методист", callback_data="users_role_set_methodist")],
        [InlineKeyboardButton(text="👨‍⚕️ Специалист", callback_data="users_role_set_specialist")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="users_back")]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text("Выберите новую роль:", reply_markup=keyboard)
    await state.set_state(UsersState.role_select_role)
    await callback.answer()

@router.callback_query(F.data.startswith("users_role_set_"))
async def users_role_set(callback: CallbackQuery, state: FSMContext):
    role_map = {
        "admin": "admin",
        "methodist": "methodist",
        "specialist": "specialist"
    }

    selected_role = callback.data.split("_")[-1]
    if selected_role not in role_map:
        await callback.answer("Неверная роль")
        return

    data = await state.get_data()
    user_id = data.get("role_user_id")

    try:
        api_client = BackendAPIClient()
        await api_client.users_update(user_id, role=role_map[selected_role])

        await callback.message.edit_text(f"✅ Роль пользователя успешно изменена на '{role_map[selected_role]}'")
        await callback.answer()
        await state.set_state(UsersState.main)

    except Exception as e:
        logger.error(f"Error updating user role: {e}")
        await callback.message.edit_text(friendly_error(e, "users_role"))
        await callback.answer()

@router.callback_query(F.data == "users_delete")
@require_role("admin", "methodist")
async def users_delete_start(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    current_role = data.get("role", "specialist")

    try:
        api_client = BackendAPIClient()
        users = await api_client.users_get_all()

        if current_role == "methodist":
            users = [u for u in users if u["role"] != "admin"]

        if not users:
            await callback.message.edit_text("Нет доступных пользователей для удаления")
            await callback.answer()
            return

        buttons = []
        for user in users:
            name = user.get("name") or "Не указано"
            role_emoji = {
                "admin": "👑",
                "methodist": "📚",
                "specialist": "👨‍⚕️"
            }.get(user["role"], "❓")

            buttons.append([InlineKeyboardButton(
                text=f"{role_emoji} {name} ({user['phone']})",
                callback_data=f"users_delete_select_{user['id']}"
            )])

        buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="users_back")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback.message.edit_text("Выберите пользователя для удаления:", reply_markup=keyboard)
        await state.set_state(UsersState.delete_select_user)
        await callback.answer()

    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        await callback.message.edit_text(friendly_error(e, "users_list"))
        await callback.answer()

@router.callback_query(F.data.startswith("users_delete_select_"))
async def users_delete_select(callback: CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split("_")[-1])
    await state.update_data(delete_user_id=user_id)

    try:
        api_client = BackendAPIClient()
        user = await api_client.users_get(user_id)

        name = user.get("name") or "Не указано"
        role_emoji = {
            "admin": "👑",
            "methodist": "📚",
            "specialist": "👨‍⚕️"
        }.get(user["role"], "❓")

        buttons = [
            [InlineKeyboardButton(text="✅ Да, удалить", callback_data="users_delete_confirm")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="users_back")]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback.message.edit_text(
            f"⚠️ Вы уверены, что хотите удалить пользователя?\n\n"
            f"{role_emoji} {name} ({user['phone']})\n"
            f"Роль: {user['role']}\n\n"
            f"Это действие нельзя отменить!",
            reply_markup=keyboard
        )
        await state.set_state(UsersState.delete_confirm)
        await callback.answer()

    except Exception as e:
        logger.error(f"Error fetching user: {e}")
        await callback.message.edit_text(friendly_error(e, "users_get"))
        await callback.answer()

@router.callback_query(F.data == "users_delete_confirm")
@require_role("admin", "methodist")
async def users_delete_confirm(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = data.get("delete_user_id")

    try:
        api_client = BackendAPIClient()
        await api_client.users_delete(user_id)

        await callback.message.edit_text("✅ Пользователь успешно удален")
        await callback.answer()
        await state.set_state(UsersState.main)

    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        await callback.message.edit_text(friendly_error(e, "users_delete"))
        await callback.answer()