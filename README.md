# Roleplay-generator

Aplikacja desktopowa w Pythonie do prowadzenia sesji RPG z Mistrzem Gry opartym na modelu Google Gemini. Pozwala wygenerować postać, prowadzić rozmowę fabularną, śledzić punkty zwrotne oraz zapisywać i wznawiać stan gry.

## Konfiguracja wstępna

1. Utwórz i aktywuj wirtualne środowisko Pythona:

```bash
python -m venv .venv
.venv\Scripts\activate
```

2. Zainstaluj zależności:

```bash
pip install -r requirements.txt
```

3. Utwórz plik `.env` w głównym katalogu projektu (plik jest ignorowany przez Git) i wpisz dane:

```env
GEMINI_API_KEY=twój_klucz_api_tutaj
GEMINI_MODEL=wybrany_model
```

## Problem użytkownika

Gracz chce rozegrać sesję RPG samodzielnie, gdy nie ma ekipy ani osoby prowadzącej grę. Potrzebuje postaci, Mistrza Gry reagującego na decyzje oraz zapisu postępu.

## Zakres obecnej wersji

- **Zrealizowane:** generowanie postaci przez LLM, rozmowa z Mistrzem Gry w czacie, lista postaci, rzut kością, punkty zwrotne zmieniające fabułę oraz zapis i wczytanie stanu gry do pliku JSON.
- **Poza zakresem / na później:** własny opis settingu przez gracza, blokada przycisku wysyłania w trakcie oczekiwania na odpowiedź oraz komunikat przy uszkodzonym pliku zapisu.

## Model pracy i zespół

Wybrany model: **przyrostowy** (4 iteracje, podział na moduły i wcześniejsze ustalanie kontraktów danych).

- **Mateusz:** zarządzanie projektem, logika punktów zwrotnych i tury, testy.
- **Volodymyr:** integracja z Google Gemini, walidacja danych, obsługa błędów i limitów API, testy.
- **Kamil:** interfejs w Tkinterze, widok postaci, panel punktów zwrotnych, rzut kością, komunikaty, testy.
- **Witold:** zapis i wczytanie stanu gry do pliku JSON, testy całościowe.

## Przebieg prac

- **Iteracja 1:** rozmowa z postacią i utrzymanie kontekstu.
- **Iteracja 2:** generowanie postaci przez LLM oraz zapis i wczytanie stanu gry.
- **Iteracja 3:** generowanie zarysu fabuły i punktów zwrotnych, panel w UI i rzut kością.
- **Iteracja 4:** podpięcie punktów zwrotnych do tury, obsługa błędów, testy automatyczne w GitHub Actions i poprawki.

## Ryzyka i zabezpieczenia

- **Błędy formatu odpowiedzi i limity API:** walidacja struktur, ponawianie prób przy błędnym JSON oraz obsługa błędów bez zawieszania aplikacji.
- **Bezpieczeństwo kluczy:** przechowywanie klucza API wyłącznie w lokalnym pliku `.env`.
- **Niespójności między modułami i testami:** wspólne kontrakty, testy w `pytest` i uruchamianie testów w GitHub Actions.

## Interesariusze i wartość

- **Gracz:** szybki start sesji solo, reakcja fabuły na decyzje i zapis postępu w pliku JSON.
- **Zespół projektowy:** podział odpowiedzialności na moduły, praca na branchach i Pull Requestach oraz weryfikacja w CI.
- **Właściciel / odbiorca:** podstawa pod dalszy rozwój mechanik RPG i nowych trybów gry.
