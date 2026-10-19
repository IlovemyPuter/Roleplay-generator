# Roleplay-generator

## Problem użytkownika
Gracz chce prowadzić wciągającą sesję RPG, w której postacie reagują na jego decyzje, a fabuła rozwija się bez konieczności posiadania Game Mastera.

## Mapa procesu

| Etap | Sprawdzalny rezultat | Punkt kontroli jakości |
|---------------|--------------|-------------------------------|
|1. Rozpoznanie potrzeb	|Lista wymagań gracza i właściciela systemu	|Każde wymaganie ma kryterium akceptacji, a zespół zrobił przegląd listy.|
|2. Plan i projekt systemu	|Podział na moduły, zadania i 4 przyrosty|	Każdy moduł ma określoną odpowiedzialność i sposób komunikacji z innymi.|
|3. Przyrost 1: rozmowa z postacią	|Działająca rozmowa z ręcznie zdefiniowaną postacią	|Test 10 wiadomości: postać zachowuje styl i uwzględnia wcześniejszy kontekst.|
|4. Przyrost 2: postać i zapis gry	|Generowanie postaci przez LLM oraz zapis i wznawianie stanu gry	|Postać ma określone cechy, a po wznowieniu gry zachowany jest poprzedni stan.|
|5. Przyrost 3: generowanie fabuły	|Wygenerowany zarys fabuły i punkty zwrotne	|Każdy punkt zwrotny ma warunek i skutek, a przegląd potwierdza brak sprzeczności między nimi.|
|6. Przyrost 4: połączenie fabuły z grą|	Punkty zwrotne wpływają na przebieg rozgrywki|	Wykonanie określonych działań przez gracza wywołuje odpowiednią zmianę fabuły.|
|7. Testy integracyjne i poprawki|	Przetestowane połączenie wszystkich głównych funkcji	|Wszystkie przypadki testowe z listy zaliczone, brak otwartych błędów krytycznych.
|8. Pierwsze wydanie|	Uruchamialna wersja aplikacji z instrukcją obsługi|	Nowy użytkownik może rozpocząć grę, rozegrać sesję i wrócić do zapisanej rozgrywki.|

## Wybrany model procesu: przyrostowy
Wymagania i projekt ustalamy na początku. Potem system powstaje w czterech przyrostach. Każdy przyrost dodaje nowe funkcje do działającej wersji i nie wymaga przerabiania wcześniejszych.

## Uzasadnienie wyboru: 3 argumenty
1.	Zawsze działająca wersja: po każdym przyroście mamy system, który można uruchomić, pokazać i przetestować.
2.	Niezależne moduły: rozmowa, generowanie postaci, zapis i fabuła to osobne funkcje. Można je dokładać po kolei i rozdzielić między osoby w zespole.
3.	Najważniejsze najpierw: rozmowa z postacią powstaje w pierwszym przyroście, więc jej błędy wykrywamy, zanim dołożymy resztę. Gdy zabraknie czasu, oddajemy działający produkt bez ostatnich funkcji.

## Najważniejsze ryzyka
1.	Nieprzewidywalność LLM: model może zapominać szczegóły, zmieniać styl postaci lub generować niespójną fabułę. Ograniczamy ryzyko przez testy i przekazywanie historii rozmowy.
2.	Problemy z integracją modułów: części zespołu mogą być niezgodne lub gotowe w różnych terminach. Ograniczamy ryzyko przez ustalenie wspólnych interfejsów, regularną integrację i testy.

## Cel systemu
Platforma umożliwia graczom prowadzenie sesji RPG z wykorzystaniem LLM, bez konieczności posiadania człowieka w roli Game Mastera (mistrza gry). System generuje postacie i fabułę, reaguje na decyzje gracza oraz zapisuje postęp rozgrywki, dzięki czemu można wrócić do niej później.

## Interesariusze i ich potrzeby

### 1. Gracz — główny użytkownik
Potrzeby i korzyści:
-	Gra w RPG bez konieczności organizowania grupy i szukania Game Mastera.
-	Możliwość samodzielnego odkrywania historii i podejmowania decyzji.
-	Rozmowy z postaciami, które reagują na działania gracza.
-	Zapisywanie rozgrywki i kontynuowanie jej w dogodnym momencie.

### 2. Właściciel platformy — osoba lub firma
Potrzeby i korzyści:
-	Rozwijanie produktu dla osób zainteresowanych grami RPG.
-	Możliwość zdobywania użytkowników i budowania społeczności.
-	Potencjalne przychody z subskrypcji lub płatnych funkcji.
-	Rozwijanie platformy o nowe światy, postacie i mechaniki.

### 3. Zespół projektowy i deweloperzy
Potrzeby i korzyści:
-	Jasno określone wymagania i zakres prac.
-	Możliwość rozwijania i testowania kolejnych funkcji.
-	Sprawny podział odpowiedzialności i integracja modułów.
-	Zdobycie doświadczenia w tworzeniu aplikacji wykorzystującej LLM.

### 4. Społeczność graczy RPG — potencjalni odbiorcy
Potrzeby i korzyści:
-	Eksperymentowanie z własnymi historiami i postaciami.
-	Rozgrywka bez konieczności dopasowywania terminów całej grupy.
-	Alternatywa dla tradycyjnych sesji RPG, a niekoniecznie ich zastępstwo.

## Kto może być właścicielem systemu?
Przyjęte założenie: właścicielem systemu jest mała firma lub zespół rozwijający internetową platformę RPG opartą na AI.

## Wartość systemu dla użytkownika i właściciela
|Dla gracza	|Dla właściciela|
|---------------|--------------|
|Rozgrywka dostępna bez Game Mastera|	Potencjalne źródło przychodów|
|Fabuła reagująca na decyzje	|Możliwość rozwoju produktu|
|Własne postacie i światy|	Pozyskiwanie i utrzymywanie użytkowników|
|Zapis i wznawianie gry|	Możliwość dodawania nowych funkcji|

## Harmonogram
### 15.10 do 18.10: Przyrost 1, rozmowa z postacią
-	15.10: kontrakty ustalone
-	16.10: atrapa
-	18.10: prawdziwe wywołanie LLM, test 10 wiadomości
### 19.10 do 25.10: Przyrost 2, postać i zapis gry
-	19.10 do 21.10: generowanie postaci przez LLM
-	22.10 do 24.10: zapis i wznawianie stanu gry
-	25.10: test, czy po wznowieniu stan się zgadza
### 26.10 do 1.11: Przyrost 3, fabuła i punkty zwrotne
-	26.10 do 28.10: struktura punktu zwrotnego w kodzie (warunek, skutek, stan)
-	29.10 do 31.10: generowanie fabuły przez LLM
-	1.11: przegląd, czy punkty nie są sprzeczne
### 2.11 do 4.11: Przyrost 4, połączenie fabuły z grą
-	2.11 do 3.11: punkty zwrotne wpływają na rozgrywkę
-	4.11: test, czy działanie gracza wywołuje zmianę fabuły
### 5.11 do 6.11: testy integracyjne i poprawki
-	5.11: przejście wszystkich przypadków testowych
-	6.11: poprawki błędów krytycznych
### 7.11: pierwsze wydanie
-	uruchamialna wersja i instrukcja obsługi
-	nowy użytkownik przechodzi grę od startu do wznowienia zapisu
### Podział zadań w przyrostach 2 i 4 ustalimy po zakończeniu przyrostu 1.

