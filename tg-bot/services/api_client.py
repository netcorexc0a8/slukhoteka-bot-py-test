import httpx
from typing import Optional, Dict, Any
from config import settings

class BackendAPIClient:
    def __init__(self):
        self.base_url = settings.BACKEND_URL

    async def auth_login(self, phone: str, platform: str, external_id: str, name: str | None = None) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = {"phone": phone, "platform": platform, "external_id": external_id}
            if name:
                payload["name"] = name
            response = await client.post(
                f"{self.base_url}/api/v1/auth/login",
                json=payload
            )
            response.raise_for_status()
            return response.json()

    async def auth_check(self, platform: str, external_id: str) -> Dict[str, Any] | None:
        """
        Проверяет авторизацию пользователя по platform и external_id
        Возвращает данные пользователя если авторизован, иначе None
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/api/v1/auth/check-auth",
                    params={"platform": platform, "external_id": external_id}
                )
                if response.status_code == 200:
                    return response.json()
                return None
            except Exception:
                return None

    async def auth_check_phone(self, phone: str) -> Dict[str, Any] | None:
        """
        Проверяет существование пользователя по номеру телефона
        Возвращает данные если существует, иначе None
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/api/v1/auth/check-phone",
                    params={"phone": phone}
                )
                if response.status_code == 200:
                    return response.json()
                return None
            except Exception:
                return None

    async def schedule_get(self, date: str, user_id: Optional[int] = None, include_deleted: bool = False) -> list[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            params = {"date": date, "include_deleted": str(include_deleted).lower()}
            if user_id:
                params["user_id"] = str(user_id)
            response = await client.get(
                f"{self.base_url}/api/v1/schedules",
                params=params
            )
            response.raise_for_status()
            return response.json()

    async def schedule_get_all(self, start_date: str, end_date: str, user_id: Optional[int] = None) -> list[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            params = {"start_date": start_date, "end_date": end_date}
            if user_id:
                params["user_id"] = str(user_id)
            response = await client.get(
                f"{self.base_url}/api/v1/schedules/range",
                params=params
            )
            response.raise_for_status()
            return response.json()

    async def schedule_create(self, user_id: int, title: str, start_time: str, end_time: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/api/v1/schedules",
                json={
                    "global_user_id": user_id,
                    "title": title,
                    "start_time": start_time,
                    "end_time": end_time
                }
            )
            response.raise_for_status()
            return response.json()

    async def schedule_update(self, schedule_id: int, **kwargs) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.put(
                f"{self.base_url}/api/v1/schedules/{schedule_id}",
                json=kwargs
            )
            response.raise_for_status()
            return response.json()

    async def schedule_delete(self, schedule_id: int) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(
                f"{self.base_url}/api/v1/schedules/{schedule_id}"
            )
            response.raise_for_status()
            return response.json()

    async def export_excel(self, start_date: str, end_date: str, user_id: Optional[int] = None, current_user_id: int = 0, current_user_role: str = "specialist") -> bytes:
        async with httpx.AsyncClient(timeout=30.0) as client:
            params = {
                "start_date": start_date,
                "end_date": end_date,
                "current_user_id": str(current_user_id),
                "current_user_role": current_user_role
            }
            if user_id:
                params["user_id"] = str(user_id)
            response = await client.get(
                f"{self.base_url}/api/v1/export/excel",
                params=params
            )
            response.raise_for_status()
            return response.content



    async def users_get_all(self, skip: int = 0, limit: int = 100) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/api/v1/users",
                params={"skip": skip, "limit": limit}
            )
            response.raise_for_status()
            return response.json()

    async def users_get(self, user_id: int) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/api/v1/users/{user_id}"
            )
            response.raise_for_status()
            return response.json()

    async def users_update(self, user_id: int, name: Optional[str] = None, role: Optional[str] = None) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = {}
            if name is not None:
                payload["name"] = name
            if role is not None:
                payload["role"] = role
            response = await client.put(
                f"{self.base_url}/api/v1/users/{user_id}",
                json=payload
            )
            response.raise_for_status()
            return response.json()

    async def users_delete(self, user_id: int) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(
                f"{self.base_url}/api/v1/users/{user_id}"
            )
            response.raise_for_status()
            return {}

    async def invite_create(self, role: str, created_by: int) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/api/v1/users/invite",
                json={"role": role, "created_by": created_by}
            )
            response.raise_for_status()
            return response.json()

    async def invite_check(self, code: str) -> Dict[str, Any] | None:
        """Проверяет валидность invite code"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/api/v1/users/invite/check",
                    params={"code": code}
                )
                if response.status_code == 200:
                    return response.json()
                return None
            except Exception:
                return None

    async def invite_use(self, code: str, user_id: int) -> bool:
        """Помечает invite code как использованный"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/v1/users/invite/use",
                    json={"code": code, "user_id": user_id}
                )
                return response.status_code == 200
            except Exception:
                return False

    async def auth_login_with_role(self, phone: str, platform: str, external_id: str, name: str | None = None, role: str = "SPECIALIST") -> Dict[str, Any]:
        """Создаёт пользователя с указанной ролью"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = {
                "phone": phone,
                "platform": platform,
                "external_id": external_id,
                "role": role
            }
            if name:
                payload["name"] = name
            response = await client.post(
                f"{self.base_url}/api/v1/auth/login",
                json=payload
            )
            response.raise_for_status()
            return response.json()

    async def sync_to_yandex(self, file_data: bytes, filename: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            files = {"file": (filename, file_data)}
            response = await client.post(
                f"{self.base_url}/api/v1/sync/yandex",
                files=files
            )
            response.raise_for_status()
            return response.json()

    async def backup_database(self) -> bytes:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.get(
                f"{self.base_url}/api/v1/backup/database"
            )
            response.raise_for_status()
            return response.content

    async def clients_get_all(self, user_id: int) -> list[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/api/v1/clients",
                params={"user_id": user_id}
            )
            response.raise_for_status()
            return response.json()

    async def client_create(self, user_id: int, name: str, phone: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/api/v1/clients",
                json={"global_user_id": user_id, "name": name, "phone": phone}
            )
            response.raise_for_status()
            return response.json()

    async def schedule_create_recurring(self, user_id: int, title: str, start_time: str, end_time: str) -> list[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/api/v1/schedules/recurring",
                json={
                    "global_user_id": user_id,
                    "title": title,
                    "start_time": start_time,
                    "end_time": end_time,
                    "is_recurring": True
                }
            )
            response.raise_for_status()
            return response.json()

    async def schedule_update_series(self, recurrence_group_id: str, **kwargs) -> list[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.put(
                f"{self.base_url}/api/v1/schedules/series/{recurrence_group_id}",
                json=kwargs
            )
            response.raise_for_status()
            return response.json()

    async def schedule_delete_series(self, recurrence_group_id: str, from_date: Optional[str] = None) -> bool:
        params = {}
        if from_date:
            params['from_date'] = from_date

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.delete(
                f"{self.base_url}/api/v1/schedules/series/{recurrence_group_id}",
                params=params
            )
            response.raise_for_status()
            return response.status_code == 204

    async def schedule_move_series(self, recurrence_group_id: str, new_start_time: str, new_end_time: str, from_date: Optional[str] = None) -> list[Dict[str, Any]]:
        params = {
            'new_start_time': new_start_time,
            'new_end_time': new_end_time
        }
        if from_date:
            params['from_date'] = from_date

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/api/v1/schedules/series/{recurrence_group_id}/move",
                params=params
            )
            response.raise_for_status()
            return response.json()

    async def schedule_get_by_id(self, schedule_id: int, include_deleted: bool = False) -> Dict[str, Any]:
        params = {}
        if include_deleted:
            params['include_deleted'] = 'true'

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/api/v1/schedules/{schedule_id}",
                params=params
            )
            response.raise_for_status()
            return response.json()

    async def schedule_get_series(self, recurrence_group_id: str) -> list[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/api/v1/schedules/series/{recurrence_group_id}"
            )
            response.raise_for_status()
            return response.json()
