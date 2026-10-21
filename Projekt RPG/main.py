
''' === pip install -U google-genai === ''' # Instalacja wymaganego pakietu do połączenia się z Gemini API 
from google import genai
from google.genai import types

# Importujemy interfejs graficzny
import tkinter as tk

# Importujemy dane postaci i klasy okien z pliku interface.py
from interface import CharacterSelectWindow, RoleplayChatApp

# Inicjalizacja klienta
# Upewnij się, że klucz API jest w zmiennej środowiskowej GEMINI_API_KEY lub podaj: api_key="TWÓJ_KLUCZ"
try:
    client = genai.Client(api_key="--TODO--")
except Exception as e:
    print(f"Błąd inicjalizacji klienta Gemini: {e}")
    client = None

class HybridGMRoleplayChatApp(RoleplayChatApp):
    """Rozszerzona klasa okna czatu, która integruje interfejs z Gemini API."""

    def __init__(self, root, character):
        # Inicjalizacja klasycznego okna z interfejsu
        super().__init__(root, character)
        
        # Inicjalizacja sesji czatu z Gemini dla wybranej postaci
        self.init_gemini_chat()

    def init_gemini_chat(self):
        if not client:
            self.append_message("System", "BŁĄD: Klient Gemini nie został zainicjalizowany. Sprawdź klucz API.", "system_tag")
            self.gemini_chat = None
            return

        # Osobowość i zasady dla AI (System Instruction)
        char = self.character
        system_instruction = """
Jesteś jednocześnie Mistrzem Gry (Game Masterem) w sesji RPG oraz wcielasz się w postać towarzyszącą graczowi o imieniu: {char['name']}.

TWOJE ZADANIA JAKO MISTRZA GRY (GM):
1. Prowadzisz fabułę, opisujesz świat, otoczenie, pogodę, zagrożenia oraz reakcje otoczenia i innych napotkanych postaci niezależnych (NPC).
2. Sprawiasz, że świat żyje i reaguje na decyzje gracza w sposób konsekwentny.

TWOJA ROLA JAKO TOWARZYSZA ({char['name']}):
1. Musisz ściśle trzymać się profilu tej postaci:
   - Rola i tło: {char['role_and_background']}
   - Osobowość: {char['personality']}
   - Styl konwersacji: {char['conversation_style']}
   - Wiedza i ograniczenia: {char['knowledge_and_limits']}
   - Przykłady dialogowe: {char['example_dialogue']}
2. Twoja postać rozmawia z graczem, wyraża swoje zdanie, doradza lub komentuje sytuację z perspektywy pierwszej osoby, zachowując swój unikalny charakter.

STRUKTURA ODPOWIEDZI:
W każdej odpowiedzi najpierw opisz sytuację jako bezstronny Mistrz Gry (co się dzieje w świecie), a następnie wpleć naturalną reakcję, dialog lub działanie {char['name']} jako towarzysza podróży gracza. Zawsze kończ wpis sytuacją wymagającą reakcji gracza.
"""
        try:
            # Tworzymy instancję czatu w pakiecie google-genai z odpowiednią instrukcją systemową
            self.gemini_chat = client.chats.create(
                model="gemini-3.7-flash",
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.8, # Wyższa temperatura = bardziej kreatywne opisy
                )
            )

            # Automatycznie generujemy początek przygody od razu po starcie czatu
            self.start_adventure()

        except Exception as e:
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


    def start_adventure(self):
        """Wysyła ukryty prompt startowy, aby Mistrz Gry rozpoczął sesję i przywitał gracza ustami towarzysza."""
        intro_prompt = (
            "Rozpocznij sesję RPG. Jako Mistrz Gry stwórz krótkie, klimatyczne wprowadzenie do świata "
            "odpowiadającego profilowi mojej postaci. Następnie spraw, aby moja towarzyszka/mój towarzysz "
            f"({self.character['name']}) odezwał się(-a) po raz pierwszy w swoim unikalnym stylu i zapytał(-a) o plan działania."
        )
        try:
            response = self.gemini_chat.send_message(intro_prompt)
            self.append_message("Mistrz Gry & Świat", response.text, "bot_tag")
        except Exception as e:
            self.handle_gemini_error(e)

    def simulate_llm_response(self, prompt: str):
        """Nadpisujemy metodę symulacji, aby wysyłać zapytanie do prawdziwego Gemini API."""
        if not self.gemini_chat:
            self.append_message("System", "Brak aktywnego połączenia z modelem Gemini.", "system_tag")
            return

        try:
            # Wysłanie wiadomości użytkownika do trwającej sesji czatu z modelem
            response = self.gemini_chat.send_message(prompt)
            bot_reply = response.text
            
            # Wyświetlenie odpowiedzi w oknie czatu
            self.append_message("Mistrz Gry & Świat", bot_reply, "bot_tag")
        
        except Exception as e:
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
