# Piksel RPG

Kooperacyjne RPG z Mistrzem Gry AI (Llama). Jedna osoba hostuje i uruchamia Llamę lokalnie, reszta dołącza kodem zaproszenia.
**Bez serwera, bez kont, bez opłat** — cały stos jest darmowy i działa na Waszych komputerach.

- **Mistrz Gry = Llama** (przez darmową Ollamę) — rysuje **mapę pikselową 256×256** narzędziami (prostokąty, linie, koła, wypełnienia, generator terenu/lochów) i stawia **znaczniki** (miasta, lochy, zagrożenia, skarby…).
- **P2P**: gracze łączą się bezpośrednio z hostem kodem zaproszenia (TCP).
- **Kto był kim** zapisuje się w Kronice; **zapisy gry są na komputerze każdego uczestnika** (każdy ma pełną kopię).
- **Wszyscy muszą dołączyć**, żeby ruszyć nową kampanię — **chyba że ich postać zginęła** (wznowienie czeka tylko na żywych).
- Tryb demo (skryptowy MG) działa bez Ollamy.

## Uruchomienie
```
pip install -r requirements.txt        # PySide6 (Qt, LGPL)
python main.py
```
Instalator z kreatorem: `python installer/install.py` (albo `PikselRPG-Setup.exe`, patrz niżej). Tryb cichy: `--silent --dir KATALOG [--ollama] [--model llama3.2:3b]`.

## Jak się gra
1. **Host**: *Hostuj nową grę* → nick, nazwa, opis świata, liczba graczy → lobby pokazuje kody zaproszenia (**Cały świat**, **LAN/VPN** i **Internet**).
2. **Gracze**: *Dołącz do gry* → nick + kod. Każdy tworzy postać (8 klas) i klika *Jestem gotowy*.
3. Host klika *Rozpocznij grę*, gdy są wszyscy i wszyscy gotowi. Llama buduje świat (mapa + znaczniki) i pisze wstęp.
4. Każda runda: wszyscy żywi gracze zgłaszają jedną akcję → MG rzuca kośćmi (silnik, nie model), rozstrzyga skutki, zmienia mapę/PŻ/ekwipunek i opisuje, co się stało. Zmarli obserwują i piszą na czacie.
5. **Wznowienie**: *Wznów zapisaną kampanię* — host może być dowolny uczestnik (jego zapis). Nie czekamy na poległych; obcy nie wejdą do zamkniętej kampanii.

## Sieć (bez płatnych usług)
- Ta sama sieć lub darmowy VPN (Tailscale, ZeroTier, Radmin) → kod **LAN/VPN**.
- **Cały świat (domyślnie, zero konfiguracji)** → host łączy się wychodząco z darmowym publicznym tunelem TCP (protokół *bore*, domyślnie `bore.pub`; klient jest wbudowany w grę, nic się nie instaluje). Kod „Cały świat” działa z każdego kraju, za każdym routerem/NAT-em, a gość tylko go wpisuje. Serwer tylko przekazuje bajty (ruch nie jest szyfrowany, chroni go losowy token w kodzie). Własny serwer: klucz `tunnel_server` w `profile.json`; wyłączenie: `"use_tunnel": false`. Gdy tunel jest niedostępny, zostają poniższe metody.
- Przez internet → host próbuje otworzyć port automatycznie (UPnP); jeśli router nie pozwala, przekieruj port TCP **47600** ręcznie. Adres publiczny sprawdza darmowe `api.ipify.org` (opcjonalnie; bez tego zostaje kod LAN).
- Ruch **nie jest szyfrowany**; ochroną jest losowy token w kodzie zaproszenia. Graj ze znajomymi, nie publikuj kodu.

## Llama
Zainstaluj [Ollamę](https://ollama.com) (tylko host) i pobierz model w *Ustawieniach* (domyślnie `llama3.2:3b`, ok. 2 GB; `llama3.1:8b` pisze lepiej, wymaga ~16 GB RAM). Działa też model bez natywnych narzędzi (JSON w treści jest parsowany).

## Windows: samodzielny instalator
Na Windowsie: `py -m pip install pyinstaller PySide6-Essentials` → `py tools\build_windows.py` → `dist\PikselRPG-Setup.exe`.
Instalator działa bez praw administratora: kopiuje pliki, tworzy skróty, wpis w „Aplikacje i funkcje”, opcjonalnie instaluje Ollamę, pobiera model i dodaje regułę zapory (UAC).

## Testy i zrzuty
```
python tests/test_core.py                                  # mapa, narzędzia, reguły startu, pętla LLM, P2P, zapisy, wznowienie
QT_QPA_PLATFORM=offscreen python tools/make_screenshots.py screenshots   # pełna gra 3 graczy przez prawdziwe okna
```

## Licencje zasobów
Ikony: [Phosphor Icons](https://phosphoricons.com) (MIT). Czcionki: Pixelify Sans, Inter (SIL OFL). Logo: własne (`tools/make_logo.py`). Qt/PySide6: LGPL. Ollama: MIT; modele Llama wg licencji Meta.


## Budowa instalatora na Windows (pliki .bat)
Uruchamiaj po kolei (albo tylko `zrob_wszystko.bat`):
`1_przygotuj.bat` (zależności) → `2_zasoby.bat` (logo/ikony) → `3_testy.bat` → `4_buduj_instalator.bat` (→ `dist\PikselRPG-Setup.exe`) → `5_uruchom_instalator.bat`.
Do szybkich prób: `uruchom_gre.bat`, `uruchom_instalator_ze_zrodel.bat`. Wymagany Python 3.10+ z PATH.


## Nowości (wersja z rolami od AI, minigrą i angielskim)
- **Role od AI zamiast klas.** Gracz podaje imię i opcjonalnie własny pomysł; przy starcie Mistrz Gry (AI) nadaje każdej postaci rolę, historię, PŻ i ekwipunek na podstawie opisu świata (narzędzie `assign_role`).
- **Losowy świat.** W formularzu hosta przycisk „Losowy świat” losuje nazwę i opis; puste pole „Świat” = AI wymyśla własny (`set_world`).
- **Mistrz Gry jak przy stole.** Nowy, konkretny prompt: proza bez ASCII-artu/tabel/markdownu (filtr `narration.py` wycina to, gdyby model jednak spróbował), rzuty przez silnik z trudnością, konsekwencje, NPC-e, a wstęp przedstawia każdą postać: kim jest, kto nią gra i co robi.
- **Stała mapa.** Teren generuje się dokładnie raz; potem mapę wolno tylko edytować (rysowanie, znaczniki, pionki). Próba ponownego `map_generate_*`/`map_clear` jest odrzucana, a widok i skala nie zmieniają się.
- **Minigra ładowania.** Podczas tworzenia świata i wznawiania gry wszyscy gracze chodzą pikselowymi postaciami po wspólnej sali (strzałki/WASD) i zbierają gwiazdki; stan liczy host (`arena.py`), klienci tylko wysyłają kierunek.
- **Narrator głosowy (TTS)** na systemowych syntezatorach (Windows/macOS/Linux, bez instalacji pakietów); wyciszenie jest lokalne (przycisk głośnika w grze, zapamiętywane w profilu).
- **Wyjście z gry z potwierdzeniem.** W trakcie gry „Wyjdź” pyta o potwierdzenie, a reszta drużyny głosuje (25 s): jeśli zgodzą się wszyscy, sesja zapisuje się u każdego i nikt nie ginie; jeśli ktoś odmówi, wychodzący sam wybiera: **zostaje w grze** albo **wychodzi, a jego postać ginie** (wpis w kronice) — o losie postaci nie decyduje nikt poza nim. W lobby i po końcu gry wyjście jest bez głosowania.
- **Angielski** w grze i instalatorze (wybór języka na pierwszej stronie instalatora i w Ustawieniach; domyślnie język systemu). `tests/test_i18n.py` pilnuje kompletności tłumaczeń.
- Pliki `.bat` do budowy (patrz wyżej) oraz kod „Cały świat” (tunel bore) do gry przez internet bez konfiguracji.
