from punkty_zwrotne import (
    stworz_zadanie_fabularne,
    zweryfikuj_wpis,
    sprawdz_warunek,
    wykonaj_punkt,
    pobierz_oczekujace
)

print("--- URUCHAMIAM TESTY KONTROLI BŁĘDÓW ---")

# 1. Test walidacji: brak pola
punkt_zly = {"id": 1, "tytul": "Test", "opis": "Opis", "stan": "oczekujacy"}
assert zweryfikuj_wpis(punkt_zly) == False, "Błąd: Punkt bez warunku przeszedł walidację!"
print("[OK] Odrzucenie braku pól działa.")

# 2. Test walidacji: float zamiast int w wartości warunku
punkt_float = stworz_zadanie_fabularne(1, "Test", "Opis", "tura", 3, "Skutek")
punkt_float["warunek"]["wartosc"] = 3.5
assert zweryfikuj_wpis(punkt_float) == False, "Błąd: Float przeszedł jako poprawny int!"
print("[OK] Blokada typów zmiennoprzecinkowych działa.")

# 3. Test sprawdzania: punkt już wykonany daje False
p_wykonany = stworz_zadanie_fabularne(1, "Test", "Opis", "tura", 1, "Skutek")
p_wykonany["stan"] = "wykonany"
stan = {"tura": 5, "ostatni_rzut": 10}
assert sprawdz_warunek(p_wykonany, stan) == False, "Błąd: Wykonany punkt nie powinien zwracać True!"
print("[OK] Blokada dla wykonanych punktów działa.")

# 4. Test sprawdzania: brak klucza ostatni_rzut w stanie gry
p_rzut = stworz_zadanie_fabularne(1, "Test", "Opis", "rzut", 10, "Skutek")
stan_pusty = {"tura": 1}
assert sprawdz_warunek(p_rzut, stan_pusty) == False, "Błąd: Brak rzutu w stanie powinien dać False!"
print("[OK] Obsługa braku rzutu działa.")

# 5. Test równego progu (rzut równy wartości)
p_prog = stworz_zadanie_fabularne(1, "Test", "Opis", "rzut", 12, "Skutek")
stan_rowny = {"tura": 1, "ostatni_rzut": 12}
assert sprawdz_warunek(p_prog, stan_rowny) == True, "Błąd: Rzut równy progowi musi dać True!"
print("[OK] Warunek równego progu działa.")

# 6. Test wielokrotnego wykonania punktu
skutek_pierwszy = wykonaj_punkt(p_prog)
skutek_drugi = wykonaj_punkt(p_prog)
assert skutek_pierwszy == "Skutek"
assert skutek_drugi is None, "Błąd: Drugie wykonanie powinno zwrócić None!"
print("[OK] Blokada wielokrotnego wykonania działa.")

print("\nWSZYSTKIE TESTY BŁĘDÓW ZALICZONE.")