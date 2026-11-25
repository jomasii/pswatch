from __future__ import annotations


class TelegramClient:
    def __init__(self, token: str, chat_id: str, session) -> None:
        self._token = token
        self._chat_id = chat_id
        self._session = session

    def send(self, text: str) -> bool:
        url = f"https://api.telegram.org/bot{self._token}/sendMessage"
        try:
            response = self._session.post(
                url,
                json={"chat_id": self._chat_id, "text": text, "disable_web_page_preview": False},
                timeout=15,
            )
            return bool(response.ok)
        except Exception:
            return False
