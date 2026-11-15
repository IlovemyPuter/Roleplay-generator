import json
import math
import random
import re

from pydantic import ValidationError
from error_handler import build_user_error_message

from config import CHAT_TEMPERATURE, load_config

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
from turn_processing import process_turn

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
        """Odświeża listę punktów zwrotnych oraz etykietę stanu gry w panelu."""
        if hasattr(self, 'state_label') and self.state_label:
            tura = self.game_state.get("tura", 0)
            rzut = self.game_state.get("ostatni_rzut")
            rzut_str = str(rzut) if rzut is not None else "brak"
            self.state_label.config(text=f"Stan gry: Tura {tura} | Ostatni rzut: {rzut_str}")

        if hasattr(self, 'points_container') and self.points_container:
            # Czyszczenie starych kart
            for widget in self.points_container.winfo_children():
                widget.destroy()

            # Generowanie nowej karty dla każdego punktu zwrotnego
            for tp in self.turning_points:
                status_color = "#198754" if tp.status == "oczekujacy" else "#6c757d"
                status_text = "Oczekujący" if tp.status == "oczekujacy" else "Wykonany"

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
        try:
            setting = self.character['role_and_background']
            plot_outline = generate_plot(setting=setting, characters=[self.character], model=model, client=client)
            self.turning_points = plot_outline.root
            self.update_turning_points_ui()
            print("✅ [API] Wygenerowano 5 punktów zwrotnych.")
        except Exception as e:
            print(f"⚠️ [API] Błąd generowania punktów zwrotnych: {e}")
            self.handle_gemini_error(e)
            self.show_system_error("Przygoda rusza bez punktów zwrotnych. Możesz grać dalej albo wrócić do menu i spróbować ponownie.")
            self.turning_points = []
            self.update_turning_points_ui()

        # Wczytanie instrukcji systemowej Mistrza Gry z pliku z folderu prompts/
        from config import GAME_MASTER_SYSTEM_INSTRUCTION_PATH
        try:
            template_text = GAME_MASTER_SYSTEM_INSTRUCTION_PATH.read_text(encoding="utf-8")
        except Exception as e:
            print(f"⚠️ [API] Nie udało się wczyta pliku promptu GM: {e}")
            template_text = "Jesteś Mistrzem Gry i towarzyszem {character_name}."

        char = self.character
        # Podstawienie danych postaci do szablonu promptu
        self.system_instruction = template_text.format(
            character_name=char['name'],
            role_and_background=char['role_and_background'],
            personality=char['personality'],
            conversation_style=char['conversation_style'],
            knowledge_and_limits=char['knowledge_and_limits'],
            example_dialogue=char['example_dialogue']
        )

        try:
            # Tworzymy instancję czatu w pakiecie google-genai z odpowiednią instrukcją systemową
            self.gemini_chat = client.chats.create(
                model=model,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    temperature=CHAT_TEMPERATURE,
                )
            )
            print("✅ [API] Sesja czatu została pomyślnie utworzona.")

            # Automatycznie generujemy początek przygody od razu po starcie czatu
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
        """Rzut k20: pozwala na wykonanie tylko jednego rzutu w danej turze."""
        if self.game_state.get("rzut_wykonany", False):
            self.append_message("System", "⚠️ W tej turze wykonano już rzut kością. Wyślij wiadomość do Mistrza Gry, aby przejść do następnej tury.", "error_tag")
            return

        # Wykonanie rzutu i zabezpieczenie przed ponownym kliknięciem w tej samej turze
        self.game_state["ostatni_rzut"] = random.randint(1, 20)
        self.game_state["rzut_wykonany"] = True  
        self.has_unsaved_changes = True
        
        # Informacja o wyniku w czacie oraz odświeżenie panelu
        self.append_message("System", f"🎲 Wykonano rzut kością k20. Wynik: **{self.game_state['ostatni_rzut']}**", "system_tag")
        self.update_turning_points_ui()

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

    def start_adventure(self):
        """Wysyła ukryty prompt startowy zawierający pełną listę punktów zwrotnych."""
        if not self.gemini_chat:
            self.append_message("System", "Brak aktywnego połączenia z modelem Gemini.", "error_tag")
            return

        # Przygotowanie czytelnej listy 5 punktów zwrotnych dla Mistrza Gry
        tp_descriptions = []
        for tp in self.turning_points:
            tp_descriptions.append(
                f"- Punkt {tp.id} [{tp.title}]: {tp.description} (Efekt: {tp.effect})"
            )
        turning_points_str = "\n".join(tp_descriptions) if tp_descriptions else "Brak zaplanowanych punktów zwrotnych."

        # Wczytanie szablonu promptu startowego z pliku Markdown
        from config import START_ADVENTURE_PROMPT_PATH
        try:
            template_text = START_ADVENTURE_PROMPT_PATH.read_text(encoding="utf-8")
        except Exception as e:
            print(f"⚠️ [API] Nie udało się wczytać pliku promptu startowego: {e}")
            template_text = (
                "Rozpocznij sesję RPG na podstawie tła: \"{role_and_background}\". "
                "Oto punkty zwrotne:\n{turning_points_list}\n"
                "Napisz wprowadzenie i dodaj [TOWARZYSZ]: dla {character_name}."
            )

        # Uzupełnienie szablonu danymi postaci oraz punktami zwrotnymi
        intro_prompt = template_text.format(
            character_name=self.character['name'],
            role_and_background=self.character['role_and_background'],
            turning_points_list=turning_points_str
        )
        
        self.has_unsaved_changes = True

        try:
            print("📤 [API] Wysyłanie promptu startowego z mapą fabuły (ze streamowaniem)...")
            response_stream = self.gemini_chat.send_message_stream(intro_prompt)
            self.stream_and_parse_response(response_stream)
            print("✅ [API] Zakończono pobieranie wprowadzenia.")
        except Exception as e:
            print(f"❌ [API] Błąd podczas generowania wprowadzenia: {e}")
            self.handle_gemini_error(e)

    def simulate_llm_response(self, prompt: str):
        """Wysyła zapytanie gracza i odbiera odpowiedź strumieniowo z podziałem."""
        if not self.gemini_chat:
            self.append_message("System", "Brak aktywnego połączenia z modelem Gemini.", "error_tag")
            return

        # --- ZWIĘKSZENIE TURY I RESET BLOKADY RZUTU ---
        self.game_state["tura"] = self.game_state.get("tura", 0) + 1
        self.game_state["rzut_wykonany"] = False  # <--- TUTAJ ODBLOKOWUJEMY RZUT W NOWEJ TURZE

        skutki = process_turn(self.game_state, self.turning_points)
        self.update_turning_points_ui()
        if skutki:
            prompt += "\n" + "\n".join(
                f"[Punkt zwrotny] {skutek}" for skutek in skutki
            )

        # Zapisujemy ruch gracza do czystej historii
        self.clean_chat_history.append({"sender": "Me", "text": prompt})
        self.has_unsaved_changes = True

        try:
            print(f"📤 [API] Wysyłanie wiadomości gracza do Gemini (ze streamowaniem): \"{prompt[:30]}...\"")
            response_stream = self.gemini_chat.send_message_stream(prompt)
            self.stream_and_parse_response(response_stream)
            print("✅ [API] Zakończono odbieranie odpowiedzi od Gemini.")
        except Exception as e:
            print(f"❌ [API] Błąd podczas komunikacji z API: {e}")
            self.handle_gemini_error(e)
            
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