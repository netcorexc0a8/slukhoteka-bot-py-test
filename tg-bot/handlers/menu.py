from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

router = Router()


def _build_keyboard(role: str) -> ReplyKeyboardMarkup:
    if role == "admin":
        buttons = [
            [KeyboardButton(text="👤 Пользователи"), KeyboardButton(text="📅 Расписание")],
            [KeyboardButton(text="📈 Статистика"), KeyboardButton(text="📊 Экспорт Excel")],
            [KeyboardButton(text="📆 Экспорт ICS"), KeyboardButton(text="☁️ Синхр. Я.Диск")],
            [KeyboardButton(text="💾 Резерв. копия БД"), KeyboardButton(text="ℹ️ Помощь")],
        ]
    elif role == "methodist":
        buttons = [
            [KeyboardButton(text="👤 Пользователи"), KeyboardButton(text="📅 Расписание")],
            [KeyboardButton(text="📊 Экспорт Excel"), KeyboardButton(text="☁️ Синхр. Я.Диск")],
            [KeyboardButton(text="ℹ️ Помощь")],
        ]
    else:
        buttons = [
            [KeyboardButton(text="📅 Расписание"), KeyboardButton(text="📊 Экспорт Excel")],
            [KeyboardButton(text="ℹ️ Помощь")],
        ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


async def show_main_menu(message: Message, state: FSMContext):
    data = await state.get_data()
    role = data.get("role", "specialist")
    await message.answer("Главное меню:", reply_markup=_build_keyboard(role))