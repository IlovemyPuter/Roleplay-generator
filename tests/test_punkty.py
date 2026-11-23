from unittest import TestCase

from pydantic import ValidationError

from turning_point import Condition, TurningPoint, is_ready, mark_executed

print("--- URUCHAMIAM TESTY KONTROLI BŁĘDÓW ---")

# 1. Test walidacji: brak pola
punkt_zly = {"id": 1, "title": "Test", "description": "Opis", "status": "oczekujacy"}
with TestCase().assertRaises(ValidationError, msg="Błąd: Punkt bez warunku przeszedł walidację!"):
    TurningPoint.model_validate(punkt_zly)
print("[OK] Odrzucenie braku pól działa.")

# 2. Test walidacji: float zamiast int w wartości warunku
punkt_float = TurningPoint(
    id=1, title="Test", description="Opis",
    condition=Condition(type="tura", value=3), effect="Skutek", status="oczekujacy",
).model_dump()
punkt_float["condition"]["value"] = 3.5
with TestCase().assertRaises(ValidationError, msg="Błąd: Float przeszedł jako poprawny int!"):
    TurningPoint.model_validate(punkt_float)
print("[OK] Blokada typów zmiennoprzecinkowych działa.")

# 3. Test sprawdzania: punkt już wykonany daje False
p_wykonany = TurningPoint(
    id=1, title="Test", description="Opis",
    condition=Condition(type="tura", value=1), effect="Skutek", status="oczekujacy",
)
p_wykonany.status = "wykonany"
stan = {"tura": 5, "ostatni_rzut": 10}
assert is_ready(p_wykonany, stan) == False, "Błąd: Wykonany punkt nie powinien zwracać True!"
print("[OK] Blokada dla wykonanych punktów działa.")

# 4. Test sprawdzania: brak klucza ostatni_rzut w stanie gry
p_rzut = TurningPoint(
    id=1, title="Test", description="Opis",
    condition=Condition(type="rzut", value=10), effect="Skutek", status="oczekujacy",
)
stan_pusty = {"tura": 1}
assert is_ready(p_rzut, stan_pusty) == False, "Błąd: Brak rzutu w stanie powinien dać False!"
print("[OK] Obsługa braku rzutu działa.")

# 5. Test równego progu (rzut równy wartości)
p_prog = TurningPoint(
    id=1, title="Test", description="Opis",
    condition=Condition(type="rzut", value=12), effect="Skutek", status="oczekujacy",
)
stan_rowny = {"tura": 1, "ostatni_rzut": 12}
assert is_ready(p_prog, stan_rowny) == True, "Błąd: Rzut równy progowi musi dać True!"
print("[OK] Warunek równego progu działa.")

# 6. Test wielokrotnego wykonania punktu
mark_executed(p_prog)
assert p_prog.status == "wykonany"
mark_executed(p_prog)
assert p_prog.status == "wykonany"
assert is_ready(p_prog, stan_rowny) == False, "Błąd: Wykonany punkt nie powinien uruchomić się ponownie!"
print("[OK] Blokada wielokrotnego wykonania działa.")

print("\nWSZYSTKIE TESTY BŁĘDÓW ZALICZONE.")
