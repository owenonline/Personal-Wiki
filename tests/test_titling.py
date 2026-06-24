from pkb.titling import generate_chat_title


class _Block:
    def __init__(self, text: str):
        self.text = text


class _Resp:
    def __init__(self, text: str):
        self.content = [_Block(text)]


class _Messages:
    def __init__(self, outer):
        self._outer = outer

    def create(self, **kwargs):
        self._outer.calls.append(kwargs)
        return _Resp(self._outer.text)


class _Beta:
    def __init__(self, outer):
        self._outer = outer

    @property
    def messages(self):
        return _Messages(self._outer)


class _FakeClient:
    def __init__(self, text: str):
        self.text = text
        self.calls: list[dict] = []

    @property
    def beta(self):
        return _Beta(self)


def test_returns_clean_stripped_title():
    client = _FakeClient('  "Reading list"  ')
    title = generate_chat_title(
        client,
        "claude-haiku-4-5",
        [
            {"role": "user", "content": "books I want to read"},
            {"role": "assistant", "content": "Added them."},
        ],
    )
    assert title == "Reading list"
    assert client.calls[0]["model"] == "claude-haiku-4-5"


def test_no_llm_call_when_no_messages():
    client = _FakeClient("ignored")
    assert generate_chat_title(client, "m", []) is None
    assert client.calls == []


def test_errors_are_swallowed():
    class Boom:
        @property
        def beta(self):
            raise RuntimeError("model unavailable")

    assert generate_chat_title(Boom(), "m", [{"role": "user", "content": "hi"}]) is None
