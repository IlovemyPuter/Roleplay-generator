import json
import math
import random
import re

from pydantic import ValidationError
from error_handler import build_user_error_message

from config import SAVE_DIR, CHAT_TEMPERATURE, load_config

from google import genai
from google.genai import types

# Importujemy interfejs graficzny
import tkinter as tk
from tkinter import ttk

# Importujemy dane postaci i klasy okien z pliku interface.py
from interface import CharacterSelectWindow, RoleplayChatApp

# Import modelu TurningPoint:
from turning_point import TurningPoint
from generate_plot import generate_plot
from turn_processing import process_turn, update_game_stage

# Importujemy logikę zapisu gry
from save_manager import save_game, load_game


settings = load_config()
model = settings.model

client = None
if settings.api_key:
    try:
        client = genai.Client(api_key=settings.api_key)
    except Exception as e:
        print(f"Błąd inicjalizacji klienta Gemini: {e}")

# --- OBSŁUGA BŁĘDÓW API ---------------------------------------
def format_retry_time(error_str: str) -> str:
    """Wyciąga z komunikatu błędu 429 czas oczekiwania, np. '17s' lub '16h56m40s'."""
    match = (
        re.search(r"retry in\s+(\d[0-9hms.]*)", error_str, re.IGNORECASE)
        or re.search(r"retryDelay\W+(\d[0-9hms.]*)", error_str)
    )
    if not match:
        return "nieznany czas"
    value = match.group(1).rstrip(".")
    only_seconds = re.fullmatch(r"(\d+(?:\.\d+)?)s", value)
    if only_seconds:
        return f"{math.ceil(float(only_seconds.group(1)))}s"
    return value or "nieznany czas"


def classify_api_error(error: Exception) -> str:
    """Zwraca rodzaj błędu: limit, json, klucz, przeciazenie, timeout albo inny."""
    text = str(error)
    upper = text.upper()
    if re.search(r"\b429\b", text) or "RESOURCE_EXHAUSTED" in upper:
        return "limit"
    if isinstance(error, (json.JSONDecodeError, ValidationError)) or "JSON" in upper or "ZARYS" in upper:
        return "json"
    if re.search(r"\b400\b", text) or "API_KEY_INVALID" in upper or "API KEY NOT VALID" in upper:
        return "klucz"
    if re.search(r"\b503\b", text) or "UNAVAILABLE" in upper:
        return "przeciazenie"
    if re.search(r"\b504\b", text) or "DEADLINE_EXCEEDED" in upper or "TIMEOUT" in upper or "TIMED OUT" in upper:
        return "timeout"
    return "inny"

class HybridGMRoleplayChatApp(RoleplayChatApp):
    """Rozszerzona klasa okna czatu, która integruje interfejs z Gemini API."""

    def __init__(self, root, character, save_data=None, player_character=None):
        # Inicjalizacja klasycznego okna z interfejsu
        super().__init__(root, character, player_character=player_character)
        # Styl komunikatów o błędach: czerwony
        self.chat_display.tag_config("error_tag", foreground="#dc3545", font=("Arial", 10, "bold"))

        self.has_unsaved_changes = False
        self.game_state = {"tura": 0, "ostatni_rzut": None, "rzut_wykonany": False}

        # --- BINDOWANIE KLAWISZY ---
        root.bind("<F5>", lambda event: self.handle_save())
        root.bind("<F8>", lambda event: self.handle_load_in_game())

        # Podpięcie akcji pod przycisk powrotu zdefiniowany w interfejsie
        if hasattr(self, 'back_btn'):
            self.back_btn.config(command=self.handle_back)

        # Podpięcie rzutu kością pod przycisk zdefiniowany w interfejsie
        if hasattr(self, 'roll_button'):
            self.roll_button.config(command=self.handle_roll)

        if save_data:
            # TRYB WCZYTANIA: Odtwarzamy stan z pliku JSON
            self.character = save_data["character"]
            if "player_character" in save_data and save_data["player_character"]:
                self.player_character = save_data["player_character"]
            
            self.system_instruction = save_data["system_instruction"]
            self.clean_chat_history = save_data["chat_history"]

            # Odtwarzanie punktów zwrotnych i stanu gry ze zrzutu
            raw_tps = save_data.get("turning_points", [])
            self.turning_points = [TurningPoint.model_validate(tp) if isinstance(tp, dict) else tp for tp in raw_tps]
            self.game_state = save_data.get("game_state", {"tura": 0, "ostatni_rzut": None})
            
            # Przywracamy listę NPC z zapisanego stanu gry i odświeżamy kafelki
            self.npcs = self.game_state.get("npcs", [])
            self.render_character_cards()
            
            self.root.after(100, self.restore_loaded_session)
        else:
            # TRYB NOWEJ GRY
            self.clean_chat_history = []
            self.system_instruction = ""
            self.game_state = {"tura": 0, "ostatni_rzut": None}
            self.has_unsaved_changes = False
            self.root.after(100, self.init_gemini_chat)

    def update_turning_points_ui(self):
        # Dynamiczne włączanie/wyłączanie przycisku rzutu w zależności od punktów zwrotnych
        if hasattr(self, 'roll_button') and self.roll_button:
            if self.is_roll_allowed() and not self.game_state.get("rzut_wykonany", False):
                self.roll_button.config(state=tk.NORMAL)
            else:
                self.roll_button.config(state=tk.DISABLED)
        
        """Odświeża listę punktów zwrotnych oraz etykietę stanu gry w panelu."""
        if hasattr(self, 'state_label') and self.state_label:
            tura = self.game_state.get("tura", 0)
            rzut = self.game_state.get("ostatni_rzut")
            rzut_str = str(rzut) if rzut is not None else "brak"
            etap = self.game_state.get("etap", "Etap 1")
            self.state_label.config(text=f"{etap} | Tura {tura} | Ostatni rzut: {rzut_str}")

        if hasattr(self, 'points_container') and self.points_container:
            # Czyszczenie starych kart w kontenerze
            for widget in self.points_container.winfo_children():
                widget.destroy()

            # Filtrujemy listę – zostawiamy tylko te, które mają status "wykonany"
            wykonane_punkty = [tp for tp in self.turning_points if tp.status == "wykonany"]

            # Jeśli żaden punkt nie został jeszcze zaliczony, wyświetlamy informację
            if not wykonane_punkty:
                info_label = ttk.Label(
                    self.points_container,
                    text="Żaden punkt zwrotny nie został osiągnięty.",
                    font=("Arial", 10, "italic"),
                    justify="center"
                )
                info_label.pack(padx=15, pady=30, anchor="center")
            else:
                # Generowanie nowej karty tylko dla wykonanych punktów zwrotnych
                for tp in wykonane_punkty:
                    status_color = "#6c757d"
                    status_text = "Wykonany"

                    # Ramka pojedynczego punktu zwrotnego (kafelek)
                    card = ttk.LabelFrame(self.points_container, padding=8)
                    card.pack(fill=tk.X, padx=5, pady=5)

                    # 1. Tytuł (mniejsza czcionka)
                    title_label = tk.Label(
                        card,
                        text=f"#{tp.id}: {tp.title}",
                        font=("Arial", 9, "bold"),
                        fg="#333333",
                        anchor="w"
                    )
                    title_label.pack(anchor="w", fill=tk.X)

                    # 2. Opis (WIĘKSZA czcionka niż tytuł + automatyczne zawijanie wierszy)
                    desc_label = tk.Label(
                        card,
                        text=tp.description,
                        font=("Arial", 11),  # Większa czcionka zgodnie z wymaganiem
                        fg="#111111",
                        justify=tk.LEFT,
                        wraplength=280  # Szerokość zawijania tekstu dopasowana do panelu
                    )
                    desc_label.pack(anchor="w", fill=tk.X, pady=(4, 4))

                    # 3. Status punktu
                    status_label = tk.Label(
                        card,
                        text=f"Stan: {status_text}",
                        font=("Arial", 8, "italic"),
                        fg=status_color,
                        anchor="e"
                    )
                    status_label.pack(anchor="e")

    def handle_load_in_game(self):
        """Obsługa wczytywania gry z poziomu aktywnego czatu (przycisk lub F8)."""
        success, data = load_game(parent_window=self.root)
        if success:
            # Podmieniamy stan bieżącej sesji na wczytany
            self.character = data["character"]
            
            # Wczytujemy postać gracza, jeśli została zapisana w pliku
            if "player_character" in data and data["player_character"]:
                self.player_character = data["player_character"]
                
            self.system_instruction = data["system_instruction"]
            self.clean_chat_history = data["chat_history"]
            
            # Odtwarzanie punktów zwrotnych
            raw_tps = data.get("turning_points", [])
            self.turning_points = [
                TurningPoint.model_validate(tp) if isinstance(tp, dict) else tp
                for tp in raw_tps
            ]
            
            # Wczytanie stanu gry oraz listy napotkanych NPC
            self.game_state = data.get("game_state", {"tura": 0, "ostatni_rzut": None})
            self.npcs = self.game_state.get("npcs", [])
            
            # Odświeżenie kafelków w lewym panelu (Gracz, Towarzysz, NPC)
            self.render_character_cards()
            
            self.has_unsaved_changes = False

            # Czyścimy widok czatu i odtwarzamy sesję od nowa
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.delete("1.0", tk.END)
            self.chat_display.config(state=tk.DISABLED)

            self.restore_loaded_session()
        else:
            if data != "Anulowano wybór pliku.":
                print(f"❌ Błąd wczytywania: {data}")

    def restore_loaded_session(self):
        """Odtwarza widok czatu oraz sesję Gemini z wczytanej historii."""
        if not client:
            self.append_message("System", "BŁĄD: Klient Gemini nie został zainicjalizowany.", "error_tag")
            return
        # 1. Wyświetlamy wczytaną historię w oknie czatu GUI
        for msg in self.clean_chat_history:
            sender = msg["sender"]
            text = msg["text"]
            tag = "bot_tag" if sender == "Mistrz Gry & Świat" else "user_tag"
            self.append_message(sender, text, tag)
            
        # 2. Przygotowujemy historię dla struktury SDK Gemini
        # Konwertujemy historię do formatu typów wiadomości Gemini (user / model)
        gemini_history = []
        for msg in self.clean_chat_history:
            role = "user" if msg["sender"] == "Me" else "model"
            gemini_history.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=msg["text"])]
                )
            )

        # 3. Tworzymy nowy czat z odtworzoną historią i instrukcją systemową
        try:
            self.gemini_chat = client.chats.create(
                model=model,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    temperature=CHAT_TEMPERATURE,
                ),
                history=gemini_history  # <-- Gemini kontynuuje zapisaną historię
            )
            self.update_turning_points_ui()
            self.append_message("System", "📂 Stan gry został pomyślnie wczytany! Możesz kontynuować przygodę.", "system_tag")
        except Exception as e:
            self.handle_gemini_error(e)
            self.gemini_chat = None

    # Metoda wywołująca zapis w klasie HybridGMRoleplayChatApp:
    def handle_save(self):
        success, result = save_game(
            character=self.character,
            player_character=self.player_character,  # <--- Przekazujemy gracza do zapisu
            system_instruction=self.system_instruction,
            chat_history=self.clean_chat_history,
            turning_points=self.turning_points,
            game_state=self.game_state,
            parent_window=self.root
        )
        
        if success:
            self.has_unsaved_changes = False
            self.append_message("System", f"💾 Gra została pomyślnie zapisana do pliku: {result}", "system_tag")
        else:
            if result != "Anulowano zapis.":
                self.append_message("System", f"❌ Błąd podczas zapisu gry: {result}", "error_tag")

    def handle_back(self):
        """Obsługa przycisku powrotu (tak jak handle_save czy handle_load_in_game)."""
        # Sprawdzamy czy od ostatniego zapisu lub startu nie było żadnej akcji
        if not self.has_unsaved_changes:
            self.return_to_menu()
        else:
            # Jeśli były akcje, pytamy użytkownika co zrobić (pop-up)
            from tkinter import messagebox
            answer = messagebox.askyesnocancel(
                "Niezapisana rozmowa",
                "Masz niezapisane postępy w rozmowie. Czy chcesz zapisać grę przed powrotem?",
                parent=self.root
            )

            if answer is True:  # Wybrano "Tak" -> zapisujemy i wracamy
                success, result = save_game(
                    character=self.character,
                    system_instruction=self.system_instruction,
                    chat_history=self.clean_chat_history,
                    turning_points=self.turning_points,
                    game_state=self.game_state,
                    parent_window=self.root
                )
                if success:
                    self.return_to_menu()
                else:
                    if result != "Anulowano zapis.":
                        self.append_message("System", f"❌ Błąd zapisu: {result}", "system_tag")
            elif answer is False:  # Wybrano "Nie" -> wracamy bez zapisu
                self.return_to_menu()
            else:
                # Wybrano "Anuluj" -> nic nie robimy, zostajemy w grze
                pass

    def return_to_menu(self):
        """Niszczy obecne okno i wraca do wyboru postaci."""
        self.root.destroy()
        select_root = tk.Tk()
        CharacterSelectWindow(select_root, on_character_selected=start_chat_app_with_hybrid_gm)
        select_root.mainloop()

    def init_gemini_chat(self):
        if not client:
            self.append_message("System", "BŁĄD: Klient Gemini nie został zainicjalizowany. Sprawdź klucz API.", "error_tag")
            self.gemini_chat = None
            return

        print("⏳ [API] Inicjalizowanie nowej sesji czatu z Gemini...")

        # Generowanie 5 punktów zwrotnych na początku nowej przygody
        generated_successfully = True
        try:
            setting = self.character['role_and_background']
            plot_outline = generate_plot(setting=setting, characters=[self.character], model=model, client=client)
            self.turning_points = plot_outline.root
            self.update_turning_points_ui()
            print("✅ [API] Wygenerowano 5 punktów zwrotnych.")
        except Exception as e:
            print(f"⚠️ [API] Błąd generowania punktów zwrotnych: {e}")
            generated_successfully = False
            self.turning_points = []

        # Jeśli wystąpił błąd lub lista punktów jest pusta, pytamy użytkownika co zrobić
        if not generated_successfully or not self.turning_points:
            from tkinter import messagebox
            answer = messagebox.askyesno(
                "Błąd generowania fabuły",
                "Nie udało się wygenerować punktów zwrotnych dla nowej przygody (błąd API lub brak odpowiedzi).\n\n"
                "Czy chcesz kontynuować grę bez punktów zwrotnych?\n"
                "(Wybierz 'Nie', aby wrócić do menu i spróbować ponownie)",
                parent=self.root
            )

            if not answer:  # Wybrano "Nie" -> wracamy do menu
                self.return_to_menu()
                return
            else:  # Wybrano "Tak" -> gramy dalej bez punktów zwrotnych
                self.update_turning_points_ui()

        # Dalsza część inicjalizacji czatu...
        from config import GAME_MASTER_SYSTEM_INSTRUCTION_PATH
        try:
            template_text = GAME_MASTER_SYSTEM_INSTRUCTION_PATH.read_text(encoding="utf-8")
        except Exception as e:
            print(f"⚠️ [API] Nie udało się wczytać pliku promptu GM: {e}")
            template_text = "Jesteś Mistrzem Gry i towarzyszem {character_name}."

        char = self.character
        self.system_instruction = template_text.format(
            character_name=char['name'],
            role_and_background=char['role_and_background'],
            personality=char['personality'],
            conversation_style=char['conversation_style'],
            knowledge_and_limits=char['knowledge_and_limits'],
            example_dialogue=char['example_dialogue']
        )

        try:
            self.gemini_chat = client.chats.create(
                model=model,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    temperature=CHAT_TEMPERATURE,
                )
            )
            print("✅ [API] Sesja czatu została pomyślnie utworzona.")
            self.start_adventure()

        except Exception as e:
            print(f"❌ [API] Błąd tworzenia sesji: {e}")
            self.append_message("System", f"Błąd tworzenia sesji Gemini: {e}", "error_tag")
            self.gemini_chat = None

    def append_message(self, sender: str, message: str, tag_name: str):
        if tag_name != "error_tag":
            super().append_message(sender, message, tag_name)
            return
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, f"{sender}: {message}\n\n", "error_tag")
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)

    def _start_on_new_line(self):
        """Gdy przerwano strumień w pół zdania, kończy linię, żeby błąd nie dokleił się do tekstu."""
        self.chat_display.config(state=tk.NORMAL)
        last_char = self.chat_display.get("end-2c", "end-1c")
        if last_char not in ("", "\n"):
            self.chat_display.insert(tk.END, "\n\n")
        self.chat_display.config(state=tk.DISABLED)

    def show_system_error(self, message: str):
        """Pokazuje graczowi komunikat systemowy w oknie czatu."""
        self._start_on_new_line()
        self.append_message("System", message, "error_tag")

    def handle_gemini_error(self, e: Exception):
        """Zamienia błąd API na czytelny komunikat w oknie gry."""
        error_msg = build_user_error_message(e)
        self.show_system_error(error_msg)

    def discard_empty_stream_message(self):
        """Usuwa pusty nagłówek 'Mistrz Gry & Świat: ', gdy model nic nie zwrócił."""
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.delete(f"{self._stream_start_index} linestart", tk.END)
        self.chat_display.config(state=tk.DISABLED)

    def handle_roll(self):
        """Rzut k20: dozwolony tylko wtedy, gdy punkt zwrotny tego wymaga i tylko raz na turę."""
        # 1. Sprawdzamy, czy fabularnie potrzebny jest rzut
        if not self.is_roll_allowed():
            self.append_message(
                "System", 
                "⚠️ Obecna sytuacja nie wymaga rzutu kością. Rzucić kością można tylko wtedy, gdy wymaga tego bieżący punkt zwrotny.", 
                "error_tag"
            )
            return

        # 2. Sprawdzamy blokadę jednorazowego rzutu w turze
        if self.game_state.get("rzut_wykonany", False):
            self.append_message(
                "System", 
                "⚠️ W tej turze wykonano już rzut kością. Wyślij wiadomość do Mistrza Gry, aby przejść do następnej tury.", 
                "error_tag"
            )
            return

        # Wykonanie rzutu
        self.game_state["ostatni_rzut"] = random.randint(1, 20)
        self.game_state["rzut_wykonany"] = True  
        self.has_unsaved_changes = True
        
        # Informacja o wyniku w czacie oraz odświeżenie panelu
        self.append_message("System", f"🎲 Wykonano rzut kością k20 na polecenie fabuły. Wynik: **{self.game_state['ostatni_rzut']}**", "system_tag")
        self.update_turning_points_ui()
        
    def is_roll_allowed(self) -> bool:
        """Sprawdza, czy aktualny etap fabuły (oczekujący punkt zwrotny) wymaga rzutu kością."""
        for tp in self.turning_points:
            if tp.status == "oczekujacy":
                cond = tp.condition
                # Obsługa, gdy condition to słownik
                if isinstance(cond, dict):
                    if cond.get("type") == "rzut":
                        return True
                # Obsługa, gdy condition to obiekt Pydantic
                elif hasattr(cond, "type"):
                    if cond.type == "rzut":
                        return True
                # Jeśli pierwszy napotkany oczekujący punkt ma inny typ (np. 'tura'),
                # to natychmiast przerywamy pętlę i blokujemy rzut.
                break
        return False

    def stream_and_parse_response(self, response_stream):
        """Na bieżąco analizuje strumień i rozdziela tekst na GM i Towarzysza."""
        full_text = ""
        gm_finalized = False

        # Zaczynamy streamować jako Mistrz Gry
        self.start_streaming_message("Mistrz Gry & Świat", "bot_tag")

        for chunk in response_stream:
            if chunk.text:
                full_text += chunk.text

                if not gm_finalized:
                    # Sprawdzamy czy znacznik [TOWARZYSZ]: pojawił się już w tekście
                    if "[TOWARZYSZ]:" in full_text:
                        parts = full_text.split("[TOWARZYSZ]:", 1)
                        gm_text = parts[0].strip()
                        comp_text = parts[1].strip() if len(parts) > 1 else ""

                        # 1. Zamykamy dymkę Mistrza Gry
                        self.update_streaming_message(gm_text)
                        self.finish_streaming_message()
                        if gm_text:
                            self.clean_chat_history.append({"sender": "Mistrz Gry & Świat", "text": gm_text})

                        # 2. Otwieramy nową dymkę dla towarzysza z jego imieniem i kolorem
                        companion_name = self.character['name']
                        self.start_streaming_message(companion_name, "companion_tag")
                        self.update_streaming_message(comp_text)

                        gm_finalized = True
                    else:
                        # Wciąż streamujemy opis Mistrza Gry
                        self.update_streaming_message(full_text)
                else:
                    # Mistrz Gry zamknięty – streamujemy dalej resztę wypowiedzi towarzysza
                    parts = full_text.split("[TOWARZYSZ]:", 1)
                    comp_text = parts[1].strip() if len(parts) > 1 else ""
                    self.update_streaming_message(comp_text)

                self.root.update()  # Odświeżanie interfejsu w locie
        # Model nic nie zwrócił (pusta odpowiedź, np. zablokowana przez filtry) 
        if not full_text.strip():
            self.discard_empty_stream_message()
            self.show_system_error(
                "⚠️ Model nie zwrócił żadnej odpowiedzi (mogła zostać zablokowana lub przerwana). "
                "Spróbuj wysłać wiadomość ponownie albo sformułować ją inaczej."
            )
            return
        # Zakończenie strumienia (gdyby model nie podał znacznika)
        if not gm_finalized:
            gm_text = self._extract_and_register_npcs(full_text)
            self.update_streaming_message(gm_text)
            self.finish_streaming_message()
            if gm_text:
                self.clean_chat_history.append({"sender": "Mistrz Gry & Świat", "text": gm_text})
        else:
            parts = full_text.split("[TOWARZYSZ]:", 1)
            comp_raw = parts[1].strip() if len(parts) > 1 else ""
            comp_text = self._extract_and_register_npcs(comp_raw)
            self.update_streaming_message(comp_text)
            self.finish_streaming_message()
            companion_name = self.character['name']
            if comp_text:
                self.clean_chat_history.append({"sender": companion_name, "text": comp_text})

    def start_adventure(self, attempt: int = 1):
        """Wysyła ukryty prompt startowy z mechanizmem automatycznego ponawiania do 3 razy i czyszczeniem pamięci w razie błędu."""
        if not self.gemini_chat:
            self.append_message("System", "Brak aktywnego połączenia z modelem Gemini.", "error_tag")
            return

        # Szukamy TYLKO PIERWSZEGO punktu o statusie "oczekujacy"
        active_tp = None
        for tp in self.turning_points:
            if tp.status == "oczekujacy":
                active_tp = tp
                break

        if active_tp:
            tp_desc = f"Bieżący cel reżyserski (Punkt #{active_tp.id} - {active_tp.title}): {active_tp.description} (Oczekiwany efekt: {active_tp.effect})"
        else:
            tp_desc = "Brak aktywnych punktów zwrotnych."

        # Wczytanie szablonu promptu startowego z pliku Markdown
        from config import START_ADVENTURE_PROMPT_PATH
        try:
            template_text = START_ADVENTURE_PROMPT_PATH.read_text(encoding="utf-8")
        except Exception as e:
            print(f"⚠️ [API] Nie udało się wczytać pliku promptu startowego: {e}")
            template_text = (
                "Rozpocznij sesję RPG na podstawie tła: \"{role_and_background}\".\n"
                "Oto twój JEDYNY obecny cel reżyserski (nie znasz kolejnych):\n{turning_points_list}\n"
                "Napisz wprowadzenie i dodaj [TOWARZYSZ]: dla {character_name}."
            )

        # Uzupełnienie szablonu danymi postaci oraz TYLKO AKTUALNYM punktem
        intro_prompt = template_text.format(
            character_name=self.character['name'],
            role_and_background=self.character['role_and_background'],
            turning_points_list=tp_desc
        )
        
        self.has_unsaved_changes = True

        try:
            print(f"📤 [API] Wysyłanie promptu startowego (próba {attempt}/3)...")
            response_stream = self.gemini_chat.send_message_stream(intro_prompt)
            
            # Bezpieczny odbiorca strumienia wprowadzenia
            success = self.safe_stream_and_parse_intro(response_stream)
            
            if not success:
                raise Exception("Model zwrócił pustą lub pręwaną odpowiedź wprowadzenia.")

            print("✅ [API] Zakończono pobieranie wprowadzenia.")

        except Exception as e:
            print(f"❌ [API] Błąd podczas generowania wprowadzenia (próba {attempt}): {e}")

            # --- BEZPAMIĘCIOWY RESET W RAZIE BŁĘDU ---
            self.clean_chat_history = []
            
            try:
                self.discard_empty_stream_message()
            except Exception:
                pass

            try:
                self.gemini_chat = client.chats.create(
                    model=model,
                    config=types.GenerateContentConfig(
                        system_instruction=self.system_instruction,
                        temperature=CHAT_TEMPERATURE,
                    )
                )
                print("🔄 [API] Zresetowano sesję czatu (wyczyszczono pamięć kontekstu).")
            except Exception as chat_err:
                print(f"❌ [API] Błąd tworzenia nowej sesji po resecie: {chat_err}")

            # Obsługa limitu 3 prób
            if attempt < 3:
                print(f"⏳ [API] Automatyczne ponawianie próby startu ({attempt + 1}/3)...")
                self.start_adventure(attempt=attempt + 1)
            else:
                from tkinter import messagebox
                retry = messagebox.askyesno(
                    "Błąd inicjalizacji przygody",
                    f"Nie udało się wygenerować wprowadzenia po 3 próbach.\nOstatni błąd: {e}\n\nCzy chcesz spróbować ponownie?",
                    parent=self.root
                )
                if retry:
                    self.start_adventure(attempt=1)
                else:
                    self.show_system_error("⚠️ Inicjalizacja przygody została przerwana przez użytkownika.")

    def safe_stream_and_parse_intro(self, response_stream) -> bool:
        """Bezpiecznie przetwarza strumień wprowadzenia i zwraca True w przypadku sukcesu."""
        full_text = ""
        gm_finalized = False

        self.start_streaming_message("Mistrz Gry & Świat", "bot_tag")

        for chunk in response_stream:
            if chunk.text:
                full_text += chunk.text

                if not gm_finalized:
                    if "[TOWARZYSZ]:" in full_text:
                        parts = full_text.split("[TOWARZYSZ]:", 1)
                        gm_text = parts[0].strip()
                        comp_text = parts[1].strip() if len(parts) > 1 else ""

                        self.update_streaming_message(gm_text)
                        self.finish_streaming_message()
                        if gm_text:
                            cleaned_gm = self._extract_and_register_npcs(gm_text)
                            cleaned_gm = self._extract_and_complete_turning_points(cleaned_gm)
                            self.clean_chat_history.append({"sender": "Mistrz Gry & Świat", "text": cleaned_gm})

                        companion_name = self.character['name']
                        self.start_streaming_message(companion_name, "companion_tag")
                        self.update_streaming_message(comp_text)
                        gm_finalized = True
                    else:
                        self.update_streaming_message(full_text)
                else:
                    parts = full_text.split("[TOWARZYSZ]:", 1)
                    comp_text = parts[1].strip() if len(parts) > 1 else ""
                    self.update_streaming_message(comp_text)

                self.root.update()

        if not full_text.strip():
            self.discard_empty_stream_message()
            return False

        if not gm_finalized:
            cleaned_gm = self._extract_and_register_npcs(full_text)
            cleaned_gm = self._extract_and_complete_turning_points(cleaned_gm)
            self.update_streaming_message(cleaned_gm)
            self.finish_streaming_message()
            if cleaned_gm:
                self.clean_chat_history.append({"sender": "Mistrz Gry & Świat", "text": cleaned_gm})
        else:
            parts = full_text.split("[TOWARZYSZ]:", 1)
            comp_raw = parts[1].strip() if len(parts) > 1 else ""
            cleaned_comp = self._extract_and_register_npcs(comp_raw)
            cleaned_comp = self._extract_and_complete_turning_points(cleaned_comp)
            self.update_streaming_message(cleaned_comp)
            self.finish_streaming_message()
            companion_name = self.character['name']
            if cleaned_comp:
                self.clean_chat_history.append({"sender": companion_name, "text": cleaned_comp})

        return True

    def simulate_llm_response(self, prompt: str):
        """Wysyła zapytanie gracza wraz z aktualnym celem reżyserskim do Gemini."""
        if not self.gemini_chat:
            self.append_message("System", "Brak aktywnego połączenia z modelem Gemini.", "error_tag")
            return

        # 1. Znajdujemy WYŁĄCZNIE PIERWSZY punkt o statusie "oczekujacy"
        active_tp = None
        for tp in self.turning_points:
            if tp.status == "oczekujacy":
                active_tp = tp
                break

        directive_text = ""
        current_rzut = self.game_state.get("ostatni_rzut")

        if active_tp:
            cond = active_tp.condition
            cond_type = cond.get("type") if isinstance(cond, dict) else getattr(cond, "type", None)
            cond_val = cond.get("value") if isinstance(cond, dict) else getattr(cond, "value", None)

            if cond_type == "rzut" and current_rzut is not None:
                if current_rzut < cond_val:
                    # RZUT NIE POWIODŁ SIĘ - WYMAGAMY POWAŻNYCH KONSEKWENCJI
                    directive_text = (
                        f"\n[⚠️ KRYTYCZNA INSTRUKCJA DLA GM - NIEUDANY RZUT]: Gracz wykonał rzut kością i uzyskał wynik {current_rzut}, co jest WYNIKIEM NIEWYSTARCZAJĄCYM do zaliczenia punktu #{active_tp.id} - \"{active_tp.title}\" (wymagano min. {cond_val}). "
                        f"Rzut zakończył się niepowodzeniem! MUSISZ BEZWZGLĘDNIE natychmiast opisać w świecie gry poważne, negatywne konsekwencje tej porażki "
                        f"(np. fizyczne obrażenia postaci, utrata cennego ekwipunku, wpadnięcie w zasadzkę, zniszczenie osłony lub drastyczne pogorszenie sytuacji taktycznej). "
                        f"Sytuacja musi stać się o wiele trudniejsza dla gracza."
                    )
                else:
                    directive_text = (
                        f"\n[INSTRUKCJA REŻYSERSKA DLA GM: Punkt #{active_tp.id} - \"{active_tp.title}\" został pomyślnie zweryfikowany rzutem ({current_rzut} >= {cond_val}). "
                        f"Możesz bezpiecznie domknąć ten etap.]"
                    )
            elif cond_type == "tura":
                directive_text = (
                    f"\n[INSTRUKCJA REŻYSERSKA DLA GM: Twój aktualny cel to Punkt #{active_tp.id} - \"{active_tp.title}\": {active_tp.description}. "
                    f"Efekt do osiągnięcia: {active_tp.effect}.]"
                )
        else:
            directive_text = "\n[INSTRUKCJA REŻYSERSKA DLA GM: Wszystkie główne punkty zwrotne zostały zrealizowane. Prowadź otwartą fabułę.]"

        full_prompt_for_ai = prompt + directive_text

        # 2. Tymczasowo dodajemy wiadomość gracza do historii
        self.clean_chat_history.append({"sender": "Me", "text": prompt})
        self.has_unsaved_changes = True

        try:
            print(f"📤 [API] Wysyłanie wiadomości gracza do Gemini (z aktywnym celem reżyserskim)...")
            
            response_stream = self.gemini_chat.send_message_stream(full_prompt_for_ai)
            success = self.safe_stream_and_parse(response_stream, prompt)
            
            if not success:
                # Jeśli safe_stream_and_parse zwróciło False, cofamy wpis gracza z historii
                if self.clean_chat_history and self.clean_chat_history[-1]["sender"] == "Me":
                    self.clean_chat_history.pop()
                
                # Pyta użytkownika o ponowne wysłanie
                self.ask_to_resend(prompt)
                return

            print("✅ [API] Zakończono pomyślnie turę i odbieranie odpowiedzi.")

        except Exception as e:
            print(f"❌ [API] Błąd podczas komunikacji z API: {e}")
            
            # 1. Usuwamy wpis gracza z historii, aby się nie zapisał
            if self.clean_chat_history and self.clean_chat_history[-1]["sender"] == "Me":
                self.clean_chat_history.pop()
            
            # 2. Czyszczymy ewentualne śmieci z niedokończonego strumienia w oknie czatu
            try:
                self.discard_empty_stream_message()
            except Exception:
                pass

            self.handle_gemini_error(e)
            
            # 3. Pytamy użytkownika, czy chce wysłać wiadomość ponownie
            self.ask_to_resend(prompt)

    def ask_to_resend(self, prompt: str):
        """Wyświetla okno dialogowe z zapytaniem o ponowne wysłanie wiadomości po błędzie."""
        from tkinter import messagebox
        retry = messagebox.askyesno(
            "Błąd komunikacji z AI",
            "Wystąpił błąd podczas komunikacji z modelem (np. przeciążenie serwera lub limit zapytań).\n\n"
            "Twoja wiadomość oraz przerwana odpowiedź nie zostały zapisane w historii.\n\n"
            "Czy chcesz wysłać wiadomość jeszcze raz?",
            parent=self.root
        )
        if retry:
            # Ponawiamy próbę wysłania tej samej wiadomości
            self.simulate_llm_response(prompt)
            
    def safe_stream_and_parse(self, response_stream, prompt: str) -> bool:
        """Odbiera strumień, parsuje odpowiedź GM-a i Towarzysza, a dopiero po sukcesie zalicza turę i zapisuje stan."""
        full_text = ""
        gm_finalized = False

        self.start_streaming_message("Mistrz Gry & Świat", "bot_tag")

        for chunk in response_stream:
            if chunk.text:
                full_text += chunk.text

                if not gm_finalized:
                    if "[TOWARZYSZ]:" in full_text:
                        parts = full_text.split("[TOWARZYSZ]:", 1)
                        gm_text = parts[0].strip()
                        comp_text = parts[1].strip() if len(parts) > 1 else ""

                        self.update_streaming_message(gm_text)
                        self.finish_streaming_message()
                        if gm_text:
                            # Przetwarzamy tekst GM-a (wyciągamy NPC i zaliczone punkty zwrotne)
                            cleaned_gm = self._extract_and_register_npcs(gm_text)
                            cleaned_gm = self._extract_and_complete_turning_points(cleaned_gm)
                            self.clean_chat_history.append({"sender": "Mistrz Gry & Świat", "text": cleaned_gm})

                        companion_name = self.character['name']
                        self.start_streaming_message(companion_name, "companion_tag")
                        self.update_streaming_message(comp_text)
                        gm_finalized = True
                    else:
                        self.update_streaming_message(full_text)
                else:
                    parts = full_text.split("[TOWARZYSZ]:", 1)
                    comp_text = parts[1].strip() if len(parts) > 1 else ""
                    self.update_streaming_message(comp_text)

                self.root.update()

        # Jeśli model nic nie zwrócił (pusta odpowiedź / zablokowanie)
        if not full_text.strip():
            self.discard_empty_stream_message()
            self.show_system_error(
                "⚠️ Model nie zwrócił żadnej odpowiedzi (mogła zostać zablokowana lub przerwana). "
                "Spróbuj wysłać wiadomość ponownie albo sformułować ją inaczej."
            )
            return False  # Zwracamy False -> tura NIE wzrośnie!

        # Finalizacja tekstu (jeśli nie było znacznika [TOWARZYSZ])
        if not gm_finalized:
            cleaned_gm = self._extract_and_register_npcs(full_text)
            cleaned_gm = self._extract_and_complete_turning_points(cleaned_gm)
            self.update_streaming_message(cleaned_gm)
            self.finish_streaming_message()
            if cleaned_gm:
                self.clean_chat_history.append({"sender": "Mistrz Gry & Świat", "text": cleaned_gm})
        else:
            parts = full_text.split("[TOWARZYSZ]:", 1)
            comp_raw = parts[1].strip() if len(parts) > 1 else ""
            cleaned_comp = self._extract_and_register_npcs(comp_raw)
            cleaned_comp = self._extract_and_complete_turning_points(cleaned_comp)
            self.update_streaming_message(cleaned_comp)
            self.finish_streaming_message()
            companion_name = self.character['name']
            if cleaned_comp:
                self.clean_chat_history.append({"sender": companion_name, "text": cleaned_comp})

        # --- SUKCES! ZWIĘKSZAMY TURĘ I ROBIMY AUTOZAPIS ---
        self.game_state["tura"] = self.game_state.get("tura", 0) + 1
        self.game_state["rzut_wykonany"] = False

        skutki = process_turn(self.game_state, self.turning_points)
        if skutki:
            self.game_state["tura"] = 0  
            if self.clean_chat_history and self.clean_chat_history[-1]["sender"] == "Me":
                self.clean_chat_history[-1]["text"] += "\n" + "\n".join(
                    f"[Punkt zwrotny] {skutek}" for skutek in skutki
                )

        self.update_turning_points_ui()

        # Bezpośredni autozapis w tle do pliku
        try:
            game_data = {
                "character": self.character,
                "player_character": self.player_character,
                "system_instruction": self.system_instruction,
                "chat_history": self.clean_chat_history,
                "turning_points": [tp.model_dump() if hasattr(tp, "model_dump") else tp for tp in self.turning_points],
                "game_state": self.game_state
            }
            
            target_file = getattr(self, 'current_save_path', SAVE_DIR / "autosave.json")
            with open(target_file, "w", encoding="utf-8") as f:
                json.dump(game_data, f, ensure_ascii=False, indent=4)
                
            self.has_unsaved_changes = False
            print(f"💾 [AUTO-SAVE] Pomyślnie zaktualizowano plik w tle: {target_file}")
        except Exception as e:
            print(f"⚠️ [AUTO-SAVE] Błąd zapisu w tle: {e}")

        return True
            
    def _extract_and_register_npcs(self, text: str) -> str:
        """Wyciąga znaczniki [NPC: Imię | Opis], rejestruje postacie i czyści tekst z tagów."""
        pattern = r"\[NPC:\s*(.*?)\s*\|\s*(.*?)\]"
        matches = re.findall(pattern, text)

        if matches:
            existing_names = {n["name"].lower() for n in self.npcs}
            added_any = False

            for name, desc in matches:
                clean_name = name.strip()
                clean_desc = desc.strip()
                if clean_name and clean_name.lower() not in existing_names:
                    self.npcs.append({"name": clean_name, "description": clean_desc})
                    existing_names.add(clean_name.lower())
                    added_any = True

            if added_any:
                self.game_state["npcs"] = self.npcs
                self.render_character_cards()

        # Usuwamy znaczniki techniczne z tekstu, który trafi do historii czatu
        cleaned_text = re.sub(pattern, "", text).strip()
        return cleaned_text

    def _extract_and_complete_turning_points(self, text: str) -> str:
        """Zaawansowana weryfikacja: tura to minimum czasowe, ale warunkiem koniecznym jest decyzja (tag) GM-a wynikająca z działań gracza."""
        pattern = r"\[PUNKT_ZALICZONY:\s*(\d+)\]"
        matches = re.findall(pattern, text)
        completed_ids = {int(m) for m in matches}

        current_tura = self.game_state.get("tura", 0)
        current_rzut = self.game_state.get("ostatni_rzut")

        # Pobieramy TYLKO PIERWSZY aktualnie oczekujący punkt (sekwencyjność)
        active_tp = None
        for tp in self.turning_points:
            if tp.status == "oczekujacy":
                active_tp = tp
                break

        if active_tp:
            cond = active_tp.condition
            cond_type = cond.get("type") if isinstance(cond, dict) else getattr(cond, "type", None)
            cond_val = cond.get("value") if isinstance(cond, dict) else getattr(cond, "value", None)

            is_ready = False

            if cond_type == "tura":
                # ZASADA DLA TUR (DUAL-GATE): 
                # 1. Tura musi osiągnąć minimalny próg (np. minęły przynajmniej 3 tury).
                # 2. ORAZ Mistrz Gry musi wydać jawny sygnał (tag), że akcja gracza doprowadziła do realizacji celu.
                if current_tura >= cond_val:
                    if active_tp.id in completed_ids:
                        is_ready = True
                        print(f"✨ [TURN-GO] Punkt #{active_tp.id} ('{active_tp.title}') zaliczony (Tura {current_tura}/{cond_val} + Decyzja GM).")
                    else:
                        print(f"⏳ [TURN-WAITING] Tura osiągnęła wymagany próg ({current_tura}/{cond_val}), ale Mistrz Gry nie zaliczył jeszcze punktu w fabule (brak tagu). Czekamy na działania gracza.")
                else:
                    if active_tp.id in completed_ids:
                        print(f"⚠️ [TURN-BLOCK] GM próbował przedwcześnie zaliczyć punkt #{active_tp.id} tagiem, ale tura jest za niska ({current_tura}/{cond_val}). Odrzucono.")

            elif cond_type == "rzut":
                # ZASADA DLA RZUTÓW: Wymagany jest fizyczny rzut gracza. Sukces zalicza etap, porażka uruchamia konsekwencje.
                if current_rzut is not None:
                    if current_rzut >= cond_val:
                        is_ready = True
                        print(f"🎲 [DICE-GO] Sukces! Punkt #{active_tp.id} ('{active_tp.title}') zaliczony przez rzut ({current_rzut} >= {cond_val}).")
                    else:
                        # RZUT ZA NISKI -> PORAŻKA I KONSEKWENCJE!
                        print(f"❌ [DICE-FAIL] Porażka rzutu ({current_rzut} < {cond_val}) dla punktu #{active_tp.id}. Konsumujemy rzut – GM opisuje negatywne konsekwencje.")
                        self.game_state["ostatni_rzut"] = None
                        self.game_state["rzut_wykonany"] = False
                        self.has_unsaved_changes = True
                else:
                    if active_tp.id in completed_ids:
                        print(f"⚠️ [DICE-BLOCK] GM chciał zaliczyć punkt #{active_tp.id} (wymaga rzutu {cond_val}), ale brak rzutu. Odrzucono.")

            # Wykonanie przejścia (zamknięcie etapu), jeśli spełniono kryteria sukcesu
            if is_ready:
                active_tp.status = "wykonany"
                self.has_unsaved_changes = True
                
                # Resetujemy licznik tur po każdym zamkniętym etapie do 0
                self.game_state["tura"] = 0
                
                # Czyszczymy rzut dla kolejnego etapu
                if cond_type == "rzut":
                    self.game_state["ostatni_rzut"] = None
                    self.game_state["rzut_wykonany"] = False

                print(f"🚀 [STAGE TRANSITION] Etap zamknięty. Punkt #{active_tp.id} wykonany. Tura zresetowana do 0.")

        # Odświeżenie interfejsu
        update_game_stage(self.game_state, self.turning_points)
        self.update_turning_points_ui()

        cleaned_text = re.sub(pattern, "", text).strip()
        return cleaned_text

# --- Zmodyfikowana funkcja startowa obsługująca dane gracza i towarzysza ---
def start_chat_app_with_hybrid_gm(selected_character, player_character=None):
    chat_root = tk.Tk()
    HybridGMRoleplayChatApp(chat_root, selected_character, player_character=player_character)
    chat_root.mainloop()


if __name__ == "__main__":
    # Uruchomienie okna wyboru postaci z pliku interface.py, 
    # ale jako funkcję zwrotną podajemy naszą nową klasę z obsługą Gemini.
    select_root = tk.Tk()
    CharacterSelectWindow(select_root, on_character_selected=start_chat_app_with_hybrid_gm)
    select_root.mainloop()