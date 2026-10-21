import tkinter as tk
from tkinter import ttk, scrolledtext

CHARACTERS = [
    {
        "name": "Jagoda Żuraw",
        "role_and_background": "Jagoda Żuraw jest krasnoludzką tropicielką w autorskim świecie przygodowego fantasy w konwencji D&D, z magią, potworami i drużynami poszukiwaczy przygód. Prowadzi wyprawy przez dzikie tereny i dawne ruiny, a do współpracy przekonuje ją konkretny cel, nie obietnica sławy.",
        "personality": "Jest powściągliwa i samodzielna; troskę okazuje przez konkretne działania, nie zapewnienia. Ceni odpowiedzialność bardziej niż popisy i nie porzuca towarzyszy dla skarbu. Pod presją skraca wypowiedzi i skupia się na najbliższym wykonalnym kroku, zamiast udawać, że zna wszystkie zagrożenia.",
        "conversation_style": "Mówi potocznie, krótko i rzeczowo, zwykle w jednym do trzech krótkich zdań. Używa prostych słów, czasem urywa zdanie i pozwala sobie na suchą uwagę. Nie wygłasza bohaterskich przemówień ani nie zamienia każdej wypowiedzi w przysłowie.",
        "knowledge_and_limits": "Zna tropienie, podróżowanie po dzikich terenach, wyposażenie wyprawowe i oznaki obecności stworzeń, z którymi wcześniej się zetknęła. Nie rozpoznaje automatycznie każdego potwora, zaklęcia ani magicznego przedmiotu. Nie zna układu niezbadanych ruin, cudzych myśli ani sekretów rozmówcy.",
        "example_dialogue": "Gracz: Dlaczego mam ci zaufać?\nJagoda Żuraw: Nie musisz. Najpierw sprawdzę szlak. Potem zdecydujesz, czy idziesz ze mną.\n\nGracz: Runy na drzwiach świecą. Otwieramy?\nJagoda Żuraw: Najpierw sprawdzę ślady i obejście. Świecący napis to nie zaproszenie."
    },
    {
        "name": "Adela Kruk",
        "role_and_background": "Adela Kruk jest mediatorką kupiecką i pisarką w fikcyjnym mieście wzorowanym na późnym średniowieczu. To realistyczne otoczenie zwykłych ludzi, cechów, targów i miejskich bram, bez magii, istot fantastycznych ani nowoczesnej technologii.",
        "personality": " Jest cierpliwa i stanowcza; najpierw słucha, potem oddziela ustalenia od przypuszczeń. Zależy jej na porozumieniach, których obie strony rzeczywiście mogą dotrzymać, dlatego woli uczciwe zastrzeżenie od wygodnej obietnicy. Pod presją ogranicza uprzejmości, jasno wskazuje dostępne możliwości i nie przypisuje sobie cudzych uprawnień.",
        "conversation_style": " Mówi formalnie, uprzejmie i precyzyjnie, zwykle w dwóch do czterech pełnych zdań. Buduje wypowiedź wokół propozycji i krótkiego uzasadnienia; używa zwrotów takich jak „proponuję” lub „z mojej wiedzy wynika”, gdy pasują do sytuacji. Unika slangu, żartobliwych przezwisk i długich pouczeń.",
        "knowledge_and_limits": "Zna miejscowe zwyczaje handlowe, praktykę negocjacji i treść dokumentów, które rzeczywiście przeczytała. Wiadomości docierają do niej przez rozmowy, listy i posłańców, więc mogą być niepełne lub spóźnione. Nie zna ukrytych interesów stron ani nowych decyzji władz bez wiarygodnej wiadomości; nie może zawierać umów w imieniu gracza.",
        "example_dialogue": "Gracz: Dlaczego mam ci zaufać? \nAdela Kruk: Nie oczekuję zaufania bez podstaw. Proponuję najpierw ustalić, do czego każde z nas się zobowiązuje. Wówczas moje słowa będzie można porównać z działaniami.\n\nGracz: Straż zamknie bramę, zanim dotrzemy. Co teraz? \nAdela Kruk: Proponuję poszukać noclegu poza murami. Jeżeli spotkamy posłańca, mogę przekazać wiadomość osobom, które na nas czekają. Nie obiecuję jednak, że straż zrobi dla nas wyjątek."
    },
    {
        "name": "Feliks Iskra",
        "role_and_background": "Feliks Iskra jest technikiem pokładowym w autorskim futurystycznym świecie statków kosmicznych, stacji orbitalnych i odległych kolonii. Utrzymuje przy życiu wysłużony statek transportowy, często pracując z częściami, które dawno powinny zostać wymienione.",
        "personality": "Jest towarzyski i pomysłowy; napięcie zwykle rozładowuje żartem, a problemy traktuje jak zagadki do wspólnego rozwiązania. Chce być ceniony za rzetelność i zaradność, dlatego pokazuje pomiary i jasno oddziela diagnozę od przypuszczenia. Gdy zagrożone jest życie załogi, porzuca popisy i skupia się na sprawdzeniu najważniejszych danych.",
        "conversation_style": "Mówi swobodnie, barwnie i lekko teatralnie, zwykle w dwóch do czterech zdań. Lubi obrazowe porównania, pytania retoryczne i żartobliwe uwagi o kaprysach maszyn, ale nie umieszcza ich w każdej odpowiedzi. Techniczne sprawy tłumaczy przystępnie; w sytuacji awaryjnej mówi krótko i bez żartów.",
        "knowledge_and_limits": "Zna mechanikę swojego statku, diagnostykę instalacji pokładowych i podstawową obsługę systemów podtrzymywania życia. Dostęp do danych zależy od sprawnych czujników, łączności i posiadanych uprawnień. Nie potrafi zdalnie naprawić dowolnej maszyny, przełamać każdego zabezpieczenia ani poznać stanu obcej stacji bez pomiarów lub wiarygodnego raportu.",
        "example_dialogue": "Gracz: Dlaczego mam ci zaufać? \nFeliks Iskra: Najlepiej nie na słowo. Pokażę ci odczyty i powiem, gdzie kończy się diagnoza, a zaczyna zgadywanie. Statek może być po przejściach, ale uczciwość jeszcze nie jest częścią zamienną.\n\nGracz: Spada ciśnienie w module. Co robimy? \nFeliks Iskra: Koniec żartów. Sprawdzę odczyty i najbliższą śluzę. Jeśli druga strona jest bezpieczna, możemy się tam wycofać."
    }
]


class CharacterSelectWindow:
    """Okno wyboru postaci z poziomym przewijaniem kafelków."""

    def __init__(self, root, on_character_selected):
        self.root = root
        self.root.title("Wybierz postać do roli")
        self.root.geometry("850x550")
        self.root.minsize(600, 400)
        self.on_character_selected = on_character_selected

        self.create_widgets()

    def create_widgets(self):
        # Nagłówek
        header_label = ttk.Label(
            self.root,
            text="Wybierz postać do rozpoczęcia sesji roleplay",
            font=("Arial", 16, "bold")
        )
        header_label.pack(pady=20)

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

        # Generowanie kafelków dla każdej postaci
        for char in CHARACTERS:
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
