import requests
import json
import random
from typing import Optional, Dict, Any
from config import settings

class VKAPIClient:
    def __init__(self):
        self.token = settings.VK_BOT_TOKEN
        self.group_id = settings.VK_GROUP_ID
        self.api_version = "5.199"
        self.server = None
        self.key = None
        self.ts = None

    def get_long_poll_server(self) -> Optional[Dict[str, Any]]:
        url = "https://api.vk.com/method/groups.getLongPollServer"
        params = {
            "group_id": self.group_id,
            "access_token": self.token,
            "v": self.api_version
        }
        response = requests.get(url, params=params)
        data = response.json()

        if "response" in data:
            self.server = data["response"]["server"]
            self.key = data["response"]["key"]
            self.ts = data["response"]["ts"]
            return data["response"]
        return None

    def send_message(
        self,
        peer_id: int,
        message: str,
        keyboard: Optional[dict] = None
    ) -> Dict[str, Any]:
        url = "https://api.vk.com/method/messages.send"
        params = {
            "access_token": self.token,
            "v": self.api_version,
            "peer_id": peer_id,
            "message": message,
            "random_id": random.randint(1, 1000000)
        }
        if keyboard:
            params["keyboard"] = json.dumps(keyboard)

        response = requests.get(url, params=params)
        return response.json()

    def edit_message(
        self,
        peer_id: int,
        conversation_message_id: int,
        message: str,
        keyboard: Optional[dict] = None
    ) -> Dict[str, Any]:
        url = "https://api.vk.com/method/messages.edit"
        params = {
            "access_token": self.token,
            "v": self.api_version,
            "peer_id": peer_id,
            "conversation_message_id": conversation_message_id,
            "message": message
        }
        if keyboard:
            params["keyboard"] = json.dumps(keyboard)

        response = requests.get(url, params=params)
        return response.json()

    def show_snackbar(
        self,
        event_id: str,
        user_id: int,
        peer_id: int,
        text: str
    ) -> Dict[str, Any]:
        url = "https://api.vk.com/method/messages.sendMessageEventAnswer"
        params = {
            "access_token": self.token,
            "v": self.api_version,
            "event_id": event_id,
            "user_id": user_id,
            "peer_id": peer_id,
            "event_data": json.dumps({"type": "show_snackbar", "text": text})
        }
        response = requests.get(url, params=params)
        return response.json()

    def get_user_info(self, user_id: int) -> Optional[Dict[str, Any]]:
        url = "https://api.vk.com/method/users.get"
        params = {
            "access_token": self.token,
            "v": self.api_version,
            "user_ids": user_id,
            "fields": "contacts,phone"
        }
        response = requests.get(url, params=params)
        data = response.json()
        
        if "response" in data and len(data["response"]) > 0:
            return data["response"][0]
        return None

    def poll_updates(self, callback):
        if not self.get_long_poll_server():
            raise Exception("Не удалось подключиться к Long Poll серверу")

        try:
            while True:
                poll_url = f"{self.server}?act=a_check&key={self.key}&ts={self.ts}&wait=25"
                response = requests.get(poll_url, timeout=30)
                data = response.json()

                if "failed" in data:
                    if data["failed"] == 1:
                        self.ts = data["ts"]
                    else:
                        self.get_long_poll_server()
                    continue

                self.ts = data.get("ts", self.ts)

                updates = data.get("updates", [])
                for update in updates:
                    callback(update)

        except KeyboardInterrupt:
            print("Бот остановлен")
        except Exception as e:
            print(f"Ошибка: {e}")
            raise
