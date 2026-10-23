import os
import json
from tkinter import filedialog

# Nazwa folderu na zapisy
SAVE_DIR = "savegame"

def ensure_save_dir():
    """Tworzy folder savegame, jeśli jeszcze nie istnieje."""
    if not os.path.exists(SAVE_DIR):
        os.makedirs(SAVE_DIR)

def save_game(character, system_instruction, chat_history, parent_window=None):
    """Zapisuje stan gry do pliku JSON w folderze savegame."""
    ensure_save_dir()
    
    """Zapisuje postać, setting oraz historię czatu do pliku JSON."""
    file_path = filedialog.asksaveasfilename(
        parent=parent_window,
        initialdir=SAVE_DIR,  # Otwiera okno dialogowe bezpośrednio w folderze savegame
        defaultextension=".json",
        filetypes=[("Pliki JSON (*.json)", "*.json"), ("Wszystkie pliki", "*.*")],
        title="Zapisz stan gry"
    )
    
    if not file_path:
        return False, "Anulowano zapis."

    save_data = {
        "character": character,
        "system_instruction": system_instruction,
        "chat_history": chat_history
    }

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(save_data, f, ensure_ascii=False, indent=4)
        return True, file_path
    except Exception as e:
        return False, str(e)

def load_game(parent_window=None):
    ensure_save_dir()
    """Wczytuje stan gry z pliku JSON i zwraca słownik z danymi."""
    file_path = filedialog.askopenfilename(
        parent=parent_window,
        initialdir=SAVE_DIR,
        filetypes=[("Pliki JSON (*.json)", "*.json"), ("Wszystkie pliki", "*.*")],
        title="Wczytaj stan gry"
    )
    if not file_path:
        return False, "Anulowano wybór pliku."

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Sprawdzamy czy plik posiada wymagane klucze
        required_keys = ["character", "system_instruction", "chat_history"]
        if not all(key in data for key in required_keys):
            return False, "Nieprawidłowy format pliku zapisu."

        return True, data
    except Exception as e:
        return False, f"Błąd podczas odczytu pliku: {e}"
