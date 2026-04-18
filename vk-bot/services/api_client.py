import requests
from typing import Optional, Dict, Any
from config import settings

class BackendAPIClient:
    def __init__(self):
        self.base_url = settings.BACKEND_URL

    def auth_login(self, phone: str, platform: str, external_id: str) -> Dict[str, Any]:
        response = requests.post(
            f"{self.base_url}/api/v1/auth/login",
            json={"phone": phone, "platform": platform, "external_id": external_id},
            timeout=30
        )
        response.raise_for_status()
        return response.json()

    def schedule_get(self, date: str, user_id: Optional[int] = None) -> Dict[str, Any]:
        params = {"date": date}
        if user_id:
            params["user_id"] = user_id
        response = requests.get(
            f"{self.base_url}/api/v1/schedules",
            params=params,
            timeout=30
        )
        response.raise_for_status()
        return response.json()

    def schedule_create(self, user_id: int, title: str, start_time: str, end_time: str) -> Dict[str, Any]:
        response = requests.post(
            f"{self.base_url}/api/v1/schedules",
            json={
                "global_user_id": user_id,
                "title": title,
                "start_time": start_time,
                "end_time": end_time
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()
