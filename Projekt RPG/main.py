from config import CHAT_TEMPERATURE, load_config

from google import genai
from google.genai import types

# Importujemy interfejs graficzny
import tkinter as tk

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

class HybridGMRoleplayChatApp(RoleplayChatApp):
    """Rozszerzona klasa okna czatu, która integruje interfejs z Gemini API."""

    def __init__(self, root, character, save_data=None):
        # Inicjalizacja klasycznego okna z interfejsu
        super().__init__(root, character)

        self.has_unsaved_changes = False

        # --- BINDOWANIE KLAWISZY ---
        root.bind("<F5>", lambda event: self.handle_save())
        root.bind("<F8>", lambda event: self.handle_load_in_game())

        # Podpięcie akcji pod przycisk powrotu zdefiniowany w interfejsie
        if hasattr(self, 'back_btn'):
            self.back_btn.config(command=self.handle_back)

        if save_data:
            # TRYB WCZYTANIA: Odtwarzamy stan z pliku JSON
            self.character = save_data["character"]
            self.system_instruction = save_data["system_instruction"]
            self.clean_chat_history = save_data["chat_history"]

            # Odtwarzanie punktów zwrotnych i stanu gry ze zrzutu
            raw_tps = save_data.get("turning_points", [])
            self.turning_points = [TurningPoint.model_validate(tp) if isinstance(tp, dict) else tp for tp in raw_tps]
            self.game_state = save_data.get("game_state", {"tura": 0, "ostatni_rzut": None})
            
            self.root.after(100, self.restore_loaded_session)
        else:
            # TRYB NOWEJ GRY
            self.clean_chat_history = []
            self.system_instruction = ""
            self.game_state = {"tura": 0, "ostatni_rzut": None}
            self.has_unsaved_changes = False
            self.root.after(100, self.init_gemini_chat)

    def update_turning_points_ui(self):
        """Odświeża tabelę punktów zwrotnych oraz etykietę stanu gry w panelu."""
        if hasattr(self, 'state_label') and self.state_label:
            tura = self.game_state.get("tura", 0)
            rzut = self.game_state.get("ostatni_rzut")
            rzut_str = str(rzut) if rzut is not None else "brak"
            self.state_label.config(text=f"Stan gry: Tura {tura} | Ostatni rzut: {rzut_str}")

        if hasattr(self, 'points_tree') and self.points_tree:
            for row in self.points_tree.get_children():
                self.points_tree.delete(row)
            for tp in self.turning_points:
                status_text = "Oczekujący" if tp.status == "oczekujacy" else "Wykonany"
                tag = "oczekujacy" if tp.status == "oczekujacy" else "wykonany"
                self.points_tree.insert(
                    "",
                    tk.END,
                    values=(tp.id, tp.title, tp.description, status_text),
                    tags=(tag,)
                )

    def handle_load_in_game(self):
        """Obsługa wczytywania gry z poziomu aktywnego czatu (przycisk lub F8)."""
        success, data = load_game(parent_window=self.root)
        if success:
            # Podmieniamy stan bieżącej sesji na wczytany
            self.character = data["character"]
            self.system_instruction = data["system_instruction"]
            self.clean_chat_history = data["chat_history"]
            raw_tps = data.get("turning_points", [])
            self.turning_points = [
                TurningPoint.model_validate(tp) if isinstance(tp, dict) else tp
                for tp in raw_tps
            ]
            self.game_state = data.get("game_state", {"tura": 0, "ostatni_rzut": None})
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
            self.append_message("System", "BŁĄD: Klient Gemini nie został zainicjalizowany.", "system_tag")
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
                self.append_message("System", f"❌ Błąd podczas zapisu gry: {result}", "system_tag")

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
            self.append_message("System", "BŁĄD: Klient Gemini nie został zainicjalizowany. Sprawdź klucz API.", "system_tag")
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
            self.turning_points = []
            self.update_turning_points_ui()

        # Osobowość i zasady dla AI (System Instruction)
        char = self.character
        self.system_instruction = f"""
Jesteś jednocześnie Mistrzem Gry (Game Masterem) w sesji RPG oraz wcielasz się w postać towarzyszącą graczowi o imieniu: {char['name']}.

TWOJE ZADANIA JAKO MISTRZA GRY (GM):
1. Prowadzisz fabułę, opisujesz świat, otoczenie, pogodę, zagrożenia oraz reakcje otoczenia i innych napotkanych postaci niezależnych (NPC).
2. Sprawiasz, że świat żyje i reaguje na decyzje gracza w sposób konsekwentny.
3. Opisuj świat zwięźle, ale plastycznie (angażuj zmysły: wzrok, słuch, zapach).
4. Postacie niezależne (NPC) mają własne motywacje, cele i charakter – nie są tylko "tłem".
5. NIE PODEJMUJ decyzji za postać gracza.

TWOJA ROLA JAKO TOWARZYSZA ({char['name']}):
1. Musisz ściśle trzymać się profilu tej postaci:
   - Rola i tło: {char['role_and_background']}
   - Osobowość: {char['personality']}
   - Styl konwersacji: {char['conversation_style']}
   - Wiedza i ograniczenia: {char['knowledge_and_limits']}
   - Przykłady dialogowe: {char['example_dialogue']}
2. Twoja postać rozmawia z graczem, wyraża swoje zdanie, doradza lub komentuje sytuację z perspektywy pierwszej osoby, zachowując swój unikalny charakter.
3. **ZAKAZ PODSUWANIA DECYZJI:** Twoja postać NIGDY nie podaje propozycji gotowych wyborów, opcji ani alternatyw typu "idziemy tak czy siak?". Możesz wyrazić swoją opinię, wątpliwość lub niezadowolenie, ale ostateczny ruch, plan i decyzja należą w 100% do gracza. Zawsze kończ wypowiedź pytaniem zostawiającym całkowitą inicjatywę graczowi.
4. **ZAKOŃCZENIE WYPOWIEDZI:** Zawsze kończ swoją wypowiedź naturalnym zawieszeniem akcji, pytaniem otwartym lub presją sytuacji z perspektywy postaci ({char['name']}) lub świata. Unikaj mechanicznych sformułożeń typu "Co robisz?", "Wybierz ruch" czy sztucznych opcji. Zamiast tego niech postać np. czeka na Twój krok, spogląda wyczekująco lub komentuje rozwijające się zagrożenie, zostawiając pełną inicjatywę graczowi.

🚨 UNIWERSALNE ZASADY SPÓJNOŚCI I KONTROLI ŚWIATA (LORE):
1. **Ścisłe poszanowanie konwencji świata:** Prawa fizyczne, obecność/brak magii, technologia oraz realia epoki zdefiniowane w "Roli i tle" ({char['role_and_background']}) są nienaruszalne. 
2. **Blokada nierealnych akcji (Brak uległości wobec gracza):** Jeśli gracz spróbuje zrobić coś sprzecznego z logiką świata (np. użyć magii w świecie bez magii) lub wykraczającego poza "Wiedzę i ograniczenia" ({char['knowledge_and_limits']}), **nigdy nie pozwalaj na to**. Mistrz Gry musi opisać brak efektu, absurdalność pomysłu lub fizyczną niemożliwość, a {char['name']} powinna zareagować na to realistycznie ze swojej perspektywy (np. odmówić, upomnieć lub uznać gracza za szaleńca).
3. **KONTROLA ŚWIATA I FAKTÓW (ZAKAZ TWORZENIA RZECZYWISTOŚCI PRZEZ GRACZA):** Tylko i wyłącznie Mistrz Gry decyduje o tym, co znajduje się w otoczeniu, jakie postacie tam są i co się dzieje. Gracz NIE MA MOCY tworzenia elementów świata. Jeśli gracz spróbuje wejść w interakcję z czymś, czego nie było w opisie (np. "flirtuję z duchem" w pustym pokoju albo "wyciągam ukryty miecz laserowy"), **Mistrz Gry musi to bezwzględnie zablokować**. Zareaguj realizmem: gracz mówi do pustej ściany / macha rękami w powietrzu, a {char['name']} patrzy na niego jak na wariata lub pyta z drwiną, z kim do cholery rozmawia. Nigdy nie pozwól, aby wymysł gracza nagle stał się rzeczywistością, jeśli wcześniej nie został opisany przez GM-a.

STRUKTURA ODPOWIEDZI:
W każdej odpowiedzi podziel swoją wypowiedź na dwie wyraźne części:
1. Najpierw opisz sytuację jako bezstronny Mistrz Gry (co się dzieje w świecie).
2. Następnie w nowej linijce dodaj słowo kluczowe `[TOWARZYSZ]:`, po którym następuje wypowiedź lub reakcja postaci ({char['name']}) w jej unikalnym stylu. 
Przykład struktury:
Opis świata i otoczenia przez Mistrza Gry...
[TOWARZYSZ]: Wypowiedź towarzysza...

Zawsze kończ wpis sytuacją wymagającą reakcji gracza.
"""
        try:
            # Tworzymy instancję czatu w pakiecie google-genai z odpowiednią instrukcją systemową
            self.gemini_chat = client.chats.create(
                model=model,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    temperature=CHAT_TEMPERATURE, # Wyższa temperatura = bardziej kreatywne opisy
                )
            )
            print("✅ [API] Sesja czatu została pomyślnie utworzona.")

            # Automatycznie generujemy początek przygody od razu po starcie czatu
            self.start_adventure()

        except Exception as e:
            print(f"❌ [API] Błąd tworzenia sesji: {e}")
            self.append_message("System", f"Błąd tworzenia sesji Gemini: {e}", "system_tag")
            self.gemini_chat = None

    def handle_gemini_error(self, e):
        """Uniwersalna metoda do parsowania i wyświetlania błędów API (429, 503 i inne)."""
        error_str = str(e)

        # Obsługa błędów niepoprawnego klucza API (400 INVALID_ARGUMENT)
        if "400" in error_str or "API_KEY_INVALID" in error_str or "API key not valid" in error_str:
            error_msg = (
                "❌ **Niepoprawny klucz API (Błąd 400)**\n"
                "• Podany klucz API jest nieważny lub został błędnie wpisany.\n\n"
                "🛠️ **Jak to naprawić?**\n"
                "1. Wejdź na stronę **Google AI Studio** (aistudio.google.com).\n"
                "2. Wygeneruj nowy klucz API.\n"
                "3. Upewnij się, że poprawnie ustawiłeś zmienną środowiskową (`$env:GEMINI_API_KEY=\"TWÓJ_KLUCZ\"`) lub podaj go bezpośrednio w kodzie: `client = genai.Client(api_key=\"TWÓJ_KLUCZ\")`."
            )
        elif "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
            # Próbujemy wyciągnąć czas oczekiwania z komunikatu błędu
            retry_time_info = "nieznany czas"
            if "Please retry in" in error_str:
                try:
                    # Wyciąganie fragmentu tekstu po "Please retry in "
                    parts = error_str.split("Please retry in ")
                    if len(parts) > 1:
                        retry_time_info = parts[1].split(".")[0] # np. "16h56m40s" lub podobnie
                except Exception:
                    pass

            error_msg = (
                "⏳ **Wyczerpano darmowy dzienny limit zapytań (Błąd 429)**\n"
                f"• Pozostały czas do odnowienia limitu: **{retry_time_info}**\n\n"
                "🛠️ **Jak obejść ten problem?**\n"
                "1. **Płatny plan:** Przejdź w Google AI Studio na plan *Pay-as-you-go* (płacisz tylko za zużycie, co usuwa sztywne dzienne limity darmowego konta).\n"
                "2. **Inne konto:** Zaloguj się w Google AI Studio na inne konto Google, wygeneruj nowy klucz API i podmień go w aplikacji.\n"
                "3. **Inny model:** Zmień model w kodzie na taki, który ma osobną pulę darmowych zapytań (jeśli jest dostępny)."
            )
        elif "503" in error_str or "UNAVAILABLE" in error_str:
            error_msg = (
                "⚠️ Model Gemini jest obecnie mocno obciążony (błąd 503). "
                "To chwilowy problem po stronie Google. Spróbuj wysłać wiadomość ponownie za kilka sekund."
            )
        else:
            error_msg = f"Wystąpił błąd podczas komunikacji z API: {e}"
            
        self.append_message("System", error_msg, "system_tag")

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

        # Zakończenie strumienia (gdyby model nie podał znacznika)
        if not gm_finalized:
            gm_text = full_text.strip()
            self.update_streaming_message(gm_text)
            self.finish_streaming_message()
            if gm_text:
                self.clean_chat_history.append({"sender": "Mistrz Gry & Świat", "text": gm_text})
        else:
            parts = full_text.split("[TOWARZYSZ]:", 1)
            comp_text = parts[1].strip() if len(parts) > 1 else ""
            self.finish_streaming_message()
            companion_name = self.character['name']
            if comp_text:
                self.clean_chat_history.append({"sender": companion_name, "text": comp_text})

    def start_adventure(self):
        """Wysyła ukryty prompt startowy zakorzeniony w realiach postaci."""
        if not self.gemini_chat:
            self.append_message("System", "Brak aktywnego połączenia z modelem Gemini.", "system_tag")
            return

        intro_prompt = (
            "Rozpocznij sesję RPG. Jako Mistrz Gry stwórz krótkie, klimatyczne wprowadzenie do świata, "
            "które bezwzględnie opiera się na realiach, epoce i kontekście opisanym w tle postaci: "
            f"\"{self.character['role_and_background']}\". "
            "Następnie wpisz znacznik [TOWARZYSZ]: i spraw, aby moja towarzyszka/mój towarzysz "
            f"({self.character['name']}) odezwał(-a) się(-a) po raz pierwszy w swoim unikalnym stylu,"
            "komentując obecną sytuację, bez podawania gotowych propozycji dalszych kroków."
        )
        self.has_unsaved_changes = True

        try:
            print("📤 [API] Wysyłanie promptu startowego (ze streamowaniem)...")
            response_stream = self.gemini_chat.send_message_stream(intro_prompt)
            self.stream_and_parse_response(response_stream)
            print("✅ [API] Zakończono pobieranie wprowadzenia.")
        except Exception as e:
            print(f"❌ [API] Błąd podczas generowania wprowadzenia: {e}")
            self.handle_gemini_error(e)

    def simulate_llm_response(self, prompt: str):
        """Wysyła zapytanie gracza i odbiera odpowiedź strumieniowo z podziałem."""
        if not self.gemini_chat:
            self.append_message("System", "Brak aktywnego połączenia z modelem Gemini.", "system_tag")
            return

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

# --- Zmodyfikowana funkcja startowa uruchamiająca nową klasę z API ---
def start_chat_app_with_hybrid_gm(selected_character):
    chat_root = tk.Tk()
    HybridGMRoleplayChatApp(chat_root, selected_character)
    chat_root.mainloop()


if __name__ == "__main__":
    # Uruchomienie okna wyboru postaci z pliku interface.py, 
    # ale jako funkcję zwrotną podajemy naszą nową klasę z obsługą Gemini.
    select_root = tk.Tk()
    CharacterSelectWindow(select_root, on_character_selected=start_chat_app_with_hybrid_gm)
    select_root.mainloop()
