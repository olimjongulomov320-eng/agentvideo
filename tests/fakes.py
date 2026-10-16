# -*- coding: utf-8 -*-
"""fakes.py — minimal stand-ins for Telegram and network objects.

These let the bot be exercised without touching the Telegram API and without
sending a single real message. Nothing here performs I/O.
"""
from typing import Any, Dict, List, Optional


class FakeMessage(object):
    def __init__(self, text: str = "", document: Optional[Any] = None):
        self.text = text
        self.document = document
        self.sent: List[Dict[str, Any]] = []
        self.edits: List[str] = []

    async def reply_text(self, text: str, **kwargs: Any):
        self.sent.append({"text": text, "kwargs": kwargs})
        return FakeMessage(text)

    async def edit_message_text(self, text: str, **kwargs: Any):
        self.edits.append(text)
        return FakeMessage(text)


class FakeUser(object):
    def __init__(self, user_id: int, first_name: str = "Tester"):
        self.id = user_id
        self.first_name = first_name


class FakeChat(object):
    def __init__(self, chat_id: int):
        self.id = chat_id


class FakeQuery(object):
    def __init__(self, data: str):
        self.data = data
        self.answers: List[str] = []
        self.message = FakeMessage()

    async def answer(self, text: str = "", **kwargs: Any):
        self.answers.append(text)

    async def edit_message_text(self, text: str, **kwargs: Any):
        self.message.edits.append(text)
        return FakeMessage(text)


class FakeDocument(object):
    def __init__(self, file_name: str, file_size: int = 1024, file_id: str = "fid"):
        self.file_name = file_name
        self.file_size = file_size
        self.file_id = file_id


class FakeUpdate(object):
    def __init__(self, update_id: int = 1, user_id: int = 1, chat_id: int = 1,
                 text: str = "", args: Optional[List[str]] = None,
                 document: Optional[FakeDocument] = None,
                 callback_data: Optional[str] = None):
        self.update_id = update_id
        self.effective_user = FakeUser(user_id)
        self.effective_chat = FakeChat(chat_id)
        self.effective_message = FakeMessage(text, document)
        self.message = self.effective_message
        self.callback_query = FakeQuery(callback_data) if callback_data else None

    # PTB handlers are async; the fakes are not, so no awaits needed.


class FakeContext(object):
    def __init__(self, args: Optional[List[str]] = None, bot: Any = None):
        self.args = args or []
        self.bot = bot or FakeBot()


class FakeBot(object):
    def __init__(self):
        self.documents: List[Dict[str, Any]] = []
        self.messages: List[Dict[str, Any]] = []

    async def send_message(self, chat_id: int, text: str, **kwargs: Any):
        self.messages.append({"chat_id": chat_id, "text": text, "kwargs": kwargs})
        return FakeMessage(text)

    async def send_document(self, chat_id: int, document: Any, **kwargs: Any):
        self.documents.append({"chat_id": chat_id, "name": kwargs.get("filename")})
        return FakeMessage()

    async def get_file(self, file_id: str):
        return FakeFile()

    async def set_my_commands(self, commands):
        return True


class FakeFile(object):
    async def download_to_drive(self, custom_path: str):
        with open(custom_path, "wb") as fh:
            fh.write(b"fake-upload")
        return custom_path


def html_pages(pages: Dict[str, str]):
    """Build a fetcher returning canned pages; unknown URLs 404."""
    from agent_system.research import FetchResult, SOURCE_ERROR, SOURCE_INSPECTED

    def fetcher(url: str) -> FetchResult:
        if url in pages:
            return FetchResult(True, 200, pages[url], SOURCE_INSPECTED,
                               "fetched %d bytes" % len(pages[url]), url)
        if url.rstrip("/") in pages:
            body = pages[url.rstrip("/")]
            return FetchResult(True, 200, body, SOURCE_INSPECTED,
                               "fetched %d bytes" % len(body), url)
        return FetchResult(False, 404, "", SOURCE_ERROR, "HTTP 404", url)

    return fetcher
