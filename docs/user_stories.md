1. Jako użytkownik chcę mieć możliwość tworzenia postaci, aby przeprowadzić z nimi grę
2. Jako użytkownik chcę mieć możliwość podejmowania decyzji podczas gry, aby mieć wpływ na jej fabułę
3. Jako użytkownik chcę mieć możliwość zapisu stanu rozgrywki, aby nie utracić postępu
4. Jako użytkownik chcę mieć możliwość wczytania ostatniego stanu rozgrywki, aby kontynuować nieukończoną rozgrywkę 
5. Jako użytkownik chcę wybrać liczby graczy na starcie, aby prowadzić rozgrywkę z kilkoma grywalnymi postaciami
6. Jako użytkownik chcę mieć możliwość opcjonalnego opisu setingu, aby odpowiadał moim preferencjom
7. Jako użytkownik chcę mieć możliwość przytrzymywania przycisku rzutu kością, aby mieć iluzję dokonania wyboru
8. Jako użytkownik chcę, aby fabuła zawierała punkty zwrotne zależne od moich decyzji, aby gra nie była tylko luźną rozmową.

1. Jako gracz chcę wybrać liczbę graczy na ekranie startowym, aby prowadzić grę kilkoma postaciami.
2. Jako gracz chcę opcjonalnie opisać setting, aby gra toczyła się w świecie, który wybrałem.
3. Jako gracz chcę opisać postać kilkoma zdaniami i dostać wygenerowaną postać z imieniem, rolą i osobowością, aby szybko mieć bohatera bez wypełniania karty ręcznie.
4. Jako gracz chcę widzieć listę swoich postaci w oknie rozgrywki, aby wiedzieć, kim gram.
5. Jako gracz chcę rozmawiać z Mistrzem Gry w oknie czatu i opisywać swoje decyzje, aby fabuła reagowała na moje działania.
6. Jako gracz chcę rzucić kością przyciskiem i zobaczyć wynik w czacie, aby losowy wynik współdecydował o skutku moich działań.
7. Jako gracz chcę, aby model wygenerował zarys fabuły z punktami zwrotnymi, aby historia miała strukturę.
8. Jako gracz chcę, aby po spełnieniu warunku punktu zwrotnego fabuła się zmieniła, a punkt został oznaczony jako wykonany, aby moje decyzje realnie zmieniały historię.
9. Jako gracz chcę zapisać stan gry (postacie, historię rozmowy, setting) do pliku, aby wrócić do niej później.
10. Jako gracz chcę wczytać zapis z pliku, aby kontynuować grę od miejsca, w którym skończyłem.
11. Jako gracz chcę zobaczyć komunikat, gdy model nie odpowiada lub plik zapisu jest uszkodzony, aby wiedzieć, co poszło nie tak.

4 najważniejsze
Historyjka 3: bez postaci nie ma gry.
Historyjka 5: to główna interakcja z modelem.
Historyjka 8: to cecha, która odróżnia aplikację od zwykłego czatu.
Historyjka 10: bez wczytania zapis nie ma sensu.
Kryteria akceptacji
Historyjka 3:
Po wpisaniu opisu i kliknięciu Generuj pojawiają się niepuste pola: imię, rola, osobowość.
Pusty opis nie wysyła zapytania i pokazuje komunikat.
Po zatwierdzeniu postać pojawia się na liście postaci w rozgrywce.
Historyjka 5:
Wiadomość gracza pojawia się w oknie czatu po kliknięciu Wyślij.
Mistrz Gry odpowiada w czacie, uwzględniając setting, postacie i wcześniejsze wiadomości.
Po wysłaniu pole tekstowe się czyści, a Wyślij jest nieaktywne do czasu odpowiedzi.
Historyjka 8:
Każdy punkt zwrotny ma warunek, skutek i stan, na początku “niewykonany”.
Gdy program uzna warunek za spełniony, stan zmienia się na “wykonany”.
Po zmianie stanu kolejne odpowiedzi Mistrza Gry uwzględniają skutek tego punktu.
Historyjka 10:
Po wybraniu poprawnego pliku wracają historia czatu, lista postaci i setting.
Po wczytaniu gracz może wysłać wiadomość i Mistrz Gry odpowiada w kontekście zapisu.
Uszkodzony plik pokazuje komunikat i nie zmienia aktualnego stanu gry.
