import pytest

from scripts.configure_groq import select_model


def test_standard_account_without_enterprise_llama():
    assert select_model({"data": [{"id": "openai/gpt-oss-20b"}]}) == "openai/gpt-oss-20b"


def test_disabled_and_non_text_models_are_not_selected():
    with pytest.raises(ValueError):
        select_model({"data": [
            {"id": "openai/gpt-oss-20b", "active": False},
            {"id": "whisper-large-v3"},
        ]})


def test_available_production_fallback():
    assert select_model({"data": [{"id": "openai/gpt-oss-120b"}]}) == "openai/gpt-oss-120b"
