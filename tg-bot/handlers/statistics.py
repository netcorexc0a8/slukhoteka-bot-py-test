from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from services.api_client import BackendAPIClient
from datetime import datetime, timedelta
import logging

router = Router()
logger = logging.getLogger(__name__)

@router.message(F.text == "📊 Статистика")
async def cmd_statistics(message: Message, state: FSMContext):
    data = await state.get_data()
    role = data.get("role", "specialist")

    if role != "admin":
        await message.answer("У вас нет прав для просмотра статистики")
        from handlers.menu import show_main_menu
        await show_main_menu(message, state)
        return

    try:
        api_client = BackendAPIClient()
        users = await api_client.users_get_all()

        today = datetime.now()
        first_day = today.replace(day=1)
        last_day = (first_day + timedelta(days=32)).replace(day=1) - timedelta(days=1)

        start_date = first_day.strftime("%Y-%m-%d")
        end_date = last_day.strftime("%Y-%m-%d")

        all_schedules = await api_client.schedule_get_all(start_date, end_date)

        current_user_id = data.get("global_user_id")
        my_schedules = [s for s in all_schedules if s["global_user_id"] == current_user_id]

        other_admins = [u for u in users if u["role"] == "admin" and u["id"] != current_user_id]
        admin_schedules = [s for s in all_schedules if s["global_user_id"] in [u["id"] for u in other_admins]]

        methodists = [u for u in users if u["role"] == "methodist"]
        methodist_schedules = [s for s in all_schedules if s["global_user_id"] in [u["id"] for u in methodists]]

        specialists = [u for u in users if u["role"] == "specialist"]
        specialist_schedules = [s for s in all_schedules if s["global_user_id"] in [u["id"] for u in specialists]]

        # Calculate daily and weekly stats
        from collections import defaultdict
        daily_stats = defaultdict(lambda: defaultdict(int))
        weekly_stats = defaultdict(lambda: defaultdict(int))

        user_roles = {u["id"]: u["role"] for u in users}

        for schedule in all_schedules:
            start_time = datetime.fromisoformat(schedule["start_time"])
            date = start_time.date()
            role = user_roles.get(schedule["global_user_id"], "unknown")

            # Daily
            daily_stats[str(date)][role] += 1
            daily_stats[str(date)]["total"] += 1

            # Weekly
            week = f"{date.isocalendar()[0]}-W{date.isocalendar()[1]:02d}"
            weekly_stats[week][role] += 1
            weekly_stats[week]["total"] += 1

        # Get current week stats
        current_week = f"{today.isocalendar()[0]}-W{today.isocalendar()[1]:02d}"
        week_stats = weekly_stats.get(current_week, {})

        text = (
            f"📊 <b>Статистика за {first_day.strftime('%B %Y')}</b>\n\n"
            f"👥 <b>Всего пользователей:</b> {len(users)}\n"
            f"  👑 Админы: {len([u for u in users if u['role'] == 'admin'])}\n"
            f"  📚 Методисты: {len([u for u in users if u['role'] == 'methodist'])}\n"
            f"  👨‍⚕️ Специалисты: {len([u for u in users if u['role'] == 'specialist'])}\n\n"
            f"📅 <b>Всего записей:</b> {len(all_schedules)}\n"
            f"  👤 Мои записи: {len(my_schedules)}\n"
            f"  👑 Записи других админов: {len(admin_schedules)}\n"
            f"  📚 Записи методистов: {len(methodist_schedules)}\n"
            f"  👨‍⚕️ Записи специалистов: {len(specialist_schedules)}\n\n"
            f"📊 <b>За текущую неделю ({current_week}):</b>\n"
            f"  📅 Всего занятий: {week_stats.get('total', 0)}\n"
            f"  👑 Админы: {week_stats.get('admin', 0)}\n"
            f"  📚 Методисты: {week_stats.get('methodist', 0)}\n"
            f"  👨‍⚕️ Специалисты: {week_stats.get('specialist', 0)}\n\n"
            f"📊 <b>За сегодня:</b>\n"
            f"  📅 Всего занятий: {daily_stats.get(str(today.date()), {}).get('total', 0)}\n"
            f"  👑 Админы: {daily_stats.get(str(today.date()), {}).get('admin', 0)}\n"
            f"  📚 Методисты: {daily_stats.get(str(today.date()), {}).get('methodist', 0)}\n"
            f"  👨‍⚕️ Специалисты: {daily_stats.get(str(today.date()), {}).get('specialist', 0)}"
        )

        buttons = [
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="stats_back")]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await message.answer(text, parse_mode="HTML", reply_markup=keyboard)
        await state.set_state("stats_viewing")

    except Exception as e:
        logger.error(f"Error loading statistics: {e}")
        await message.answer(f"Ошибка загрузки статистики: {e}")


@router.callback_query(F.data == "stats_back")
async def stats_back(callback: CallbackQuery, state: FSMContext):
    from handlers.menu import show_main_menu
    await callback.message.delete()
    await show_main_menu(callback.message, state)
    await callback.answer()
