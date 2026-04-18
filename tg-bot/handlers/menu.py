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
            [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="📊 Экспорт Excel")],
            [KeyboardButton(text="📅 Экспорт ICS"), KeyboardButton(text="🔄 Синхронизация")],
            [KeyboardButton(text="💾 Резерв. копия БД")]
        ]
    elif role == "methodist":
        buttons = [
            [KeyboardButton(text="👤 Пользователи"), KeyboardButton(text="📅 Расписание")],
            [KeyboardButton(text="📊 Экспорт Excel"), KeyboardButton(text="🔄 Синхронизация")]
        ]
    else:
        buttons = [
            [KeyboardButton(text="📅 Расписание"), KeyboardButton(text="📊 Экспорт Excel")]
        ]

    keyboard = ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True
    )

    await message.answer("Главное меню:", reply_markup=keyboard)









