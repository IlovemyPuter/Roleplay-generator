import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from character_manager import load_characters
from config import load_config
from generate_character import generate_character
from save_manager import load_game
from turning_point import TurningPoint, is_ready


class CharacterSelectWindow:
    """Okno wyboru postaci z poziomym przewijaniem kafelków."""

    def __init__(self, root, on_character_selected):
        self.root = root
        self.root.title("Wybierz postać do roli")
        self.root.geometry("1000x650")
        self.root.minsize(600, 480)
        self.on_character_selected = on_character_selected

        self.create_widgets()

        self.root.bind("<F8>", lambda event: self.handle_load_game_from_menu())

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

    def trigger_character_generation(self):
        description = self.description_entry.get("1.0", tk.END).strip()

        # Jeśli pole jest puste lub wciąż ma tekst placeholdera, przerywamy
        if not description or description == self.placeholder_text:
            messagebox.showwarning("Błąd", "Najpierw wpisz opis nowej postaci w polu tekstowym!", parent=self.root)
            return

        try:
            from google import genai
            from character_manager import save_character, load_characters

            settings = load_config()
            if not settings.api_key:
                messagebox.showerror("Błąd", "Brak klucza GEMINI_API_KEY w zmiennych środowiskowych.", parent=self.root)
                return

            client = genai.Client(api_key=settings.api_key)

            # Informacja dla użytkownika (generowanie może chwilę potrwać)
            messagebox.showinfo("Generowanie","Trwa generowanie nowej postaci przez AI... Kliknij OK i poczekaj chwilę.", parent=self.root)

            # 1. Wywołanie funkcji generującej (zwraca obiekt Character)[cite: 2]
            new_character = generate_character(description, client, model=settings.model)

            # 2. Zapisanie postaci do pliku JSON w folderze characters/[cite: 4]
            saved_path = save_character(new_character)
            print(f"✅ Zapisano nową postać do pliku: {saved_path}")

            # 3. Czyszczenie pola tekstowego
            self.description_entry.delete("1.0", tk.END)
            self.description_entry.insert("1.0", self.placeholder_text)
            self.description_entry.config(foreground="grey")

            # 4. Odświeżenie kafelków w oknie menu, aby nowa postać pojawiła się wizualnie
            self.refresh_character_tiles()

            messagebox.showinfo("Sukces",f"Postać została pomyślnie wygenerowana i zapisana!\nMożesz ją teraz wybrać z listy.", parent=self.root)  # lub info

        except Exception as e:
            messagebox.showerror("Błąd generowania", f"Nie udało się wygenerować postaci:\n{e}", parent=self.root)

    def create_widgets(self):
        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill=tk.X, padx=20, pady=15)

        header_label = ttk.Label(
            top_frame,
            text="Wybierz postać lub wpisz opis i wygeneruj nową",
            font=("Arial", 14, "bold")
        )
        header_label.pack(side=tk.TOP, anchor="w", pady=(0, 10))

        # --- Panela górna z polem wielolinijkowym i przyciskami ---
        input_container = ttk.Frame(top_frame)
        input_container.pack(fill=tk.X, expand=True)

        # 1. Wielolinijkowe pole tekstowe na opis nowej postaci (ScrolledText / Text)
        self.description_entry = scrolledtext.ScrolledText(
            input_container,
            height=4,  # Wysokość odpowiadająca prawemu panelowi z przyciskami
            font=("Arial", 10),
            wrap=tk.WORD,
            background="#ffffff"
        )
        self.description_entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 15))
        # --- OBSŁUGA NAPISU FANTOMOWEGO (PLACEHOLDER) ---
        self.placeholder_text = "Wpisz opis nowej postaci tutaj..."

        # Wstawiamy placeholder na start i ustawiamy szary kolor
        self.description_entry.insert("1.0", self.placeholder_text)
        self.description_entry.config(foreground="grey")

        # Biny wykrywające kliknięcie (wejście) i opuszczenie pola
        self.description_entry.bind("<FocusIn>", self._on_placeholder_focus_in)
        self.description_entry.bind("<FocusOut>", self._on_placeholder_focus_out)

        # 2. Ramka po prawej stronie na przyciski o jednakowej szerokości
        btn_box = ttk.Frame(input_container)
        btn_box.pack(side=tk.RIGHT, fill=tk.Y)

        btn_width = 18  # Jednakowa szerokość obu przycisków w znakach

        gen_btn = ttk.Button(
            btn_box,
            text="✨ Generuj",
            width=btn_width,
            command=self.trigger_character_generation
        )
        gen_btn.pack(side=tk.TOP, fill=tk.X, pady=(0, 6))

        load_btn = ttk.Button(
            btn_box,
            text="📁 Wczytaj grę",
            width=btn_width,
            command=self.handle_load_game_from_menu
        )
        load_btn.pack(side=tk.BOTTOM, fill=tk.X)

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

    def _on_placeholder_focus_in(self, event):
        """Usuwa placeholder po kliknięciu w pole tekstowe."""
        current_text = self.description_entry.get("1.0", tk.END).strip()
        if current_text == self.placeholder_text:
            self.description_entry.delete("1.0", tk.END)
            self.description_entry.config(foreground="black")  # Przywracamy normalny czarny tekst

    def _on_placeholder_focus_out(self, event):
        """Przywraca placeholder, jeśli pole zostało puste po wyjściu."""
        current_text = self.description_entry.get("1.0", tk.END).strip()
        if not current_text:
            self.description_entry.insert("1.0", self.placeholder_text)
            self.description_entry.config(foreground="grey")

    def refresh_character_tiles(self):
        """Odświeża listę kafelków w oknie wyboru."""
        # Usuwamy stare kafelki z ramki
        for widget in self.tiles_frame.winfo_children():
            widget.destroy()

        # Wczytujemy postacie na nowo (w tym nowo dodaną)[cite: 4]
        characters = load_characters()
        if not characters:
            empty_label = ttk.Label(
                self.tiles_frame,
                text="Brak postaci w folderze characters/.",
                font=("Arial", 12),
            )
            empty_label.pack(padx=20, pady=40)
        else:
            for char in characters:
                self.create_character_tile(char)

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
        """Otwiera okno dialogowe do podania własnych danych gracza, a następnie uruchamia grę."""
        # Tworzymy małe okno dialogowe Toplevel do personalizacji gracza
        dialog = tk.Toplevel(self.root)
        dialog.title("Twoja postać (Gracz)")
        dialog.geometry("450x400")
        dialog.grab_set()  # Blokuje okno główne do momentu zamknięcia dialogu

        ttk.Label(dialog, text="Wprowadź dane swojej postaci:", font=("Arial", 12, "bold")).pack(pady=(15, 10))

        form_frame = ttk.Frame(dialog, padding=10)
        form_frame.pack(fill=tk.BOTH, expand=True)

        # 1. Imię gracza
        ttk.Label(form_frame, text="Twoje imię / nazwa:", font=("Arial", 9, "bold")).pack(anchor="w")
        name_entry = ttk.Entry(form_frame, font=("Arial", 10))
        name_entry.pack(fill=tk.X, pady=(2, 10))
        name_entry.insert(0, "Bohater")

        # 2. Tło i rola
        ttk.Label(form_frame, text="Tło i rola (kim jesteś?):", font=("Arial", 9, "bold")).pack(anchor="w")
        bg_text = scrolledtext.ScrolledText(form_frame, height=4, font=("Arial", 9), wrap=tk.WORD)
        bg_text.pack(fill=tk.BOTH, expand=True, pady=(2, 10))
        bg_text.insert("1.0", "Wędrowiec szukający własnej ścieżki w nieprzyjaznym świecie.")

        # 3. Osobowość / Cechy
        ttk.Label(form_frame, text="Cechy osobowości:", font=("Arial", 9, "bold")).pack(anchor="w")
        personality_entry = ttk.Entry(form_frame, font=("Arial", 10))
        personality_entry.pack(fill=tk.X, pady=(2, 15))
        personality_entry.insert(0, "Ostrożny, zdeterminowany, ciekawski.")

        player_data = {}

        def on_confirm():
            player_data["name"] = name_entry.get().strip() or "Bohater"
            player_data["role_and_background"] = bg_text.get("1.0", tk.END).strip()
            player_data["personality"] = personality_entry.get().strip()
            dialog.destroy()

            # Zamykamy okno wyboru postaci i przekazujemy dane do gry
            self.root.destroy()
            # Wywołujemy funkcję zwrotną, przekazując towarzysza ORAZ słownik gracza
            self.on_character_selected(character, player_data)

        confirm_btn = ttk.Button(dialog, text="Rozpocznij przygodę", command=on_confirm)
        confirm_btn.pack(pady=(0, 15), ipadx=10, ipady=5)


class RoleplayChatApp:
    """Główne okno czatu z LLM."""

    def __init__(self, root, character, player_character=None):
        self.root = root
        self.character = character  # Towarzysz AI
        # Domyślne dane postaci gracza, jeśli nie przekazano osobnego słownika
        self.player_character = player_character or {
            "name": "Gracz (Ty)",
            "role_and_background": "Główny bohater opowieści podejmujący kluczowe decyzje.",
            "personality": "Zdeterminowany, reagujący na zmieniający się świat."
        }

        self.root.title(f"LLM Roleplay - Rozmawiasz z: {character['name']}")
        self.root.geometry("1280x700")  # Zwiększona szerokość, aby pomieścić 3 kolumny
        self.root.minsize(1000, 500)

        # Stan potrzebny do oceny warunków punktów zwrotnych
        self.turning_points: list[TurningPoint] = []
        self.game_state: dict[str, int | None] = {"tura": 0, "ostatni_rzut": None}

        self.style = ttk.Style()
        self.style.theme_use('clam')

        self.create_widgets()
        self.send_system_greeting()
        
        self.npcs: list[dict[str, str]] = []

    def create_widgets(self):
        # 1. Panel postaci po LEWEJ stronie okna
        self.create_characters_panel()

        # 2. Panel punktów zwrotnych po PRAWEJ stronie okna
        self.create_turning_points_panel()

        # 3. Główny obszar czatu na ŚRODKU
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # ------------------------------------------------------------------
        # 0. Pasek przycisków akcji nad czatem (Zapisz / Wczytaj)
        # ------------------------------------------------------------------
        action_bar = ttk.Frame(main_frame)
        action_bar.pack(fill=tk.X, pady=(0, 5))

        save_btn = ttk.Button(action_bar, text="💾 Zapisz grę",
                              command=lambda: getattr(self, 'handle_save', lambda: None)())
        save_btn.pack(side=tk.LEFT, padx=(0, 5))

        load_btn = ttk.Button(action_bar, text="📂 Wczytaj grę",
                              command=lambda: getattr(self, 'handle_load_in_game', lambda: None)())
        load_btn.pack(side=tk.LEFT)

        self.back_btn = ttk.Button(
            action_bar,
            text="Powrót"
        )
        self.back_btn.pack(side=tk.RIGHT)

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

        self.roll_button = ttk.Button(input_frame, text="🎲 Rzut k20")
        self.roll_button.pack(side=tk.RIGHT, padx=(0, 5))

        send_button = ttk.Button(input_frame, text="Wyślij", command=self.send_message)
        send_button.pack(side=tk.RIGHT)

    def create_turning_points_panel(self):
        """Panel po prawej stronie okna: stan gry oraz lista punktów zwrotnych w postaci wielolinijkowych kart."""
        panel = ttk.LabelFrame(self.root, text=" Punkty zwrotne ", padding=8)
        panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 10), pady=10)

        self.state_label = ttk.Label(panel, font=("Arial", 10, "bold"))
        self.state_label.pack(anchor="w", pady=(0, 6))

        # Kontener z przewijaniem pionowym dla punktów zwrotnych
        container = ttk.Frame(panel)
        container.pack(fill=tk.BOTH, expand=True)

        self.points_canvas = tk.Canvas(container, bg="#f0f2f5", highlightthickness=0, width=320)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.points_canvas.yview)

        # Ramka mieszcząca karty punktów zwrotnych
        self.points_container = ttk.Frame(self.points_canvas)
        self.points_container.bind(
            "<Configure>",
            lambda e: self.points_canvas.configure(scrollregion=self.points_canvas.bbox("all"))
        )

        self.points_canvas.create_window((0, 0), window=self.points_container, anchor="nw")
        self.points_canvas.configure(yscrollcommand=scrollbar.set)

        self.points_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

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
        
    def create_characters_panel(self):
        """Panel po lewej stronie okna: karty postaci gracza oraz towarzysza."""
        panel = ttk.LabelFrame(self.root, text=" Postacie ", padding=8)
        panel.pack(side=tk.LEFT, fill=tk.Y, padx=(10, 0), pady=10)

        container = ttk.Frame(panel)
        container.pack(fill=tk.BOTH, expand=True)

        self.chars_canvas = tk.Canvas(container, bg="#f0f2f5", highlightthickness=0, width=280)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.chars_canvas.yview)

        self.chars_container = ttk.Frame(self.chars_canvas)
        self.chars_container.bind(
            "<Configure>",
            lambda e: self.chars_canvas.configure(scrollregion=self.chars_canvas.bbox("all"))
        )

        self.chars_canvas.create_window((0, 0), window=self.chars_container, anchor="nw")
        self.chars_canvas.configure(yscrollcommand=scrollbar.set)

        self.chars_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.render_character_cards()

    def render_character_cards(self):
        """Renderuje karty dla postaci gracza, towarzysza oraz napotkanych NPC."""
        if not hasattr(self, 'chars_container'):
            return

        for widget in self.chars_container.winfo_children():
            widget.destroy()

        # --- KARTA 1: POSTAĆ GRACZA ---
        player_card = ttk.LabelFrame(self.chars_container, text=" 🗡️ Twoja postać ", padding=8)
        player_card.pack(fill=tk.X, padx=5, pady=(5, 10))

        tk.Label(
            player_card,
            text=self.player_character.get("name", "Gracz"),
            font=("Arial", 10, "bold"),
            fg="#0b5ed7",
            anchor="w"
        ).pack(anchor="w", fill=tk.X)

        tk.Label(
            player_card,
            text=f"Tło: {self.player_character.get('role_and_background', '')}",
            font=("Arial", 9),
            fg="#222222",
            justify=tk.LEFT,
            wraplength=245
        ).pack(anchor="w", fill=tk.X, pady=(4, 2))

        if self.player_character.get("personality"):
            tk.Label(
                player_card,
                text=f"Cechy: {self.player_character.get('personality')}",
                font=("Arial", 9, "italic"),
                fg="#555555",
                justify=tk.LEFT,
                wraplength=245
            ).pack(anchor="w", fill=tk.X, pady=(2, 0))

        # --- KARTA 2: TOWARZYSZ ---
        comp_card = ttk.LabelFrame(self.chars_container, text=" 🛡️ Towarzysz ", padding=8)
        comp_card.pack(fill=tk.X, padx=5, pady=5)

        tk.Label(
            comp_card,
            text=self.character.get("name", "Towarzysz"),
            font=("Arial", 10, "bold"),
            fg="#6f42c1",
            anchor="w"
        ).pack(anchor="w", fill=tk.X)

        tk.Label(
            comp_card,
            text=f"Rola: {self.character.get('role_and_background', '')}",
            font=("Arial", 9),
            fg="#222222",
            justify=tk.LEFT,
            wraplength=245
        ).pack(anchor="w", fill=tk.X, pady=(4, 4))

        tk.Label(
            comp_card,
            text=f"Osobowość: {self.character.get('personality', '')}",
            font=("Arial", 9),
            fg="#444444",
            justify=tk.LEFT,
            wraplength=245
        ).pack(anchor="w", fill=tk.X, pady=(2, 0))

        # --- SEKCJA 3: NAPOTKANE POSTACIE (NPC) ---
        if getattr(self, 'npcs', None):
            npc_section = ttk.LabelFrame(self.chars_container, text=" 👥 Napotkane postacie (NPC) ", padding=8)
            npc_section.pack(fill=tk.X, padx=5, pady=(10, 5))

            for npc in self.npcs:
                npc_box = ttk.Frame(npc_section)
                npc_box.pack(fill=tk.X, pady=(0, 6))

                tk.Label(
                    npc_box,
                    text=f"• {npc['name']}",
                    font=("Arial", 9, "bold"),
                    fg="#198754",
                    anchor="w"
                ).pack(anchor="w", fill=tk.X)

                tk.Label(
                    npc_box,
                    text=npc['description'],
                    font=("Arial", 8),
                    fg="#333333",
                    justify=tk.LEFT,
                    wraplength=235
                ).pack(anchor="w", fill=tk.X, padx=(8, 0))