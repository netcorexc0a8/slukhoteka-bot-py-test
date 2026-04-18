from typing import List, Optional
from datetime import datetime, timedelta
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
from app.models.schedule import Schedule
from app.models.user import GlobalUser, Role
from sqlalchemy.orm import Session, joinedload
from collections import defaultdict

class ExcelExportService:
    def _merge_same_cells(self, ws, start_row, end_row, column_idx, alignment):
        current_value = None
        merge_start = None
        
        for row in range(start_row, end_row + 1):
            cell = ws.cell(row=row, column=column_idx)
            cell_value = cell.value
            if cell_value != current_value:
                if merge_start is not None and merge_start != row - 1:
                    ws.merge_cells(start_row=merge_start, start_column=column_idx, end_row=row - 1, end_column=column_idx)
                merge_start = row
                current_value = cell_value
        
        if merge_start is not None and merge_start != end_row:
            ws.merge_cells(start_row=merge_start, start_column=column_idx, end_row=end_row, end_column=column_idx)
        
        for row in range(start_row, end_row + 1):
            cell = ws.cell(row=row, column=column_idx)
            cell.alignment = alignment

    def _get_platform_by_schedule(self, db: Session, schedule: Schedule) -> str:
        from app.models.user import PlatformUser
        platform_user = db.query(PlatformUser).filter(
            PlatformUser.global_user_id == schedule.global_user_id
        ).first()
        if platform_user:
            return "Telegram" if platform_user.platform == "telegram" else "VK"
        return ""

    def _write_sheet(self, ws, schedules, db: Session):
        headers = ["Дата записи", "День недели", "Время записи", "Клиент", "Специалист", "Платформа записи", "Дата создания", "Дата обновления"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal='center', vertical='center')

        days_of_week = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
        
        for row, schedule in enumerate(schedules, 2):
            ws.cell(row=row, column=1, value=schedule.start_time.strftime("%d.%m.%Y"))
            ws.cell(row=row, column=2, value=days_of_week[schedule.start_time.weekday()])
            ws.cell(row=row, column=3, value=schedule.start_time.strftime('%H:%M'))
            ws.cell(row=row, column=4, value=schedule.title)
            ws.cell(row=row, column=5, value=schedule.global_user.name or schedule.global_user.phone)
            ws.cell(row=row, column=6, value=self._get_platform_by_schedule(db, schedule))
            ws.cell(row=row, column=7, value=schedule.created_at.strftime("%d.%m.%Y %H:%M"))
            ws.cell(row=row, column=8, value=schedule.updated_at.strftime("%d.%m.%Y %H:%M"))

        if schedules:
            end_row = len(schedules) + 1
            self._merge_same_cells(ws, 2, end_row, 1, Alignment(horizontal='left', vertical='top'))
            
            # Merge day of week cells only within the same day
            from collections import defaultdict
            date_groups = defaultdict(list)
            for row, schedule in enumerate(schedules, 2):
                date_str = schedule.start_time.strftime("%d.%m.%Y")
                date_groups[date_str].append(row)
            
            for date, rows in date_groups.items():
                if len(rows) > 1:
                    ws.merge_cells(start_row=rows[0], start_column=2, end_row=rows[-1], end_column=2)
                    for r in rows:
                        ws.cell(r, 2).alignment = Alignment(horizontal='left', vertical='top')

        for col in ws.columns:
            max_length = 0
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            ws.column_dimensions[col[0].column_letter].width = max_length + 2

    def export_statistics(
        self,
        schedules: List[Schedule],
        users: List[GlobalUser],
        db: Session
    ) -> bytes:
        from collections import defaultdict
        from datetime import datetime, timedelta

        wb = Workbook()

        # Prepare data structures
        user_roles = {user.id: user.role.value for user in users}
        daily_stats = defaultdict(lambda: defaultdict(int))  # date -> role -> count
        weekly_stats = defaultdict(lambda: defaultdict(int))  # week -> role -> count

        for schedule in schedules:
            date = schedule.start_time.date()
            role = user_roles.get(schedule.global_user_id, 'unknown')

            # Daily stats
            daily_stats[str(date)][role] += 1
            daily_stats[str(date)]['total'] += 1

            # Weekly stats (ISO week)
            week = f"{date.isocalendar()[0]}-W{date.isocalendar()[1]:02d}"
            weekly_stats[week][role] += 1
            weekly_stats[week]['total'] += 1

        # Daily stats sheet
        ws_daily = wb.create_sheet("Ежедневная статистика")
        headers = ["Дата", "Всего занятий", "Админы", "Методисты", "Специалисты"]
        for col, header in enumerate(headers, 1):
            cell = ws_daily.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal='center')

        row = 2
        for date_str in sorted(daily_stats.keys()):
            stats = daily_stats[date_str]
            ws_daily.cell(row=row, column=1, value=date_str)
            ws_daily.cell(row=row, column=2, value=stats.get('total', 0))
            ws_daily.cell(row=row, column=3, value=stats.get('admin', 0))
            ws_daily.cell(row=row, column=4, value=stats.get('methodist', 0))
            ws_daily.cell(row=row, column=5, value=stats.get('specialist', 0))
            row += 1

        # Weekly stats sheet
        ws_weekly = wb.create_sheet("Недельная статистика")
        headers = ["Неделя", "Всего занятий", "Админы", "Методисты", "Специалисты"]
        for col, header in enumerate(headers, 1):
            cell = ws_weekly.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal='center')

        row = 2
        for week in sorted(weekly_stats.keys()):
            stats = weekly_stats[week]
            ws_weekly.cell(row=row, column=1, value=week)
            ws_weekly.cell(row=row, column=2, value=stats.get('total', 0))
            ws_weekly.cell(row=row, column=3, value=stats.get('admin', 0))
            ws_weekly.cell(row=row, column=4, value=stats.get('methodist', 0))
            ws_weekly.cell(row=row, column=5, value=stats.get('specialist', 0))
            row += 1

        # Auto-adjust column widths
        for ws in [ws_daily, ws_weekly]:
            for col in ws.columns:
                max_length = 0
                for cell in col:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                ws.column_dimensions[col[0].column_letter].width = max_length + 2

        from io import BytesIO
        output = BytesIO()
        wb.save(output)
        return output.getvalue()

    def export_schedule(
        self,
        schedules: List[Schedule],
        current_user: GlobalUser,
        db: Session
    ) -> bytes:
        wb = Workbook()
        ws_general = wb.active
        ws_general.title = "Общее расписание"
        self._write_sheet(ws_general, schedules, db)

        # Add statistics sheets
        self._add_statistics_sheets(wb, schedules, db)

        specialist_schedules = defaultdict(list)
        for schedule in schedules:
            if schedule.global_user:
                specialist_name = schedule.global_user.name or schedule.global_user.phone
                specialist_schedules[specialist_name].append(schedule)

        for specialist_name, spec_schedules in specialist_schedules.items():
            ws_spec = wb.create_sheet(specialist_name)
            self._write_sheet(ws_spec, spec_schedules, db)

        from io import BytesIO
        output = BytesIO()
        wb.save(output)
        return output.getvalue()

    def _add_statistics_sheets(self, wb: Workbook, schedules: List[Schedule], db: Session):
        from collections import defaultdict

        # Get all users for role mapping
        from app.crud.user import get_all_users
        users = get_all_users(db)

        # Prepare data structures
        daily_by_user = defaultdict(lambda: defaultdict(int))
        weekly_by_user = defaultdict(lambda: defaultdict(int))

        for schedule in schedules:
            if not schedule.global_user:
                continue
            date = schedule.start_time.date()
            user_name = schedule.global_user.name or schedule.global_user.phone

            # Daily by user
            daily_by_user[user_name][str(date)] += 1

            # Weekly by user
            week = f"{date.isocalendar()[0]}-W{date.isocalendar()[1]:02d}"
            weekly_by_user[user_name][week] += 1

        # Filter users to only include those with records
        users_with_records = set()
        users_with_records.update(daily_by_user.keys())
        users_with_records.update(weekly_by_user.keys())
        user_names = [user.name or user.phone for user in users if (user.name or user.phone) in users_with_records]

        # Create combined daily-weekly statistics sheet
        ws_combined = wb.create_sheet("Статистика по дням-неделям")

        # Daily statistics table (left side)
        daily_dates = sorted(set(date for user_data in daily_by_user.values() for date in user_data.keys()))
        if daily_dates:
            # Headers for daily table
            ws_combined.cell(row=1, column=1, value="Дата").font = Font(bold=True)
            for col, user_name in enumerate(user_names, 2):
                ws_combined.cell(row=1, column=col, value=user_name).font = Font(bold=True)
            # Add "Всего занятий" column
            total_col = len(user_names) + 2
            ws_combined.cell(row=1, column=total_col, value="Всего занятий").font = Font(bold=True)

            # Data for daily table
            for row, date_str in enumerate(daily_dates, 2):
                ws_combined.cell(row=row, column=1, value=date_str)
                daily_total = 0
                for col, user_name in enumerate(user_names, 2):
                    count = daily_by_user[user_name].get(date_str, 0)
                    ws_combined.cell(row=row, column=col, value=count)
                    daily_total += count
                ws_combined.cell(row=row, column=total_col, value=daily_total)

        # Weekly statistics table (right side, with 2 empty columns gap)
        weekly_weeks = sorted(set(week for user_data in weekly_by_user.values() for week in user_data.keys()))
        if weekly_weeks:
            start_col = len(user_names) + 5  # 2 columns gap + 1 for daily total + 2 for spacing

            # Headers for weekly table
            ws_combined.cell(row=1, column=start_col, value="Неделя").font = Font(bold=True)
            for col, user_name in enumerate(user_names, start_col + 1):
                ws_combined.cell(row=1, column=col, value=user_name).font = Font(bold=True)
            # Add "Всего занятий" column for weekly
            weekly_total_col = start_col + len(user_names) + 1
            ws_combined.cell(row=1, column=weekly_total_col, value="Всего занятий").font = Font(bold=True)

            # Data for weekly table
            for row, week in enumerate(weekly_weeks, 2):
                ws_combined.cell(row=row, column=start_col, value=week)
                weekly_total = 0
                for col, user_name in enumerate(user_names, start_col + 1):
                    count = weekly_by_user[user_name].get(week, 0)
                    ws_combined.cell(row=row, column=col, value=count)
                    weekly_total += count
                ws_combined.cell(row=row, column=weekly_total_col, value=weekly_total)

        # Auto-adjust column widths
        for col in ws_combined.columns:
            max_length = 0
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            ws_combined.column_dimensions[col[0].column_letter].width = max_length + 2
