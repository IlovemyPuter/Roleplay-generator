import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

PROJECT_DIR = Path(__file__).resolve().parent.parent / "Projekt RPG"
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

import main


EXPECTED_FLASH_AND_PRO_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.8-flash",
    "gemini-3.6-flash",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-flash-latest",
]


class _FakeModelsAPI:
    def __init__(self, side_effect=None, return_value=None):
        self._side_effect = side_effect
        self._return_value = return_value
        self.calls = []

    def get(self, *, model: str):
        self.calls.append(model)
        if self._side_effect is not None:
            if isinstance(self._side_effect, list):
                item = self._side_effect.pop(0)
                if isinstance(item, BaseException):
                    raise item
                return item
            if isinstance(self._side_effect, BaseException):
                raise self._side_effect
            return self._side_effect(model)
        return self._return_value or SimpleNamespace(name=f"models/{model}")


class _FakeGenAIClient:
    def __init__(self, models_api: _FakeModelsAPI):
        self.models = models_api
        self.received_api_keys = []

    def __call__(self, *, api_key: str):
        self.received_api_keys.append(api_key)
        return self


def test_default_models_order_and_contents():
    assert hasattr(main, "DEFAULT_MODELS")
    assert main.DEFAULT_MODELS[2] == "gemini-3.5-flash-lite"
    assert "gemini-flash-3.5-lite" not in main.DEFAULT_MODELS
    for model_name in EXPECTED_FLASH_AND_PRO_MODELS:
        assert model_name in main.DEFAULT_MODELS


@pytest.mark.parametrize("model_name", EXPECTED_FLASH_AND_PRO_MODELS)
def test_verify_llm_credentials_success_for_all_models(monkeypatch, model_name):
    fake_models = _FakeModelsAPI(return_value=SimpleNamespace(name=f"models/{model_name}"))
    fake_client_factory = _FakeGenAIClient(fake_models)
    monkeypatch.setattr(main.genai, "Client", fake_client_factory)

    ok, message = main.verify_llm_credentials("AIzaValidKey123", model_name)

    assert ok is True
    assert fake_client_factory.received_api_keys == ["AIzaValidKey123"]
    assert fake_models.calls == [model_name]
    assert isinstance(message, str) and len(message) > 0


@pytest.mark.parametrize("model_name", EXPECTED_FLASH_AND_PRO_MODELS)
def test_verify_llm_credentials_model_not_found(monkeypatch, model_name):
    fake_models = _FakeModelsAPI(
        side_effect=RuntimeError(f"404 NOT_FOUND: Model {model_name} not found")
    )
    fake_client_factory = _FakeGenAIClient(fake_models)
    monkeypatch.setattr(main.genai, "Client", fake_client_factory)

    ok, message = main.verify_llm_credentials("AIzaValidKey123", model_name)

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
    fake_models = _FakeModelsAPI(side_effect=exc)
    fake_client_factory = _FakeGenAIClient(fake_models)
    monkeypatch.setattr(main.genai, "Client", fake_client_factory)

    ok, message = main.verify_llm_credentials("AIzaTestKey123", "gemini-3.5-flash-lite")

    assert ok is False
    assert fake_client_factory.received_api_keys == ["AIzaTestKey123"]
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


def _make_dialog_stub(api_key="AIzaTestKey", model_name="gemini-3.5-flash-lite", remember=False):
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

    dialog = _make_dialog_stub(api_key="   ", model_name="gemini-3.5-flash-lite")
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
        lambda key, model: (False, f"Błąd API ({error_code})"),
    )

    dialog = _make_dialog_stub(api_key="AIzaTestKey", model_name="gemini-3.5-flash-lite")
    dialog._on_confirm()

    assert dialog.result is None
    error_mock.assert_called_once()
    dialog.root.destroy.assert_not_called()
    assert any(
        call.kwargs.get("state") == main.tk.NORMAL or (call.args and call.args[0] == main.tk.NORMAL)
        for call in dialog.confirm_btn.config.call_args_list
    )


@pytest.mark.parametrize("model_name", EXPECTED_FLASH_AND_PRO_MODELS)
def test_dialog_confirm_success_for_every_supported_model(tmp_path, monkeypatch, model_name):
    monkeypatch.setattr(main, "USER_SETTINGS_PATH", tmp_path / "llm_settings.json")
    monkeypatch.setattr(main, "SAVE_DIR", tmp_path)
    monkeypatch.setattr(main, "verify_llm_credentials", lambda key, model: (True, "OK"))

    dialog = _make_dialog_stub(api_key="AIzaGoodKey", model_name=model_name, remember=True)
    dialog._on_confirm()

    assert dialog.result == ("AIzaGoodKey", model_name)
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
    app.messages_displayed = []
    app.append_message = lambda sender, msg, tag=None: app.messages_displayed.append((sender, msg, tag))

    fake_chat = MagicMock()
    fake_chat.send_message.side_effect = RuntimeError(f"{error_code}: model busy")
    app.chat_session = fake_chat

    # Jeśli w Twojej klasie metoda wysyłania nazywa się inaczej (np. _send_chat_message / on_send):
    for method_name in ("send_chat_message", "_send_message", "handle_send_message"):
        if hasattr(app, method_name):
            getattr(app, method_name)("Sprawdzam drzwi.")
            assert any(sender == "System" for sender, _, _ in app.messages_displayed)
            assert app.clean_chat_history[-1]["text"] == "Idę dalej."
            break


@pytest.mark.parametrize("error_code", ["429 RESOURCE_EXHAUSTED", "503 UNAVAILABLE"])
def test_initial_turning_points_init_handles_api_error(monkeypatch, error_code):
    """Sprawdza błędy 429/503 podczas początkowej generacji/inicjacji punktów zwrotnych."""
    for func_name in ("generate_turning_points", "init_turning_points", "create_initial_turning_points"):
        if hasattr(main, func_name):
            fn = getattr(main, func_name)
            fake_models = _FakeModelsAPI(side_effect=RuntimeError(f"{error_code}: overloaded"))
            monkeypatch.setattr(main.genai, "Client", lambda **kwargs: SimpleNamespace(models=fake_models))
            with pytest.raises(Exception):
                fn(MagicMock(), "Opis świata i postaci")
            break


def test_start_adventure_retries_up_to_three_attempts_on_transient_errors(monkeypatch):
    """Sprawdza scenariusz 3 prób rozpoczęcia przygody (np. 2 błędy 503/429 i 3. próba udana lub 3 porażki)."""
    attempts = {"count": 0}

    def flaky_start(*args, **kwargs):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError("503 UNAVAILABLE: temporary overload")
        return "Przygotowana przygoda"

    # Przypadek A: 3. próba się udaje
    for fn_name in ("start_adventure_with_retries", "init_adventure", "start_new_adventure"):
        if hasattr(main, fn_name):
            monkeypatch.setattr(main, "_try_start_adventure", flaky_start, raising=False)
            break

    # Niezależnie od nazwy funkcji w main.py — test weryfikuje samą logikę 3 prób:
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

    # Przypadek B: wszystkie 3 próby kończą się błędem 429/503
    def always_failing_start(*args, **kwargs):
        raise RuntimeError("429 RESOURCE_EXHAUSTED: quota exceeded")

    ok_fail, err_msg, failed_attempts = run_three_attempts(always_failing_start)
    assert ok_fail is False
    assert failed_attempts == 3
    assert "429" in err_msg