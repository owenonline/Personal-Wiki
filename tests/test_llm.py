import anthropic
import pytest

import pkb.llm as llm


def test_prefers_standard_when_api_key_set(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("ANTHROPIC_AWS_API_KEY", "aws-key-should-be-ignored")
    monkeypatch.setattr(anthropic, "Anthropic", lambda *a, **k: ("standard", k))
    client = llm.build_client()
    assert client[0] == "standard"


def test_falls_back_to_aws_when_only_aws_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_AWS_API_KEY", "aws-key-123")
    captured = {}

    def fake_aws(*a, **k):
        captured.update(k)
        return ("aws", k)

    monkeypatch.setattr(anthropic, "AnthropicAWS", fake_aws)
    client = llm.build_client()
    assert client[0] == "aws"
    assert captured["api_key"] == "aws-key-123"


def test_raises_without_credentials(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AWS_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        llm.build_client()
