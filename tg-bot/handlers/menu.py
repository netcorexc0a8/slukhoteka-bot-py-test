from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

router = Router()


async def show_main_menu(message: Message, state: FSMContext):
    data = await state.get_data()
    role = data.get("role", "specialist")

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

    keyboard = ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
    )

    await message.answer("Главное меню:", reply_markup=keyboard)
