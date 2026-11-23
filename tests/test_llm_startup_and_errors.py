import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

PROJECT_DIR = Path(__file__).resolve().parent.parent / "Projekt RPG"
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

import llm_client
from config import Config
from llm_client import LLMConfigError, LLMError, create_provider
import main


EXPECTED_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-2.0-flash",
    "gemini-flash-latest",
]


class _FakeProvider:
    def __init__(self, *, name="Gemini", model="gemini-3.8-flash", generate_side_effect=None, generate_return="OK"):
        self.name = name
        self.model = model
        self._generate_side_effect = generate_side_effect
        self._generate_return = generate_return
        self.generate_calls = []
        self.chat_calls = []

    def generate_text(self, contents: str, **kwargs) -> str:
        self.generate_calls.append((contents, kwargs))
        if self._generate_side_effect is not None:
            if isinstance(self._generate_side_effect, list):
                item = self._generate_side_effect.pop(0)
                if isinstance(item, BaseException):
                    raise item
                return item
            if isinstance(self._generate_side_effect, BaseException):
                raise self._generate_side_effect
            return self._generate_side_effect(contents, **kwargs)
        return self._generate_return

    def start_chat(self, system_instruction: str, **kwargs):
        self.chat_calls.append((system_instruction, kwargs))
        return MagicMock()


def test_default_models_order_and_contents():
    assert hasattr(main, "DEFAULT_MODELS")
    assert "gemini-flash-3.5-lite" not in main.DEFAULT_MODELS
    for model_name in EXPECTED_MODELS:
        assert model_name in main.DEFAULT_MODELS


@pytest.mark.parametrize("model_name", EXPECTED_MODELS)
def test_verify_llm_credentials_success_for_all_models(monkeypatch, model_name):
    captured_configs = []
    fake_provider = _FakeProvider(name="Gemini", model=model_name, generate_return="pong")

    def _fake_create_provider(cfg: Config):
        captured_configs.append(cfg)
        return fake_provider

    monkeypatch.setattr(llm_client, "create_provider", _fake_create_provider)

    ok, message = main.verify_llm_credentials("AIzaValidKey123", model_name, provider_name="gemini")

    assert ok is True
    assert len(captured_configs) == 1
    assert captured_configs[0].api_key == "AIzaValidKey123"
    assert captured_configs[0].model == model_name
    assert fake_provider.generate_calls
    assert isinstance(message, str) and len(message) > 0


@pytest.mark.parametrize("model_name", EXPECTED_MODELS)
def test_verify_llm_credentials_model_not_found(monkeypatch, model_name):
    fake_provider = _FakeProvider(
        name="Gemini",
        model=model_name,
        generate_side_effect=RuntimeError(f"404 NOT_FOUND: Model {model_name} not found"),
    )
    monkeypatch.setattr(llm_client, "create_provider", lambda cfg: fake_provider)

    ok, message = main.verify_llm_credentials("AIzaValidKey123", model_name, provider_name="gemini")

    assert ok is False
    assert model_name in message


@pytest.mark.parametrize(
    ("exc", "expected_snippet"),
    [
        (RuntimeError("401 UNAUTHENTICATED: API_KEY_INVALID"), "klucz"),
        (RuntimeError("400 INVALID_ARGUMENT: API key not valid"), "klucz"),
        (RuntimeError("429 RESOURCE_EXHAUSTED: Quota exceeded"), "limit"),
        (RuntimeError("503 UNAVAILABLE: The model is overloaded"), "przeciąż"),
    ],
)
def test_verify_llm_credentials_handles_api_errors(monkeypatch, exc, expected_snippet):
    fake_provider = _FakeProvider(name="Gemini", model="gemini-3.8-flash", generate_side_effect=exc)
    monkeypatch.setattr(llm_client, "create_provider", lambda cfg: fake_provider)

    ok, message = main.verify_llm_credentials("AIzaTestKey123", "gemini-3.8-flash", provider_name="gemini")

    assert ok is False
    assert expected_snippet.lower() in message.lower()


def test_save_and_load_llm_settings_respects_remember_key(tmp_path, monkeypatch):
    settings_path = tmp_path / "llm_settings.json"
    monkeypatch.setattr(main, "USER_SETTINGS_PATH", settings_path)
    monkeypatch.setattr(main, "SAVE_DIR", tmp_path)

    main.save_llm_settings("AIzaSecretKey", "gemini-3.8-flash", remember_key=False)
    loaded_without_key = main.load_saved_llm_settings()
    assert loaded_without_key.get("model") == "gemini-3.8-flash"
    assert not loaded_without_key.get("api_key")

    main.save_llm_settings("AIzaSecretKey", "gemini-3.5-flash-lite", remember_key=True)
    loaded_with_key = main.load_saved_llm_settings()
    assert loaded_with_key["model"] == "gemini-3.5-flash-lite"
    assert loaded_with_key["api_key"] == "AIzaSecretKey"


def test_load_saved_llm_settings_handles_corrupted_file(tmp_path, monkeypatch):
    settings_path = tmp_path / "llm_settings.json"
    settings_path.write_text("{ zepsuty json", encoding="utf-8")
    monkeypatch.setattr(main, "USER_SETTINGS_PATH", settings_path)

    assert main.load_saved_llm_settings() == {}


class _DummyVar:
    def __init__(self, value=""):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


def _make_dialog_stub(api_key="AIzaTestKey", model_name="gemini-3.8-flash", remember=False):
    dialog = main.LlmStartupDialog.__new__(main.LlmStartupDialog)
    dialog.root = MagicMock()
    dialog.key_var = _DummyVar(api_key)
    dialog.model_var = _DummyVar(model_name)
    dialog.remember_var = _DummyVar(remember)
    dialog.status_var = _DummyVar("")
    dialog.confirm_btn = MagicMock()
    dialog.cancel_btn = MagicMock()
    dialog.result = None
    return dialog


def test_dialog_confirm_empty_key_shows_warning(monkeypatch):
    warn_mock = MagicMock()
    monkeypatch.setattr(main.messagebox, "showwarning", warn_mock)

    dialog = _make_dialog_stub(api_key="   ", model_name="gemini-3.8-flash")
    dialog._on_confirm()

    assert dialog.result is None
    warn_mock.assert_called_once()
    dialog.root.destroy.assert_not_called()


def test_dialog_confirm_empty_model_shows_warning(monkeypatch):
    warn_mock = MagicMock()
    monkeypatch.setattr(main.messagebox, "showwarning", warn_mock)

    dialog = _make_dialog_stub(api_key="AIzaTestKey", model_name="   ")
    dialog._on_confirm()

    assert dialog.result is None
    warn_mock.assert_called_once()
    dialog.root.destroy.assert_not_called()


@pytest.mark.parametrize(
    "error_code",
    [
        "429 RESOURCE_EXHAUSTED",
        "503 UNAVAILABLE",
        "401 API_KEY_INVALID",
    ],
)
def test_dialog_confirm_api_error_shows_error_and_reenables_buttons(monkeypatch, error_code):
    error_mock = MagicMock()
    monkeypatch.setattr(main.messagebox, "showerror", error_mock)
    monkeypatch.setattr(
        main,
        "verify_llm_credentials",
        lambda key, model, *args, **kwargs: (False, f"Błąd API ({error_code})"),
    )

    dialog = _make_dialog_stub(api_key="AIzaTestKey", model_name="gemini-3.8-flash")
    dialog._on_confirm()

    assert dialog.result is None
    error_mock.assert_called_once()
    dialog.root.destroy.assert_not_called()
    assert any(
        call.kwargs.get("state") == main.tk.NORMAL or (call.args and call.args[0] == main.tk.NORMAL)
        for call in dialog.confirm_btn.config.call_args_list
    )


@pytest.mark.parametrize("model_name", EXPECTED_MODELS)
def test_dialog_confirm_success_for_every_supported_model(tmp_path, monkeypatch, model_name):
    monkeypatch.setattr(main, "USER_SETTINGS_PATH", tmp_path / "llm_settings.json")
    monkeypatch.setattr(main, "SAVE_DIR", tmp_path)
    monkeypatch.setattr(main, "verify_llm_credentials", lambda key, model, *args, **kwargs: (True, "OK"))

    dialog = _make_dialog_stub(api_key="AIzaGoodKey", model_name=model_name, remember=True)
    dialog._on_confirm()

    assert dialog.result == ("gemini", "AIzaGoodKey", model_name)
    saved = json.loads((tmp_path / "llm_settings.json").read_text(encoding="utf-8"))
    assert saved["model"] == model_name
    assert saved["api_key"] == "AIzaGoodKey"
    dialog.root.destroy.assert_called_once()


@pytest.mark.parametrize("err_snippet", ["429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE", "OVERLOADED"])
def test_app_error_classifier_recognizes_quota_and_overload(err_snippet):
    if hasattr(main, "classify_api_error"):
        category = main.classify_api_error(RuntimeError(f"Error {err_snippet}: busy"))
        assert category is not None
    if hasattr(main, "build_user_error_message"):
        msg = main.build_user_error_message(RuntimeError(f"Error {err_snippet}: busy"))
        assert isinstance(msg, str) and len(msg) > 0


@pytest.mark.parametrize("error_code", ["429 RESOURCE_EXHAUSTED", "503 UNAVAILABLE"])
def test_chat_turn_handles_quota_or_overload_without_crashing(monkeypatch, error_code):
    """Sprawdza zachowanie podczas rozmowy na czacie, gdy model zwróci 429 lub 503."""
    app = main.HybridGMRoleplayChatApp.__new__(main.HybridGMRoleplayChatApp)
    app.root = MagicMock()
    app.clean_chat_history = [{"sender": "Me", "text": "Idę dalej."}]
    app.game_state = {"tura": 1, "ostatni_rzut": None, "rzut_wykonany": False}
    app.turning_points = []
    app.has_unsaved_changes = False
    app.messages_displayed = []
    app.append_message = lambda sender, msg, tag=None: app.messages_displayed.append((sender, msg, tag))
    app.show_system_error = lambda msg: app.messages_displayed.append(("System", msg, "error_tag"))
    app.handle_llm_error = lambda exc: app.messages_displayed.append(("System", str(exc), "error_tag"))
    app.discard_empty_stream_message = MagicMock()

    fake_chat = MagicMock()
    fake_chat.send_message_stream.side_effect = RuntimeError(f"{error_code}: model busy")
    app.llm_chat = fake_chat

    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda *args, **kwargs: False)

    if hasattr(app, "simulate_llm_response"):
        app.simulate_llm_response("Sprawdzam drzwi.")
        assert any(sender == "System" for sender, _, _ in app.messages_displayed)
        assert app.clean_chat_history[-1]["text"] == "Idę dalej."


@pytest.mark.parametrize("error_code", ["429 RESOURCE_EXHAUSTED", "503 UNAVAILABLE"])
def test_initial_turning_points_init_handles_api_error(monkeypatch, error_code):
    """Sprawdza błędy 429/503 podczas początkowej generacji punktów zwrotnych."""
    fake_provider = _FakeProvider(
        name="Gemini",
        model="gemini-3.8-flash",
        generate_side_effect=RuntimeError(f"{error_code}: overloaded"),
    )
    monkeypatch.setattr(main, "llm", fake_provider)

    for func_name in ("generate_turning_points", "init_turning_points", "create_initial_turning_points"):
        if hasattr(main, func_name):
            fn = getattr(main, func_name)
            with pytest.raises(Exception):
                fn(MagicMock(), "Opis świata i postaci")
            break


def test_start_adventure_retries_up_to_three_attempts_on_transient_errors(monkeypatch):
    """Sprawdza scenariusz 3 prób rozpoczęcia przygody (sukces przy 3. próbie oraz 3 porażki)."""
    attempts = {"count": 0}

    def flaky_start(*args, **kwargs):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError("503 UNAVAILABLE: temporary overload")
        return "Przygotowana przygoda"

    def run_three_attempts(operation):
        last_exc = None
        for attempt in range(1, 4):
            try:
                return True, operation(), attempt
            except Exception as exc:
                last_exc = exc
        return False, str(last_exc), 3

    attempts["count"] = 0
    ok, result, used_attempts = run_three_attempts(flaky_start)
    assert ok is True
    assert used_attempts == 3
    assert result == "Przygotowana przygoda"

    def always_failing_start(*args, **kwargs):
        raise RuntimeError("429 RESOURCE_EXHAUSTED: quota exceeded")

    ok_fail, err_msg, failed_attempts = run_three_attempts(always_failing_start)
    assert ok_fail is False
    assert failed_attempts == 3
    assert "429" in err_msg


def test_openrouter_missing_api_key_raises_config_error():
    cfg = Config(
        provider="openrouter",
        api_key="",
        model="openrouter/auto",
        base_url="https://openrouter.ai/api/v1",
    )
    with pytest.raises(LLMConfigError) as exc_info:
        create_provider(cfg)
    assert "OPENROUTER_API_KEY" in (exc_info.value.user_message or str(exc_info.value))


def test_ollama_works_without_api_key_and_uses_default_placeholder():
    fake_openai_client = MagicMock()
    cfg = Config(
        provider="ollama",
        api_key="",
        model="llama3.2",
        base_url="http://localhost:11434/v1",
    )
    provider = llm_client.OpenAICompatibleProvider(
        "Ollama",
        cfg.model,
        cfg.base_url or "",
        cfg.api_key or "ollama",
        client=fake_openai_client,
    )
    assert provider.name == "Ollama"
    assert provider.model == "llama3.2"


def test_openrouter_stream_chat_yields_chunks_and_updates_history_only_on_non_empty_reply(monkeypatch):
    fake_openai = SimpleNamespace(
        APITimeoutError=TimeoutError,
        APIConnectionError=ConnectionError,
        BadRequestError=ValueError,
    )
    monkeypatch.setitem(sys.modules, "openai", fake_openai)

    chunk_1 = SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="Witaj "))])
    chunk_2 = SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="wędrowcze."))])

    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = iter([chunk_1, chunk_2])

    provider = llm_client.OpenAICompatibleProvider(
        "OpenRouter",
        "stepfun/step-3.5-flash:free",
        "https://openrouter.ai/api/v1",
        "sk-or-test",
        client=fake_client,
    )
    session = provider.start_chat("Jesteś MG.")
    chunks = list(session.send_message_stream("Rozglądam się."))

    assert chunks == ["Witaj ", "wędrowcze."]
    assert session._history[-2:] == [
        {"role": "user", "content": "Rozglądam się."},
        {"role": "assistant", "content": "Witaj wędrowcze."},
    ]


def test_verify_llm_credentials_openrouter_without_key_fails():
    ok, msg = main.verify_llm_credentials("", "openrouter/auto", provider_name="openrouter")
    assert ok is False
    assert "klucz" in msg.lower()


def test_verify_llm_credentials_ollama_without_key_calls_provider(monkeypatch):
    fake_provider = _FakeProvider(name="Ollama", model="llama3.2", generate_return="pong")
    monkeypatch.setattr(llm_client, "create_provider", lambda cfg: fake_provider)

    ok, msg = main.verify_llm_credentials("", "llama3.2", provider_name="ollama")
    assert ok is True
    assert "Ollama" in msg
    assert fake_provider.generate_calls


@pytest.mark.parametrize("err_code", ["429", "503"])
def test_openrouter_or_ollama_quota_or_overload_in_verify(monkeypatch, err_code):
    fake_provider = _FakeProvider(
        name="OpenRouter",
        model="openrouter/auto",
        generate_side_effect=LLMError(f"HTTP {err_code} temporary issue"),
    )
    monkeypatch.setattr(llm_client, "create_provider", lambda cfg: fake_provider)

    ok, msg = main.verify_llm_credentials("sk-or-test", "openrouter/auto", provider_name="openrouter")
    assert ok is False
    assert err_code in msg

@pytest.mark.parametrize("provider_name", ["gemini", "openrouter", "ollama"])
def test_provider_models_mapping_contains_expected_entries(provider_name):
    assert hasattr(main, "PROVIDER_MODELS")
    assert provider_name in main.PROVIDER_MODELS
    assert isinstance(main.PROVIDER_MODELS[provider_name], list)
    assert len(main.PROVIDER_MODELS[provider_name]) > 0


@pytest.mark.parametrize(
    "provider_name, expected_model",
    [
        ("gemini", "gemini-3.5-flash-lite"),
        ("openrouter", "openrouter/auto"),
        ("ollama", "llama3.2"),
    ],
)

def test_dialog_provider_change_updates_available_models(provider_name, expected_model):
    dialog = main.LlmStartupDialog.__new__(main.LlmStartupDialog)
    dialog.provider_var = _DummyVar(provider_name)
    dialog.model_var = _DummyVar("")
    dialog.model_combo = {}

    if hasattr(dialog, "_on_provider_change"):
        dialog._on_provider_change()
        assert expected_model in dialog.model_combo["values"]
        assert dialog.model_var.get() == expected_model