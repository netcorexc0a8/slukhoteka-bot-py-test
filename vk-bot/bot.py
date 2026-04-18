from datetime import datetime
from config import settings
from services.vk_api import VKAPIClient
from handlers.main import process_message, process_callback

vk_api = VKAPIClient()

def handle_update(update):
    if update.get("type") == "message_new":
        message_data = update.get("object", {}).get("message", {})
        from_id = message_data.get("from_id")
        peer_id = message_data.get("peer_id")
        text = message_data.get("text", "")

        if text:
            import asyncio
            asyncio.run(process_message(from_id, peer_id, text, vk_api))

    elif update.get("type") == "message_event":
        event_data = update.get("object", {})
        user_id = event_data.get("user_id")
        peer_id = event_data.get("peer_id")
        event_id = event_data.get("event_id")
        conversation_message_id = event_data.get("conversation_message_id")
        payload = event_data.get("payload")

        import asyncio
        asyncio.run(process_callback(peer_id, user_id, event_id, conversation_message_id, payload, vk_api))

if __name__ == "__main__":
    print("Запуск VK бота Слухотека...")
    vk_api.poll_updates(handle_update)
