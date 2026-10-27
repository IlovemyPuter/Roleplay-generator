import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from character_manager import load_characters
from save_manager import load_game


class CharacterSelectWindow:
    """Okno wyboru postaci z poziomym przewijaniem kafelków."""

    def __init__(self, root, on_character_selected):
        self.root = root
        self.root.title("Wybierz postać do roli")
        self.root.geometry("850x550")
        self.root.minsize(600, 400)
        self.on_character_selected = on_character_selected

        self.create_widgets()


    def handle_load_game_from_menu(self):
        """Obsługa wczytywania gry z menu głównego."""
        success, data = load_game(parent_window=self.root)
        
        if success:
            # Importujemy klasę tutaj, co eliminuje błąd cyklicznego importu
            from main import HybridGMRoleplayChatApp
            
            # 1. Ukrywamy lub niszczymy okno menu głównego
            self.root.destroy()
            # 2. Tworzymy nowe okno dla gry
            game_window = tk.Tk()
            # 3. Uruchamiamy aplikację czatu, przekazując wczytane dane z pliku JSON
            # (Przekazujemy character z data["character"] oraz całe data do argumentu save_data)
            app = HybridGMRoleplayChatApp(game_window, character=data["character"], save_data=data)
            
            game_window.mainloop()
        else:
            if data != "Anulowano wybór pliku.":
                print(f"Błąd wczytywania: {data}")

    def create_widgets(self):
        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill=tk.X, padx=20, pady=20)

        header_label = ttk.Label(
            top_frame,
            text="Wybierz postać do rozpoczęcia sesji roleplay",
            font=("Arial", 16, "bold")
        )
        header_label.pack(side=tk.LEFT)

        # Przycisk wczytywania w oknie wyboru postaci
        load_btn = ttk.Button(
            top_frame,
            text="📁 Wczytaj grę",
            command=self.handle_load_game_from_menu
        )
        load_btn.pack(side=tk.RIGHT)

        # Kontener główny na scrollowalny obszar
        container = ttk.Frame(self.root)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        # Canvas + Scrollbar do poziomego przewijania
        self.canvas = tk.Canvas(container, bg="#f0f2f5", highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="horizontal", command=self.canvas.xview)

        # Ramka mieszcząca kafelki wewnątrz Canvasa
        self.tiles_frame = ttk.Frame(self.canvas)
        self.tiles_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.tiles_frame, anchor="nw")
        self.canvas.configure(xscrollcommand=scrollbar.set)

        # Pakowanie komponentów przewijania
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))

        # Generowanie kafelków dla każdej postaci z folderu characters/
        characters = load_characters()
        if not characters:
            empty_label = ttk.Label(
                self.tiles_frame,
                text="Brak postaci w folderze characters/.",
                font=("Arial", 12),
            )
            empty_label.pack(padx=20, pady=40)
            messagebox.showwarning(
                "Brak postaci",
                "Nie znaleziono poprawnych plików JSON w folderze characters/.",
                parent=self.root,
            )
        else:
            for char in characters:
                self.create_character_tile(char)

        # Obsługa przewijania kółkiem myszy
        self.canvas.bind_all("<Shift-MouseWheel>", self._on_mouse_wheel)

    def create_character_tile(self, char):
        """Tworzy pojedynczy kafelek dla postaci ze wszystkimi danymi z szablonu."""
        # Ramka kafelka
        tile = ttk.LabelFrame(self.tiles_frame, text=f" {char['name']} ", padding=15)
        tile.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        # Stały rozmiar kafelka
        inner_content = ttk.Frame(tile, width=320, height=380)
        inner_content.pack(fill=tk.BOTH, expand=True)
        inner_content.pack_propagate(False)

        # Tekst z informacjami z szablonu
        details_text = (
            f"Role and background:\n{char['role_and_background']}\n\n"
            f"Personality:\n{char['personality']}\n\n"
            f"Conversation style:\n{char['conversation_style']}\n\n"
            f"Knowledge and limits:\n{char['knowledge_and_limits']}\n\n"
            f"Dialogue examples:\n{char['example_dialogue']}"
        )

        # 1. Przycisk wyboru
        select_btn = ttk.Button(
            inner_content,
            text="Wybierz tę postać",
            command=lambda c=char: self.select_character(c)
        )
        select_btn.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0), ipady=3)

        # 2. Pole tekstowe opisu
        text_widget = scrolledtext.ScrolledText(
            inner_content,
            wrap=tk.WORD,
            font=("Arial", 9),
            background="#ffffff"
        )
        text_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Wstawienie informacji do pola i zablokowanie edycji
        text_widget.insert("1.0", details_text)
        text_widget.config(state=tk.DISABLED)

    def _on_mouse_wheel(self, event):
        """Przewijanie poziome"""
        self.canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")

    def select_character(self, character):
        """Zamyka okno wyboru i przekazuje wybraną postać do głównej aplikacji."""
        self.root.destroy()
        self.on_character_selected(character)


class RoleplayChatApp:
    """Główne okno czatu z LLM."""

    def __init__(self, root, character):
        self.root = root
        self.character = character
        self.root.title(f"LLM Roleplay - Rozmawiasz z: {character['name']}")
        self.root.geometry("650x650")
        self.root.minsize(450, 450)

        self.style = ttk.Style()
        self.style.theme_use('clam')

        self.create_widgets()
        self.send_system_greeting()

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        # ------------------------------------------------------------------
        # 0. Pasek przycisków akcji nad czatem (Zapisz / Wczytaj)
        # ------------------------------------------------------------------
        action_bar = ttk.Frame(main_frame)
        action_bar.pack(fill=tk.X, pady=(0, 5))

        save_btn = ttk.Button(action_bar, text="💾 Zapisz grę", command=lambda: getattr(self, 'handle_save', lambda: None)())
        save_btn.pack(side=tk.LEFT, padx=(0, 5))

        load_btn = ttk.Button(action_bar, text="📂 Wczytaj grę", command=lambda: getattr(self, 'handle_load_in_game', lambda: None)())
        load_btn.pack(side=tk.LEFT)

        # ------------------------------------------------------------------
        # 1. Historia konwersacji
        # ------------------------------------------------------------------
        history_frame = ttk.LabelFrame(main_frame, text=f" Czat z: {self.character['name']} ", padding="5")
        history_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.chat_display = scrolledtext.ScrolledText(
            history_frame,
            wrap=tk.WORD,
            font=("Arial", 11),
            state=tk.DISABLED,
            background="#f8f9fa"
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True)

        # Style tagów tekstowych
        self.chat_display.tag_config("user_tag", foreground="#0b5ed7", font=("Arial", 11, "bold"))
        self.chat_display.tag_config("bot_tag", foreground="#198754", font=("Arial", 11, "bold"))
        self.chat_display.tag_config("companion_tag", foreground="#6f42c1", font=("Arial", 11, "bold"))
        self.chat_display.tag_config("system_tag", foreground="#6c757d", font=("Arial", 10, "italic"))

        # ------------------------------------------------------------------
        # 2. Obszar wprowadzania wiadomości
        # ------------------------------------------------------------------
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.msg_entry = ttk.Entry(input_frame, font=("Arial", 11))
        self.msg_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.msg_entry.focus()
        self.msg_entry.bind("<Return>", lambda event: self.send_message())

        send_button = ttk.Button(input_frame, text="Wyślij", command=self.send_message)
        send_button.pack(side=tk.RIGHT)

    def append_message(self, sender: str, message: str, tag_name: str):
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, f"{sender}: ", tag_name)
        self.chat_display.insert(tk.END, f"{message}\n\n")
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)

    def send_system_greeting(self):
        """Wiadomość startowa informująca o załadowanej postać"""
        intro = (
            f"Załadowano profil postaci:\n"
            f"• Rola: {self.character['role_and_background']}\n"
            f"• Osobowość: {self.character['personality']}"
        )
        self.append_message("System", intro, "system_tag")

    def send_message(self):
        user_text = self.msg_entry.get().strip()
        if not user_text:
            return

        # Wyświetlenie wiadomości użytkownika jako "Me"
        self.append_message("Me", user_text, "user_tag")
        self.msg_entry.delete(0, tk.END)
        self.root.after(600, lambda: self.simulate_llm_response(user_text))

    def start_streaming_message(self, sender: str, tag_name: str):
        """Rozpoczyna nową wiadomość strumieniową w oknie czatu[cite: 2]."""
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, f"{sender}: ", tag_name)
        # Zapisujemy indeks, od którego zaczyna się treść wiadomości
        self._stream_start_index = self.chat_display.index("end-1c")
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)

    def update_streaming_message(self, text: str):
        """Aktualizuje treść wiadomości w trakcie streamowania tokenów[cite: 2]."""
        self.chat_display.config(state=tk.NORMAL)
        # Usuwamy dotychczasowy tekst odpowiedzi i wstawiamy nowy, powiększony fragment
        self.chat_display.delete(self._stream_start_index, tk.END)
        self.chat_display.insert(tk.END, text)
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)

    def finish_streaming_message(self):
        """Kończy strumieniowanie, dodając odstępy na końcu[cite: 2]."""
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, "\n\n")
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)