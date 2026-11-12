def stworz_zadanie_fabularne(id_p, tytul, opis, typ_w, wartosc_w, skutek):
    return {
        "id": id_p,
        "tytul": tytul,
        "opis": opis,
        "warunek": {"typ": typ_w, "wartosc": wartosc_w},
        "skutek": skutek,
        "stan": "oczekujacy"
    }

def zweryfikuj_wpis(punkt):
    wymagane = ["id", "tytul", "opis", "warunek", "skutek", "stan"]
    if not isinstance(punkt, dict):
        return False
    if not all(k in punkt for k in wymagane):
        return False
    if not isinstance(punkt["id"], int) or isinstance(punkt["id"], bool):
        return False
    if not (1 <= punkt["id"] <= 5):
        return False
    if punkt["stan"] not in ["oczekujacy", "wykonany"]:
        return False
    
    war = punkt["warunek"]
    if not isinstance(war, dict) or "typ" not in war or "wartosc" not in war:
        return False
    if war["typ"] not in ["rzut", "tura"]:
        return False
    if not isinstance(war["wartosc"], int) or isinstance(war["wartosc"], bool):
        return False
        
    return True 

def sprawdz_warunek(punkt, stan_gry):
    if not isinstance(punkt, dict) or not isinstance(stan_gry, dict):
        return False
    if punkt.get("stan") != "oczekujacy":
        return False
        
    warunek = punkt.get("warunek")
    if not isinstance(warunek, dict) or "typ" not in warunek or "wartosc" not in warunek:
        return False
        
    typ = warunek["typ"]
    wartosc = warunek["wartosc"]
    if not isinstance(wartosc, int) or isinstance(wartosc, bool):
        return False
    
    if typ == "tura":
        if "tura" not in stan_gry:
            return False
        return stan_gry["tura"] >= wartosc
        
    if typ == "rzut":
        if "ostatni_rzut" not in stan_gry or stan_gry["ostatni_rzut"] is None:
            return False
        wynik = stan_gry["ostatni_rzut"]
        return wynik >= wartosc
        
    return False

def wykonaj_punkt(punkt):
    if punkt.get("stan") == "wykonany":
        return None
    punkt["stan"] = "wykonany"
    return punkt.get("skutek", "")

def pobierz_oczekujace(lista_punktow):
    return [punkt for punkt in lista_punktow if punkt.get("stan") == "oczekujacy"]

def obsluz_ture(stan_gry, lista_punktow):
    stan_gry["tura"] += 1
    skutki = []

    for punkt in pobierz_oczekujace(lista_punktow):
        if sprawdz_warunek(punkt, stan_gry):
            skutek = wykonaj_punkt(punkt)
            if isinstance(skutek, str):
                skutki.append(skutek)

    stan_gry["ostatni_rzut"] = None
    return skutki


# TYMCZASOWE, do podmiany przez resztę grupy
stan_gry = {"tura": 0, "ostatni_rzut": None}
lista_punktow = [
    stworz_zadanie_fabularne(1, "Pierwszy zwrot", "Pojawia się pierwszy trop.", "tura", 2, "Wprowadź pierwszy trop do sceny."),
    stworz_zadanie_fabularne(2, "Niepokojący ślad", "Bohater dostrzega niepokojący ślad.", "rzut", 10, "Opisz niepokojący ślad."),
    stworz_zadanie_fabularne(3, "Nowy sojusznik", "Ważna postać wkracza do historii.", "tura", 4, "Wprowadź ważnego sojusznika."),
    stworz_zadanie_fabularne(4, "Ryzykowny sukces", "Wysoki wynik zmienia bieg sceny.", "rzut", 16, "Opisz znaczący sukces i jego konsekwencję."),
    stworz_zadanie_fabularne(5, "Punkt kulminacyjny", "Historia zbliża się do punktu kulminacyjnego.", "tura", 8, "Zbuduj scenę prowadzącą do punktu kulminacyjnego."),
]
