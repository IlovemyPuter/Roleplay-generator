import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

import save_manager
from turning_point import Condition, TurningPoint

import main
from main import HybridGMRoleplayChatApp


@pytest.fixture
def sample_character():
    return {
        "name": "Lyra",
        "role_and_background": "Zwiadowczyni z Północy",
        "personality": "Ostrożna i lojalna",
        "conversation_style": "Zwięzły, konkretny",
        "knowledge_and_limits": "Zna szlaki górskie",
        "example_dialogue": "Uważaj na ślady przy przełęczy.",
    }


@pytest.fixture
def sample_player():
    return {
        "name": "Kael",
        "role_and_background": "Wędrowny alchemik",
    }


@pytest.fixture
def sample_turning_points():
    return [
        TurningPoint(
            id=1,
            title="Zasadzka na przełęczy",
            description="Odkryj ślady bandytów przed zmrokiem.",
            condition=Condition(type="tura", value=2),
            effect="Drużyna unika zaskoczenia.",
            status="wykonany",
        ),
        TurningPoint(
            id=2,
            title="Negocjacje ze strażnikiem",
            description="Przekonaj strażnika bramy do otwarcia przejścia.",
            condition=Condition(type="rzut", value=12),
            effect="Brama zostaje otwarta.",
            status="oczekujacy",
        ),
    ]


@pytest.fixture
def sample_game_state():
    return {
        "tura": 3,
        "ostatni_rzut": 14,
        "rzut_wykonany": True,
        "etap": "Etap 2",
        "npcs": [
            {"name": "Borin", "description": "Krasnoludzki kowal z kuźni pod górą"},
            {"name": "Mirella", "description": "Zielarka zbierająca korzenie w dolinie"},
        ],
    }


def test_ensure_save_dir_creates_missing_directory(tmp_path, monkeypatch):
    target_dir = tmp_path / "nowy_savegame"
    monkeypatch.setattr(save_manager, "SAVE_DIR", target_dir)

    assert not target_dir.exists()
    save_manager.ensure_save_dir()
    assert target_dir.exists()
    assert target_dir.is_dir()


def test_save_and_load_full_roundtrip(
    tmp_path,
    monkeypatch,
    sample_character,
    sample_player,
    sample_turning_points,
    sample_game_state,
):
    save_dir = tmp_path / "savegame"
    save_file = save_dir / "zapis_przygody.json"
    monkeypatch.setattr(save_manager, "SAVE_DIR", save_dir)
    monkeypatch.setattr("save_manager.filedialog.asksaveasfilename", lambda **kwargs: str(save_file))
    monkeypatch.setattr("save_manager.filedialog.askopenfilename", lambda **kwargs: str(save_file))

    history = [
        {"sender": "Mistrz Gry & Świat", "text": "Wiatr wyje między skałami przełęczy."},
        {"sender": "Lyra", "text": "Zwolnij, widzę świeże tropy przy głazie."},
        {"sender": "Me", "text": "Sprawdzam ślady i przygotowuję miksturę."},
    ]

    ok_save, saved_path = save_manager.save_game(
        character=sample_character,
        system_instruction="Jesteś Mistrzem Gry.",
        chat_history=history,
        turning_points=sample_turning_points,
        game_state=sample_game_state,
        parent_window=MagicMock(),
        player_character=sample_player,
    )

    assert ok_save is True
    assert Path(saved_path) == save_file
    assert save_file.exists()

    ok_load, loaded_data = save_manager.load_game(parent_window=MagicMock())

    assert ok_load is True
    assert loaded_data["character"] == sample_character
    assert loaded_data["player_character"] == sample_player
    assert loaded_data["system_instruction"] == "Jesteś Mistrzem Gry."
    assert loaded_data["chat_history"] == history
    assert loaded_data["game_state"] == sample_game_state
    assert len(loaded_data["turning_points"]) == 2

    restored_tps = [TurningPoint.model_validate(tp) for tp in loaded_data["turning_points"]]
    assert restored_tps[0].status == "wykonany"
    assert restored_tps[1].condition.type == "rzut"
    assert restored_tps[1].condition.value == 12


def test_save_defaults_when_optional_args_omitted(tmp_path, monkeypatch, sample_character):
    save_dir = tmp_path / "savegame"
    save_file = save_dir / "minimal.json"
    monkeypatch.setattr(save_manager, "SAVE_DIR", save_dir)
    monkeypatch.setattr("save_manager.filedialog.asksaveasfilename", lambda **kwargs: str(save_file))

    ok, result = save_manager.save_game(
        character=sample_character,
        system_instruction="Instrukcja",
        chat_history=[],
    )

    assert ok is True
    assert result == str(save_file)

    raw = json.loads(save_file.read_text(encoding="utf-8"))
    assert raw["player_character"] is None
    assert raw["turning_points"] == []
    assert raw["game_state"] == {"tura": 0, "ostatni_rzut": None}


def test_save_accepts_dict_turning_points(tmp_path, monkeypatch, sample_character):
    save_dir = tmp_path / "savegame"
    save_file = save_dir / "dict_tps.json"
    monkeypatch.setattr(save_manager, "SAVE_DIR", save_dir)
    monkeypatch.setattr("save_manager.filedialog.asksaveasfilename", lambda **kwargs: str(save_file))

    tp_dict = {
        "id": 1,
        "title": "Punkt ze słownika",
        "description": "Opis punktu",
        "condition": {"type": "tura", "value": 1},
        "effect": "Skutek",
        "status": "oczekujacy",
    }

    ok, _ = save_manager.save_game(
        character=sample_character,
        system_instruction="Instrukcja",
        chat_history=[],
        turning_points=[tp_dict],
    )

    assert ok is True
    raw = json.loads(save_file.read_text(encoding="utf-8"))
    assert raw["turning_points"] == [tp_dict]


def test_save_cancelled_by_user(tmp_path, monkeypatch, sample_character):
    save_dir = tmp_path / "savegame"
    monkeypatch.setattr(save_manager, "SAVE_DIR", save_dir)
    monkeypatch.setattr("save_manager.filedialog.asksaveasfilename", lambda **kwargs: "")

    ok, message = save_manager.save_game(
        character=sample_character,
        system_instruction="Instrukcja",
        chat_history=[],
    )

    assert ok is False
    assert message == "Anulowano zapis."
    assert list(save_dir.iterdir()) == []


def test_load_cancelled_by_user(tmp_path, monkeypatch):
    monkeypatch.setattr(save_manager, "SAVE_DIR", tmp_path / "savegame")
    monkeypatch.setattr("save_manager.filedialog.askopenfilename", lambda **kwargs: "")

    ok, message = save_manager.load_game()

    assert ok is False
    assert message == "Anulowano wybór pliku."


@pytest.mark.parametrize(
    "missing_key",
    ["character", "system_instruction", "chat_history"],
)
def test_load_missing_required_key(tmp_path, monkeypatch, sample_character, missing_key):
    payload = {
        "character": sample_character,
        "system_instruction": "Instrukcja",
        "chat_history": [],
    }
    del payload[missing_key]

    bad_file = tmp_path / f"brak_{missing_key}.json"
    bad_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    monkeypatch.setattr(save_manager, "SAVE_DIR", tmp_path)
    monkeypatch.setattr("save_manager.filedialog.askopenfilename", lambda **kwargs: str(bad_file))

    ok, message = save_manager.load_game()

    assert ok is False
    assert message == "Nieprawidłowy format pliku zapisu."


def test_load_corrupted_json_returns_read_error(tmp_path, monkeypatch):
    broken_file = tmp_path / "uszkodzony.json"
    broken_file.write_text("{ niepoprawny_json: [1, 2, ", encoding="utf-8")

    monkeypatch.setattr(save_manager, "SAVE_DIR", tmp_path)
    monkeypatch.setattr("save_manager.filedialog.askopenfilename", lambda **kwargs: str(broken_file))

    ok, message = save_manager.load_game()

    assert ok is False
    assert message.startswith("Błąd podczas odczytu pliku:")


def test_load_nonexistent_file_returns_read_error(tmp_path, monkeypatch):
    missing_file = tmp_path / "nie_istnieje.json"

    monkeypatch.setattr(save_manager, "SAVE_DIR", tmp_path)
    monkeypatch.setattr("save_manager.filedialog.askopenfilename", lambda **kwargs: str(missing_file))

    ok, message = save_manager.load_game()

    assert ok is False
    assert message.startswith("Błąd podczas odczytu pliku:")


def test_invalid_turning_point_fails_pydantic_validation(tmp_path, monkeypatch, sample_character):
    invalid_tp_file = tmp_path / "bledny_punkt.json"
    payload = {
        "character": sample_character,
        "system_instruction": "Instrukcja",
        "chat_history": [],
        "turning_points": [
            {
                "id": 99,
                "title": "Błędny punkt",
                "description": "Opis",
                "condition": {"type": "tura", "value": 1},
                "effect": "Efekt",
                "status": "oczekujacy",
            }
        ],
    }
    invalid_tp_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    monkeypatch.setattr(save_manager, "SAVE_DIR", tmp_path)
    monkeypatch.setattr("save_manager.filedialog.askopenfilename", lambda **kwargs: str(invalid_tp_file))

    ok, data = save_manager.load_game()
    assert ok is True

    with pytest.raises(ValidationError):
        [TurningPoint.model_validate(tp) for tp in data["turning_points"]]


def test_save_write_error_returns_false_and_exception_text(tmp_path, monkeypatch, sample_character):
    save_dir = tmp_path / "savegame"
    target_file = save_dir / "zapis.json"
    monkeypatch.setattr(save_manager, "SAVE_DIR", save_dir)
    monkeypatch.setattr("save_manager.filedialog.asksaveasfilename", lambda **kwargs: str(target_file))

    def fake_open(*args, **kwargs):
        if kwargs.get("mode") == "w" or (len(args) > 1 and args[1] == "w"):
            raise OSError("Dysk pełny lub brak uprawnień")
        return open(*args, **kwargs)

    monkeypatch.setattr("builtins.open", fake_open)

    ok, message = save_manager.save_game(
        character=sample_character,
        system_instruction="Instrukcja",
        chat_history=[],
    )

    assert ok is False
    assert "Dysk pełny lub brak uprawnień" in message


def _make_app_stub(sample_character, sample_player, sample_turning_points, sample_game_state):
    """Tworzy lekką instancję HybridGMRoleplayChatApp bez uruchamiania pełnego GUI i API."""
    app = HybridGMRoleplayChatApp.__new__(HybridGMRoleplayChatApp)
    app.root = MagicMock()
    app.character = dict(sample_character)
    app.player_character = dict(sample_player)
    app.system_instruction = "Instrukcja systemowa GM"
    app.clean_chat_history = [
        {"sender": "Mistrz Gry & Świat", "text": "Witaj w mrocznym lesie."},
        {"sender": "Me", "text": "Rozglądam się uważnie."},
    ]
    app.turning_points = list(sample_turning_points)
    app.game_state = dict(sample_game_state)
    app.npcs = list(sample_game_state.get("npcs", []))
    app.has_unsaved_changes = True

    app.chat_display = MagicMock()
    app.appended_messages = []
    app.append_message = lambda sender, message, tag_name: app.appended_messages.append(
        (sender, message, tag_name)
    )
    app.render_character_cards = MagicMock()
    app.update_turning_points_ui = MagicMock()
    app.restore_loaded_session = MagicMock()
    return app


def test_app_handle_save_persists_state_and_resets_unsaved_flag(
    tmp_path,
    monkeypatch,
    sample_character,
    sample_player,
    sample_turning_points,
    sample_game_state,
):
    save_dir = tmp_path / "savegame"
    target_file = save_dir / "zapis_z_gry.json"
    monkeypatch.setattr("save_manager.SAVE_DIR", save_dir)
    monkeypatch.setattr("save_manager.filedialog.asksaveasfilename", lambda **kwargs: str(target_file))

    app = _make_app_stub(sample_character, sample_player, sample_turning_points, sample_game_state)
    app.handle_save()

    assert app.has_unsaved_changes is False
    assert target_file.exists()
    assert any(sender == "System" and "zapisana" in msg for sender, msg, _ in app.appended_messages)

    saved = json.loads(target_file.read_text(encoding="utf-8"))
    assert saved["player_character"] == sample_player
    assert saved["game_state"]["tura"] == sample_game_state["tura"]
    assert len(saved["turning_points"]) == len(sample_turning_points)


def test_app_handle_save_cancelled_keeps_unsaved_flag(
    tmp_path,
    monkeypatch,
    sample_character,
    sample_player,
    sample_turning_points,
    sample_game_state,
):
    monkeypatch.setattr("save_manager.SAVE_DIR", tmp_path / "savegame")
    monkeypatch.setattr("save_manager.filedialog.asksaveasfilename", lambda **kwargs: "")

    app = _make_app_stub(sample_character, sample_player, sample_turning_points, sample_game_state)
    app.handle_save()

    assert app.has_unsaved_changes is True
    assert app.appended_messages == []


def test_app_handle_load_in_game_restores_all_state(
    tmp_path,
    monkeypatch,
    sample_character,
    sample_player,
    sample_turning_points,
    sample_game_state,
):
    save_dir = tmp_path / "savegame"
    save_file = save_dir / "wczytanie.json"
    monkeypatch.setattr("save_manager.SAVE_DIR", save_dir)
    monkeypatch.setattr("save_manager.filedialog.asksaveasfilename", lambda **kwargs: str(save_file))
    monkeypatch.setattr("save_manager.filedialog.askopenfilename", lambda **kwargs: str(save_file))

    writer_app = _make_app_stub(sample_character, sample_player, sample_turning_points, sample_game_state)
    writer_app.handle_save()

    reader_app = _make_app_stub(
        {"name": "Inna", "role_and_background": "", "personality": "", "conversation_style": "", "knowledge_and_limits": "", "example_dialogue": ""},
        {"name": "Inny Gracz", "role_and_background": ""},
        [],
        {"tura": 0, "ostatni_rzut": None, "npcs": []},
    )
    reader_app.handle_load_in_game()

    assert reader_app.character == sample_character
    assert reader_app.player_character == sample_player
    assert reader_app.game_state == sample_game_state
    assert reader_app.npcs == sample_game_state["npcs"]
    assert len(reader_app.turning_points) == 2
    assert all(isinstance(tp, TurningPoint) for tp in reader_app.turning_points)
    assert reader_app.has_unsaved_changes is False
    reader_app.render_character_cards.assert_called_once()
    reader_app.restore_loaded_session.assert_called_once()


def test_app_handle_load_in_game_corrupted_file_keeps_current_state(
    tmp_path,
    monkeypatch,
    sample_character,
    sample_player,
    sample_turning_points,
    sample_game_state,
):
    broken_file = tmp_path / "zepsuty.json"
    broken_file.write_text("nie-json", encoding="utf-8")

    monkeypatch.setattr("save_manager.SAVE_DIR", tmp_path)
    monkeypatch.setattr("save_manager.filedialog.askopenfilename", lambda **kwargs: str(broken_file))

    app = _make_app_stub(sample_character, sample_player, sample_turning_points, sample_game_state)
    original_tura = app.game_state["tura"]

    app.handle_load_in_game()

    assert app.game_state["tura"] == original_tura
    assert app.character == sample_character
    app.restore_loaded_session.assert_not_called()