"""
HTTP-клиент к backend.
Методы для bookings + subscriptions + services + groups.
"""
import httpx
from typing import Optional, Dict, Any, List
from config import settings


class BackendAPIClient:
    def __init__(self):
        self.base_url = settings.BACKEND_URL

    # ------------------------------------------------------------------
    # AUTH
    # ------------------------------------------------------------------
    async def auth_login(self, phone: str, platform: str, external_id: str, name: str | None = None) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = {"phone": phone, "platform": platform, "external_id": external_id}
            if name:
                payload["name"] = name
            response = await client.post(f"{self.base_url}/api/v1/auth/login", json=payload)
            response.raise_for_status()
            return response.json()

    async def auth_login_with_role(self, phone: str, platform: str, external_id: str, name: str | None = None, role: str = "SPECIALIST") -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = {"phone": phone, "platform": platform, "external_id": external_id, "role": role}
            if name:
                payload["name"] = name
            response = await client.post(f"{self.base_url}/api/v1/auth/login", json=payload)
            response.raise_for_status()
            return response.json()

    async def auth_check(self, platform: str, external_id: str) -> Dict[str, Any] | None:
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/api/v1/auth/check-auth",
                    params={"platform": platform, "external_id": external_id},
                )
                if response.status_code == 200:
                    return response.json()
                return None
            except Exception:
                return None

    async def auth_check_phone(self, phone: str) -> Dict[str, Any] | None:
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/api/v1/auth/check-phone",
                    params={"phone": phone},
                )
                if response.status_code == 200:
                    return response.json()
                return None
            except Exception:
                return None

    # ------------------------------------------------------------------
    # SERVICES
    # ------------------------------------------------------------------
    async def services_list(self) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{self.base_url}/api/v1/services")
            response.raise_for_status()
            return response.json()

    # ------------------------------------------------------------------
    # CLIENTS
    # ------------------------------------------------------------------
    async def clients_get_all(self, user_id: int) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/api/v1/clients",
                params={"user_id": user_id},
            )
            response.raise_for_status()
            return response.json()

    async def client_create(
        self, user_id: int, name: str, phone: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"global_user_id": user_id, "name": name}
        if phone:
            payload["phone"] = phone
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/api/v1/clients",
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    # ------------------------------------------------------------------
    # SUBSCRIPTIONS
    # ------------------------------------------------------------------
    async def subscriptions_for_client(
        self, client_id: int, only_usable: bool = False, only_active: bool = False,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"client_id": client_id}
        if only_usable:
            params["only_usable"] = "true"
        if only_active:
            params["only_active"] = "true"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/api/v1/subscriptions",
                params=params,
            )
            response.raise_for_status()
            return response.json()

    async def subscription_create(
        self,
        client_id: int,
        service_id: int,
        assigned_specialist_id: Optional[int] = None,
        group_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "client_id": client_id,
            "service_id": service_id,
        }
        if assigned_specialist_id is not None:
            payload["assigned_specialist_id"] = assigned_specialist_id
        if group_id is not None:
            payload["group_id"] = group_id
        if notes:
            payload["notes"] = notes
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/api/v1/subscriptions",
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def subscription_update(self, subscription_id: int, **kwargs) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.put(
                f"{self.base_url}/api/v1/subscriptions/{subscription_id}",
                json=kwargs,
            )
            response.raise_for_status()
            return response.json()

    async def subscription_delete(self, subscription_id: int) -> bool:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(
                f"{self.base_url}/api/v1/subscriptions/{subscription_id}"
            )
            return response.status_code == 204

    # ------------------------------------------------------------------
    # GROUPS (для алгоритмики)
    # ------------------------------------------------------------------
    async def groups_list(self, service_id: Optional[int] = None) -> List[Dict[str, Any]]:
        params = {}
        if service_id is not None:
            params["service_id"] = service_id
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/api/v1/groups",
                params=params,
            )
            response.raise_for_status()
            return response.json()

    async def group_get(self, group_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/api/v1/groups/{group_id}"
            )
            response.raise_for_status()
            return response.json()

    async def group_create(
        self, name: str, service_id: int,
        max_participants: int = 6,
        day_of_week: Optional[int] = None, time: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "name": name,
            "service_id": service_id,
            "max_participants": max_participants,
        }
        if day_of_week is not None:
            payload["day_of_week"] = day_of_week
        if time is not None:
            payload["time"] = time
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/api/v1/groups",
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def group_update(self, group_id: str, **kwargs) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.put(
                f"{self.base_url}/api/v1/groups/{group_id}",
                json=kwargs,
            )
            response.raise_for_status()
            return response.json()

    async def group_delete(self, group_id: str) -> bool:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(
                f"{self.base_url}/api/v1/groups/{group_id}"
            )
            return response.status_code == 204

    async def group_add_participant(self, group_id: str, client_id: int) -> bool:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/api/v1/groups/{group_id}/participants/{client_id}"
            )
            return response.status_code in (200, 201)

    async def group_remove_participant(self, group_id: str, client_id: int) -> bool:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(
                f"{self.base_url}/api/v1/groups/{group_id}/participants/{client_id}"
            )
            return response.status_code == 204

    # ------------------------------------------------------------------
    # BOOKINGS
    # ------------------------------------------------------------------
    async def bookings_for_date(
        self, date: str, specialist_id: Optional[int] = None, client_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"date": date}
        if specialist_id is not None:
            params["specialist_id"] = specialist_id
        if client_id is not None:
            params["client_id"] = client_id
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/api/v1/bookings",
                params=params,
            )
            response.raise_for_status()
            return response.json()

    async def bookings_for_range(
        self, start_date: str, end_date: str,
        specialist_id: Optional[int] = None, client_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"start_date": start_date, "end_date": end_date}
        if specialist_id is not None:
            params["specialist_id"] = specialist_id
        if client_id is not None:
            params["client_id"] = client_id
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/api/v1/bookings",
                params=params,
            )
            response.raise_for_status()
            return response.json()

    async def booking_create(
        self,
        subscription_id: int,
        start_time: str,
        end_time: str,
        specialist_id: Optional[int] = None,
        co_specialist_ids: Optional[List[int]] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "subscription_id": subscription_id,
            "start_time": start_time,
            "end_time": end_time,
        }
        if specialist_id is not None:
            payload["specialist_id"] = specialist_id
        if co_specialist_ids:
            payload["co_specialist_ids"] = co_specialist_ids
        if notes:
            payload["notes"] = notes
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/api/v1/bookings",
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def booking_delete(self, booking_id: int, actor_id: Optional[int] = None) -> bool:
        params = {}
        if actor_id is not None:
            params["actor_id"] = actor_id
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(
                f"{self.base_url}/api/v1/bookings/{booking_id}",
                params=params,
            )
            return response.status_code == 204

    async def booking_update(self, booking_id: int, **kwargs) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.put(
                f"{self.base_url}/api/v1/bookings/{booking_id}",
                json=kwargs,
            )
            response.raise_for_status()
            return response.json()

    async def booking_create_recurring(
            self,
            subscription_id: int,
            first_start_time: str,
            duration_minutes: int = 60,
            specialist_id: Optional[int] = None,
            co_specialist_ids: Optional[List[int]] = None,
            notes: Optional[str] = None,
        ) -> Dict[str, Any]:
            """Создаёт серию броней — по 1 в неделю до конца абонемента."""
            payload: Dict[str, Any] = {
                "subscription_id": subscription_id,
                "first_start_time": first_start_time,
                "duration_minutes": duration_minutes,
            }
            if specialist_id is not None:
                payload["specialist_id"] = specialist_id
            if co_specialist_ids:
                payload["co_specialist_ids"] = co_specialist_ids
            if notes:
                payload["notes"] = notes
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/bookings/recurring",
                    json=payload,
                )
                response.raise_for_status()
                return response.json()

    async def booking_group_move(
        self,
        group_id: str,
        old_start: str,
        new_start: str,
        duration_minutes: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Переносит всё групповое занятие на новое время."""
        payload: Dict[str, Any] = {
            "group_id": group_id,
            "old_start": old_start,
            "new_start": new_start,
        }
        if duration_minutes is not None:
            payload["duration_minutes"] = duration_minutes
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/api/v1/bookings/group/move",
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    # ------------------------------------------------------------------
    # USERS
    # ------------------------------------------------------------------
    async def users_get_all(self, skip: int = 0, limit: int = 100) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/api/v1/users",
                params={"skip": skip, "limit": limit},
            )
            response.raise_for_status()
            return response.json()

    async def users_get(self, user_id: int) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{self.base_url}/api/v1/users/{user_id}")
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
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def users_delete(self, user_id: int) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(f"{self.base_url}/api/v1/users/{user_id}")
            response.raise_for_status()
            return {}

    # ------------------------------------------------------------------
    # INVITES
    # ------------------------------------------------------------------
    async def invite_create(self, role: str, created_by: int) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/api/v1/users/invite",
                json={"role": role, "created_by": created_by},
            )
            response.raise_for_status()
            return response.json()

    async def invite_check(self, code: str) -> Dict[str, Any] | None:
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/api/v1/users/invite/check",
                    params={"code": code},
                )
                if response.status_code == 200:
                    return response.json()
                return None
            except Exception:
                return None

    async def invite_use(self, code: str, user_id: int) -> bool:
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/v1/users/invite/use",
                    json={"code": code, "user_id": user_id},
                )
                return response.status_code == 200
            except Exception:
                return False

    # ------------------------------------------------------------------
    # EXPORT, SYNC, BACKUP
    # ------------------------------------------------------------------
    async def export_excel(
        self, start_date: str, end_date: str,
        user_id: Optional[int] = None,
        current_user_id: int = 0, current_user_role: str = "specialist",
    ) -> bytes:
        async with httpx.AsyncClient(timeout=30.0) as client:
            params = {
                "start_date": start_date,
                "end_date": end_date,
                "current_user_id": str(current_user_id),
                "current_user_role": current_user_role,
            }
            if user_id:
                params["user_id"] = str(user_id)
            response = await client.get(
                f"{self.base_url}/api/v1/export/excel",
                params=params,
            )
            response.raise_for_status()
            return response.content

    async def sync_to_yandex(self, file_data: bytes, filename: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            files = {"file": (filename, file_data)}
            response = await client.post(
                f"{self.base_url}/api/v1/sync/yandex",
                files=files,
            )
            response.raise_for_status()
            return response.json()

    async def backup_database(self) -> bytes:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.get(f"{self.base_url}/api/v1/backup/database")
            response.raise_for_status()
            return response.content
