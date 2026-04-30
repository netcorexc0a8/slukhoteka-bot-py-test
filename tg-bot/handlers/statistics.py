from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from services.api_client import BackendAPIClient
from datetime import datetime, timedelta
from collections import defaultdict
import logging

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text.in_(["📊 Статистика", "📈 Статистика"]))
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
        users_resp = await api_client.users_get_all()
        # users_get_all может возвращать либо список, либо dict с "users"
        users = users_resp if isinstance(users_resp, list) else users_resp.get("users", [])

        today = datetime.now()
        first_day = today.replace(day=1)
        last_day = (first_day + timedelta(days=32)).replace(day=1) - timedelta(days=1)

        start_date = first_day.strftime("%Y-%m-%d")
        end_date = last_day.strftime("%Y-%m-%d")

        all_bookings = await api_client.bookings_for_range(start_date, end_date)
        # Не считаем удалённые и отменённые
        all_bookings = [
            b for b in all_bookings
            if not b.get("deleted_at")
            and b.get("status") not in ("cancelled", "specialist_cancelled")
        ]

        current_user_id = data.get("global_user_id")
        my_bookings = [b for b in all_bookings if b.get("specialist_id") == current_user_id]

        other_admins = [u for u in users if u.get("role") == "admin" and u["id"] != current_user_id]
        admin_ids = {u["id"] for u in other_admins}
        admin_bookings = [b for b in all_bookings if b.get("specialist_id") in admin_ids]

        methodists = [u for u in users if u.get("role") == "methodist"]
        methodist_ids = {u["id"] for u in methodists}
        methodist_bookings = [b for b in all_bookings if b.get("specialist_id") in methodist_ids]

        specialists = [u for u in users if u.get("role") == "specialist"]
        specialist_ids = {u["id"] for u in specialists}
        specialist_bookings = [b for b in all_bookings if b.get("specialist_id") in specialist_ids]

        daily_stats = defaultdict(lambda: defaultdict(int))
        weekly_stats = defaultdict(lambda: defaultdict(int))
        user_roles = {u["id"]: u.get("role", "unknown") for u in users}

        for b in all_bookings:
            try:
                start_time = datetime.fromisoformat(b["start_time"].replace("Z", "+00:00"))
            except Exception:
                continue
            date = start_time.date()
            r = user_roles.get(b.get("specialist_id"), "unknown")

            daily_stats[str(date)][r] += 1
            daily_stats[str(date)]["total"] += 1

            week = f"{date.isocalendar()[0]}-W{date.isocalendar()[1]:02d}"
            weekly_stats[week][r] += 1
            weekly_stats[week]["total"] += 1

        current_week = f"{today.isocalendar()[0]}-W{today.isocalendar()[1]:02d}"
        week_stats = weekly_stats.get(current_week, {})
        today_stats = daily_stats.get(str(today.date()), {})

        text = (
            f"📊 <b>Статистика за {first_day.strftime('%B %Y')}</b>\n\n"
            f"👥 <b>Всего пользователей:</b> {len(users)}\n"
            f"  👑 Админы: {len([u for u in users if u.get('role') == 'admin'])}\n"
            f"  📚 Методисты: {len([u for u in users if u.get('role') == 'methodist'])}\n"
            f"  👨‍⚕️ Специалисты: {len([u for u in users if u.get('role') == 'specialist'])}\n\n"
            f"📅 <b>Всего записей:</b> {len(all_bookings)}\n"
            f"  👤 Мои записи: {len(my_bookings)}\n"
            f"  👑 Записи других админов: {len(admin_bookings)}\n"
            f"  📚 Записи методистов: {len(methodist_bookings)}\n"
            f"  👨‍⚕️ Записи специалистов: {len(specialist_bookings)}\n\n"
            f"📊 <b>За текущую неделю ({current_week}):</b>\n"
            f"  📅 Всего занятий: {week_stats.get('total', 0)}\n"
            f"  👑 Админы: {week_stats.get('admin', 0)}\n"
            f"  📚 Методисты: {week_stats.get('methodist', 0)}\n"
            f"  👨‍⚕️ Специалисты: {week_stats.get('specialist', 0)}\n\n"
            f"📊 <b>За сегодня:</b>\n"
            f"  📅 Всего занятий: {today_stats.get('total', 0)}\n"
            f"  👑 Админы: {today_stats.get('admin', 0)}\n"
            f"  📚 Методисты: {today_stats.get('methodist', 0)}\n"
            f"  👨‍⚕️ Специалисты: {today_stats.get('specialist', 0)}"
        )

        buttons = [[InlineKeyboardButton(text="⬅️ Назад", callback_data="stats_back")]]
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
