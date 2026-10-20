
''' === pip install -U google-genai === ''' # Instalacja wymaganego pakietu do połączenia się z Gemini API 
from google import genai
from google.genai import types

# Importujemy interfejs graficzny
import tkinter as tk

# Importujemy dane postaci i klasy okien z pliku interface.py
from interface import CharacterSelectWindow, RoleplayChatApp

# Inicjalizacja klienta
try:
    client = genai.Client(api_key="AQ.Ab8RN6ICn9LUJBfd2EDE4eRXAwgY0uvON5w79Xpc-04wM9Zxew")
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

        # 2. Osobowość i zasady dla AI (System Instruction)
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
                    temperature=0.8,
                )
            )

            # Automatycznie generujemy początek przygody od razu po starcie czatu
            self.start_adventure()

        except Exception as e:
            self.append_message("System", f"Błąd tworzenia sesji Gemini: {e}", "system_tag")
            self.gemini_chat = None

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
            self.append_message("System", f"Nie udało się rozpocząć przygody: {e}", "system_tag")

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
            error_str = str(e)
            if "503" in error_str or "UNAVAILABLE" in error_str:
                error_msg = (
                    "⚠️ Model Gemini jest obecnie mocno obciążony (błąd 503). "
                    "To chwilowy problem po stronie Google. Spróbuj wysłać wiadomość ponownie za kilka sekund."
                )
            else:
                error_msg = f"Wystąpił błąd podczas komunikacji z API: {e}"
                
            self.append_message("System", error_msg, "system_tag")


'''
def main():
    print("=== INICJACJA SILNIKA RPG ===")
    
    # 3. Konfiguracja czatu z instrukcją systemową
    chat = client.chats.create(
        model="gemini-3.7-flash",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.8, # Wyższa temperatura = bardziej kreatywne opisy
        )
    )

    # 4. Rozpoczęcie przygody (Prompt inicjujący)
    start_prompt = (
        "Rozpocznij przygodę. Stwórz krótkie, klimatyczne wprowadzenie. "
        "Obudziłem się w opuszczonej ruinie na skraju przeklętego lasu. "
        "Opisz otoczenie i zapytaj mnie o pierwszy krok."
    )

    print("\n--- ROZPOCZĘCIE SESJI ---\n")
    response = chat.send_message(start_prompt)
    print(f"GM: {response.text}\n")

    # 5. Główna pętla gry (Game Loop)
    while True:
        try:
            player_input = input("Ty: ")
            
            # Warunek wyjścia z gry
            if player_input.lower() in ["exit", "quit", "koniec"]:
                print("\nSesja zakończona. Do zobaczenia przy kolejnej przygodzie!")
                break
                
            if not player_input.strip():
                continue

            # Wysłanie decyzji gracza do Gemini
            response = chat.send_message(player_input)
            print(f"\nGM: {response.text}\n")

        except KeyboardInterrupt:
            print("\nPrzerwano sesję.")
            break

if __name__ == "__main__":
    main()
    '''

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