import requests

from ps5watch.telegram import TelegramClient


class FakeResponse:
    def __init__(self, status=200):
        self.status_code = status

    @property
    def ok(self):
        return self.status_code == 200


class FakeSession:
    def __init__(self, response=None, exc=None):
        self.calls = []
        self.response = response or FakeResponse()
        self.exc = exc

    def post(self, url, json=None, timeout=None):
        self.calls.append((url, json))
        if self.exc:
            raise self.exc
        return self.response


def test_send_posts_to_bot_api():
    session = FakeSession()
    ok = TelegramClient("TOKEN", "42", session).send("oi")
    assert ok is True
    url, payload = session.calls[0]
    assert url == "https://api.telegram.org/botTOKEN/sendMessage"
    assert payload["chat_id"] == "42" and payload["text"] == "oi"


def test_send_returns_false_on_http_error():
    session = FakeSession(response=FakeResponse(500))
    assert TelegramClient("T", "1", session).send("x") is False


def test_send_returns_false_on_exception():
    session = FakeSession(exc=requests.ConnectionError("boom"))
    assert TelegramClient("T", "1", session).send("x") is False
