"""Local EN/PL translations. English is selected at every application start."""
import re
LANGUAGE='en'

# Polish source text | English display text. Longer phrases take precedence.
_PAIRS='''
Wybierz wejście audio radia. Jeśli nie ma USB Audio CODEC, podłącz radio i uruchom program ponownie.|Select the radio audio input. If USB Audio CODEC is missing, connect the radio and restart the application.
DATA i USB|DATA & USB
Kalibracja|Calibration
Otwarta|Open
Zgodnie z SQL|Follow SQL
Znacznik kalibracyjny|Calibration marker
Połącz|Connect
Rozłącz|Disconnect
Panel i waterfall|Panel & waterfall
Baza i pamięci|Library & memories
Ustawienia radia|Radio settings
Radio niepołączone. Waterfall zatrzymany.|Radio disconnected. Waterfall stopped.
Poczekaj na zakończenie operacji pamięci.|Wait for the current operation to finish.
Brak aktualnego połączenia. Zaczekaj na jego odzyskanie.|No current connection. Wait for reconnection.
Łączenie z radiem…|Connecting to the radio…
RADIO ODŁĄCZONE|RADIO DISCONNECTED
CZĘSTOTLIWOŚĆ [MHz]     •     CI-V / USB|FREQUENCY [MHz]     •     CI-V / USB
Ustaw częstotliwość|Set frequency
Wybierz częstotliwość z pamięci…|Recall a memory…
Wybierz częstotliwość z pamięci|Recall a memory
Wybierz częstotliwość…|Recall a memory…
Ustaw emisję / filtr|Set mode / filter
Wejście audio|Audio input
Uruchom waterfall|Start waterfall
Zatrzymaj waterfall|Stop waterfall
Audio zatrzymane|Audio stopped
Zakres audio [Hz]|Audio range [Hz]
Tło [dBFS]|Floor [dBFS]
Wyczyść|Clear
Waterfall AUDIO: częstotliwość dźwięku, nie panorama RF. Nowe dane u góry. Brak obsługi nadawania w wersji 0.1.|AUDIO waterfall: audio frequencies, not an RF panorama. New data at the top. Transmitting is not supported.
Odczytaj 101 pamięci + kopia|Read 101 memories + backup
Eksport CSV|Export CSV
Import CSV do biblioteki|Import CSV into library
Kanał|Channel
Nazwa|Name
Emisja|Mode
Filtr|Filter
Kanał 1–99|Channel 1–99
Nazwa (9 znaków)|Name (9 characters)
Zapisz ten kanał do radia…|Write this channel to the radio…
DATA, CTCSS i osobne ustawienia TX…|DATA, CTCSS & separate TX settings…
Import CSV nie zapisuje niczego w radiu. Zapis pojedynczego kanału wymaga potwierdzenia. P1/P2 tylko do odczytu.|CSV import does not write to the radio. Writing a channel requires confirmation. P1/P2 are read-only.
Ustawienia dodatkowe: osobna emisja/filtr TX, DATA, ton i TSQL dla obu części pamięci oraz SELECT.|Extra settings: separate TX mode/filter, DATA, tone and TSQL for both memory sections, and SELECT.
Pamięć — DATA, CTCSS i ustawienia TX|Memory — DATA, CTCSS & TX settings
Emisja TX|TX mode
Filtr TX|TX filter
Ton RX: 0 OFF / 1 TONE / 2 TSQL|RX tone: 0 OFF / 1 TONE / 2 TSQL
Ton TX: 0 OFF / 1 TONE / 2 TSQL|TX tone: 0 OFF / 1 TONE / 2 TSQL
CTCSS w części RX [Hz]|CTCSS in RX section [Hz]
TSQL w części RX [Hz]|TSQL in RX section [Hz]
CTCSS w części TX [Hz]|CTCSS in TX section [Hz]
TSQL w części TX [Hz]|TSQL in TX section [Hz]
SELECT do skanowania|SELECT for scanning
Dane dodatkowe przygotowane. Dopiero Zapisz ten kanał zmieni pamięć radia.|Extra fields prepared. Use Write this channel to change the radio memory.
Zachowaj w formularzu|Keep in editor
Anuluj|Cancel
Częstotliwość|Frequency
Odczytaj wszystkie ustawienia|Read all settings
Odczytaj konfigurację z radia. Wybierz grupę lub wyszukaj funkcję.|Read the radio configuration. Select a group or search for a function.
Szukaj funkcji, np. CTCSS, DATA, filtr, USB|Search for a function, e.g. CTCSS, DATA, filter, USB
Funkcja radia|Radio function
Odczyt|Readback
Wybierz ustawienie z listy|Select a setting from the list
Zmiany są wysyłane pojedynczo i sprawdzane odczytem.|Changes are sent individually and verified by readback.
Stan radia:|Radio state:
Zastosuj i sprawdź odczyt|Apply and verify
Odczyt jest migawką. Po zmianie emisji lub FIL odśwież konfigurację. Zmiana pola nie zmienia radia.|Readings are a snapshot. Refresh after changing mode or FIL. Editing a field does not change the radio.
niedostępne|unavailable
nie odczytano|not read
Najpierw połącz radio i zaczekaj na zakończenie bieżącej operacji.|Connect the radio and wait for the current operation to finish.
Odczytywanie wszystkich ustawień…|Reading all settings…
Wartość poza zakresem|Value out of range
Potwierdź zmianę|Confirm change
Zastosować wybraną wartość?|Apply the selected value?
Wysyłanie i sprawdzanie:|Sending and verifying:
Ustawienie|Setting
Szukaj nazwy, kanału lub MHz|Search name, channel or MHz
Odczytaj pamięci z radia|Read memories from radio
Przywołuje RX, emisję, filtr i DATA; w FM także CTCSS/TSQL. Nie zmienia częstotliwości TX ani split.|Recalls RX, mode, filter and DATA; also CTCSS/TSQL in FM. TX frequency and split are unchanged.
Przywołaj ustawienia pamięci|Recall memory settings
Zamknij|Close
Trwa odczyt pamięci z radia…|Reading radio memories…
Widoczne pamięci:|Visible memories:
Zaznacz pozycję i kliknij Ustaw lub naciśnij Enter.|Select an entry and click Recall or press Enter.
Brak pasujących pamięci. Odczytaj pamięci z radia, zaimportuj CSV w zakładce Baza i pamięci lub zmień wyszukiwanie.|No matching memories. Read from the radio, import a CSV in Library & memories, or change your search.
Najpierw zaznacz pamięć na liście.|Select a memory from the list first.
Połącz radio i zaczekaj na zakończenie bieżącej operacji.|Connect the radio and wait for the current operation to finish.
Przywoływanie i sprawdzanie ustawień pamięci…|Recalling and verifying memory settings…
— pusta —|— empty —
TAK|YES
NIE|NO
Pamięci|Memories
Dane pamięci|Memory data
Zapis do radia|Write to radio
Nadpisać pamięć|Overwrite memory
Przed zapisem powstanie kopia dotychczasowej pamięci.|The existing memory will be backed up before writing.
Zapisano CSV. Pełne kopie JSON zachowują również tony i pozostałe pola.|CSV saved. Full JSON backups also preserve tones and other fields.
Eksport|Export
Powtórzony kanał lub nieprawidłowe pole split|Duplicate channel or invalid split field
Wczytano|Loaded
pozycji do biblioteki. Nie zmieniono pamięci radia.|entries into the library. Radio memories were not changed.
Import CSV|CSV import
Przechwytywanie audio…|Capturing audio…
BŁĄD USB AUDIO — odłącz/podłącz USB i uruchom program ponownie|USB AUDIO ERROR — reconnect USB and restart the application
Nie udało się uruchomić audio USB|Could not start USB audio
PRZESTEROWANIE|CLIPPING
przerwy:|overflows:
ODCZYT Z RADIA|RADIO READBACK
ODCZYT NIEAKTUALNY|STALE READING
PONAWIANIE|RECONNECTING
ROZŁĄCZONO|DISCONNECTED
Radio odłączone — odczyt nieaktualny|Radio disconnected — reading is stale
Odczyt nieaktualny — brak połączenia|Stale reading — no connection
Odczytano|Read
Ustawienia odczytane. Nie zmieniono radia.|Settings read. The radio was not changed.
Zapis i odczyt OK:|Write and readback OK:
Zmieniono|Changed
Wynik potwierdzony odczytem.|Verified by readback.
Przywołano profil pamięci i potwierdzono odczyt.|Memory profile recalled and verified by readback.
Błąd operacji — sprawdź komunikat i odśwież odczyt.|Operation failed — check the message and refresh the readings.
Błąd:|Error:
BRAK DANYCH AUDIO — sprawdź USB|NO AUDIO DATA — check USB
Operacja w toku|Operation in progress
Zaczekaj na zakończenie operacji pamięci.|Wait for the memory operation to finish.
Podaj częstotliwość 0,030000–60,000000 MHz, z dokładnością do 1 Hz.|Enter a frequency from 0.030000 to 60.000000 MHz, with 1 Hz precision.
Nieprawidłowy kanał, emisja lub filtr|Invalid channel, mode or filter
Nazwa: 1–9 znaków ASCII (litery, cyfry, spacja, / ? . -).|Name: 1–9 ASCII characters (letters, numbers, space, / ? . -).
Częstotliwość poza zakresem radia|Frequency outside the radio range
Nieprawidłowa emisja lub filtr TX|Invalid TX mode or filter
Niepoprawne pole|Invalid field
Niepoprawny ton|Invalid tone
Nieprawidłowa flaga SELECT|Invalid SELECT flag
Połączono:|Connected:
bit/s|bit/s
Rozłączono radio|Radio disconnected
Łączność jest odzyskiwana. Operacja nie została wysłana; ponów ją po połączeniu.|Reconnecting. The operation was not sent; retry after connection is restored.
Emisja lub filtr zmieniły się od odczytu. Odśwież ustawienia przed zapisem.|Mode or filter changed since the last reading. Refresh settings before writing.
Odczyt pamięci|Reading memory
Odczytano 101 pamięci. Kopia:|Read 101 memories. Backup:
Pamięć|Memory
zapis i weryfikacja OK. Kopia:|write and verification OK. Backup:
Najpierw połącz radio|Connect the radio first
Brak bieżącego odczytu — automatycznie odzyskuję połączenie|No current reading — reconnecting automatically
Rejestr wymaga 7 pól oddzielonych średnikiem; zobacz opis.|The register requires 7 semicolon-separated fields; see the description.
Nieprawidłowa częstotliwość rejestru|Invalid band register frequency
Nieprawidłowa emisja, filtr, DATA lub ton|Invalid mode, filter, DATA or tone
Nieobsługiwana częstotliwość CTCSS|Unsupported CTCSS frequency
Nieznany format rejestru pasma|Unknown band register format
Podaj dwie granice MHz oddzielone średnikiem|Enter two band edges in MHz separated by a semicolon
Granice muszą rosnąć i mieścić się w 0–60 MHz, dokładność 1 Hz|Edges must be ascending, within 0–60 MHz, with 1 Hz precision
Nieznany format granic pasma|Unknown band edge format
Niepoprawne dane BCD z radia|Invalid BCD data received from radio
Wartość poza zakresem BCD|Value outside the BCD range
Niepełna odpowiedź pamięci|Incomplete memory response
Nieznany format pamięci:|Unknown memory format:
bajtów|bytes
Radio odrzuciło komendę (NG)|Radio rejected the command (NG)
Brak odpowiedzi CI-V; odczyt będzie ponowiony. Sprawdź radio/USB, jeśli problem trwa.|No CI-V response; the read will be retried. Check the radio/USB if the problem persists.
Niepełne dane częstotliwości/emisji|Incomplete frequency/mode data
Zakres odbioru: 0,03–60 MHz|Receive range: 0.03–60 MHz
Radio nie potwierdziło zadanej częstotliwości|Radio did not confirm the requested frequency
Nieprawidłowy filtr|Invalid filter
Radio nie potwierdziło emisji/filtra|Radio did not confirm the mode/filter
Numer pamięci poza zakresem|Memory number out of range
Niepełny odczyt|Incomplete readback
Niepoprawny odczyt DATA|Invalid DATA readback
Niepoprawny odczyt przesunięcia|Invalid offset readback
Niepełny odczyt przełącznika|Incomplete switch readback
Tekst CW: do 70 znaków ASCII, litery/cyfry oraz spacja / ? , . @ ^ *|CW text: up to 70 ASCII characters, letters/numbers and space / ? , . @ ^ *
Wartość niedostępna dla tego ustawienia/emisji|Value unavailable for this setting/mode
Radio zwróciło|Radio returned
zamiast|instead of
Odśwież ustawienia.|Refresh settings.
Zapis obsługuje pamięci 1–99|Writing supports memories 1–99
Odczyt po zapisie różni się od wysłanych danych; sprawdź pamięć|Readback differs from written data; check the memory
Nieprawidłowy rozmiar FFT|Invalid FFT size
Nie można otworzyć wejścia USB audio. Zamknij inne programy audio, odłącz i podłącz USB, a następnie uruchom program ponownie. Sterowanie CI-V może nadal działać. Szczegóły zapisano w dane/program.log.|Cannot open USB audio input. Close other audio programs, reconnect USB and restart this application. CI-V control may still work. Details are in dane/program.log.
Wyłączone|Off
Włączone|On
Wyłączony|Off
Włączony|On
Wyłączona|Off
Odbiornik|Receiver
Audio i poziomy|Audio & levels
Filtry i CW|Filters & CW
Nadajnik|Transmitter settings
Wyświetlacz radia|Radio display
VFO i strojenie|VFO & tuning
Antena i tuner|Antenna & tuner settings
VOX i BK-IN|VOX & BK-IN
Sygnalizacja|Beeps & indications
Syntezator mowy|Speech synthesizer
Klucz CW|CW keyer
Połączenie CI-V|CI-V connection
Korekcja audio|Audio equalizer
Skanowanie|Scan settings
Wiadomości CW|CW messages
Rejestry pasm|Band registers
Granice pasm użytkownika|User band edges
Przedwzmacniacz|Preamplifier
Wzmocnienie sygnału przed odbiornikiem.|Signal amplification before the receiver.
Tłumik wejściowy|Input attenuator
Tłumienie silnych sygnałów wejściowych.|Attenuates strong input signals.
Automatyka AGC|Automatic gain control (AGC)
FAST — szybka|FAST
MID — średnia|MID
SLOW — wolna|SLOW
Szybkość regulacji wzmocnienia; dostępność zależy od emisji.|Gain control speed; availability depends on mode.
Tłumienie zakłóceń impulsowych.|Suppresses impulse noise.
Redukcja szumów (NR)|Noise reduction (NR)
Cyfrowa redukcja szumów.|Digital noise reduction.
Automatyczny Notch|Auto notch
Tłumienie pojedynczych tonów zakłócających.|Suppresses interfering single tones.
Głośność radia (AF)|Radio volume (AF)
Położenie regulacji 0–255; nie jest to poziom wejścia USB komputera.|Control position 0–255; this is not the computer USB input level.
Wzmocnienie odbiornika (RF)|Receiver gain (RF)
Położenie regulacji RF 0–255.|RF control position 0–255.
Blokada szumów (SQL)|Squelch (SQL)
Położenie regulacji SQL 0–255.|SQL control position 0–255.
Siła redukcji NR|NR strength
Poziom redukcji 0–255; włącz NR w zakładce Odbiornik.|Reduction level 0–255; enable NR in Receiver.
Poziom NB|NB level
Poziom 0–255; włącz NB w zakładce Odbiornik.|Level 0–255; enable NB in Receiver.
Twin PBT — wewnętrzny|Twin PBT — inner
Twin PBT — zewnętrzny|Twin PBT — outer
Położenie 0–255; środek 128.|Position 0–255; centre 128.
Ton CW (CW PITCH)|CW pitch
Skala 0–255: 0 ≈ 300 Hz, 128 ≈ 600 Hz, 255 ≈ 900 Hz.|Scale 0–255: 0 ≈ 300 Hz, 128 ≈ 600 Hz, 255 ≈ 900 Hz.
Prędkość klucza CW|CW keyer speed
Położenie regulacji 0–255, nie bezpośrednia wartość WPM.|Control position 0–255, not a direct WPM value.
Położenie filtra Notch|Notch filter position
Położenie 0–255; środek 128. Aktywność zależy od ustawienia radia.|Position 0–255; centre 128. Availability depends on radio settings.
Regulacja mocy RF|RF power control
Położenie 0–255, nie waty. Zmiana nie uruchamia nadawania.|Position 0–255, not watts. Changing it does not key the transmitter.
Wzmocnienie mikrofonu|Microphone gain
Położenie MIC 0–255.|MIC position 0–255.
Poziom kompresora|Compressor level
Położenie COMP 0–255; aktywność kompresora zależy od ustawienia radia.|COMP position 0–255; compressor activity depends on radio settings.
Głośność monitora|Monitor volume
Położenie MONI GAIN 0–255.|MONI GAIN position 0–255.
Kontrast LCD|LCD contrast
Zmienia wyświetlacz fizycznego radia, nie okno programu.|Changes the physical radio display, not this application window.
Podświetlenie LCD|LCD backlight
Zmienia podświetlenie fizycznego radia.|Changes the physical radio backlight.
Krok strojenia|Tuning step
Antena|Antenna
Ton nadawczy|Transmit tone
Blokada tonowa TSQL|Tone squelch TSQL
Kompresor mowy|Speech compressor
Monitor nadawania|Transmit monitor
Blokada pokrętła|Dial lock
Pierwszy filtr IF|First IF filter
6 kHz — opcja FL-430|6 kHz — optional FL-430
3 kHz — opcja FL-431|3 kHz — optional FL-431
Kształt filtra DSP|DSP filter shape
Szerokość Manual Notch|Manual notch width
Pasmo nadawania SSB|SSB transmit bandwidth
Tuner antenowy|Antenna tuner
Ominięty|Bypassed
Podsłuch częstotliwości TX (XFC)|Transmit frequency check (XFC)
Włączenie może umożliwić automatyczne nadawanie pod wpływem dźwięku lub klucza.|Enabling this may allow automatic transmission triggered by audio or a key.
Opóźnienie BK-IN|BK-IN delay
Wzmocnienie VOX|VOX gain
Szerokość bieżącego filtra IF|Current IF filter bandwidth
Dotyczy aktualnej emisji i FIL1/2/3. Zmiana może wyzerować przesunięcie Twin PBT. FM ma stałe szerokości.|Applies to the current mode and FIL1/2/3. May reset Twin PBT shift. FM bandwidths are fixed.
Stała czasowa AGC|AGC time constant
Tryb DATA / filtr|DATA mode / filter
Dostępny w SSB, AM i FM. Wybiera filtr DATA niezależnie od normalnej emisji.|Available in SSB, AM and FM. Selects the DATA filter independently of normal mode.
Częstotliwość tonu nadawczego|Transmit tone frequency
Częstotliwość blokady TSQL|TSQL tone frequency
Ton CTCSS. Funkcja używana w FM.|CTCSS tone. Used in FM.
Jasność LCD (SET)|LCD brightness (SET)
Poziom sygnałów dźwiękowych|Beep level
Ogranicznik poziomu beep|Beep level limit
Dźwięk potwierdzenia|Confirmation beep
Sygnalizacja granic pasm|Band edge beep
Pasma fabryczne|Factory bands
Pasma użytkownika i limit TX|User bands and TX limit
Pasma użytkownika|User bands
Częstotliwość beep|Beep frequency
Funkcja pokrętła RF/SQL|RF/SQL knob function
Zatrzymanie szczytu miernika|Meter peak hold
Limit czasu nadawania CI-V|CI-V transmit timeout
Przesunięcie FM Split — KF|FM split offset — HF
Przesunięcie FM Split — 50 MHz|FM split offset — 50 MHz
Podaj przesunięcie w kHz, od -9999 do +9999.|Enter an offset in kHz from -9999 to +9999.
Blokada Split|Split lock
Automatyczny start tunera|Automatic tuner start
Może uruchamiać strojenie podczas nadawania.|May start antenna tuning during transmission.
Strojenie po PTT|Tune after PTT
Może uruchamiać strojenie po naciśnięciu PTT.|May start antenna tuning when PTT is pressed.
Wybór anteny|Antenna selection
Ręczny|Manual
Automatyczny|Automatic
Głośność syntezatora|Speech volume
Język|Language
Angielski|English
Japoński|Japanese
Szybkość|Speed
Wolna|Slow
Szybka|Fast
Odczyt S-metra|Announce S-meter
Odczyt emisji po zmianie|Announce mode after change
Liczba pamięci Memo Pad|Memo Pad count
Automatyczny krok pokrętła|Automatic dial step
Szybkość UP/DOWN mikrofonu|Microphone UP/DOWN speed
Szybkie zerowanie RIT/ΔTX|Quick RIT/ΔTX clear
Rodzaj Notch —|Notch type —
Popup szerokości Notch|Notch width popup
Popup PBT|PBT popup
Popup FIL|FIL popup
Synchroniczne strojenie SSB/CW|SSB/CW synchronous tuning
Normalna wstęga CW|CW normal sideband
Pierwsze menu klucza|Initial keyer menu
Klawiatura zewnętrzna|External keypad
Blokada szumów dla audio USB|USB audio squelch
Poziom modulacji USB|USB modulation level
Źródło modulacji — DATA OFF|Modulation source — DATA OFF
Źródło modulacji — DATA ON|Modulation source — DATA ON
Funkcja portu USB|USB port function
Wybór RTTY przerywa sterowanie przez USB. Aby wrócić, ustaw CI-V na panelu radia.|Selecting RTTY interrupts USB control. Restore CI-V on the radio panel to reconnect.
Prędkość dekodera RTTY|RTTY decoder baud rate
Marker kalibracyjny|Calibration marker
Funkcja kalibracyjna; może wpłynąć na odbiór.|Calibration function; may affect reception.
Częstotliwość odniesienia|Reference frequency
Zmienia kalibrację częstotliwości radia. Zanotuj wartość początkową.|Changes radio frequency calibration. Record the initial value.
Ustawienie filtrów audio zeruje korekcję basów i sopranów tej emisji.|Setting audio filters resets bass and treble for this mode.
Basy|Bass
Soprany|Treble
Korekcja RX może wyłączyć HPF/LPF tej emisji.|RX equalization may disable HPF/LPF for this mode.
Pasmo SSB TX —|SSB TX bandwidth —
Format numeru zawodów|Contest number format
Normalny|Normal
Pamięć zwiększająca numer|Count-up trigger memory
Aktualny numer zawodów|Current contest number
Głośność podsłuchu CW|CW sidetone volume
Ogranicznik podsłuchu CW|CW sidetone limit
Czas powtarzania|Repeat interval
Opis wiadomości|Message display
Numer|Number
Pierwsze znaki|First characters
Stosunek kreski do kropki|Dash/dot ratio
Czas narastania CW|CW rise time
Polaryzacja łopatek|Paddle polarity
Normalna|Normal
Odwrócona|Reversed
Rodzaj klucza|Key type
Sztorcowy|Straight
Elektroniczny|Electronic
Kluczowanie UP/DOWN mikrofonu|Microphone UP/DOWN keying
Częstotliwość MARK|MARK frequency
Przesunięcie RTTY|RTTY shift
Polaryzacja kluczowania|Keying polarity
Kod nowej linii|Newline code
Wiersze dekodera|Decoder rows
Szybkość skanowania|Scan speed
Wznawianie skanowania|Scan resume
Głębokość NB|NB depth
Szerokość NB|NB width
Opóźnienie VOX|VOX delay
Pamięć klucza M|Keyer memory M
Maksymalnie 70 znaków. Zapisuje tekst, nie uruchamia nadawania.|Maximum 70 characters. Stores text without starting transmission.
rejestr|register
Format: MHz;emisja;FIL;DATA 0/1;ton 0/OFF 1/TONE 2/TSQL;CTCSS TX Hz;CTCSS SQL Hz. Zapis nie stroi aktywnego VFO.|Format: MHz;mode;FIL;DATA 0/1;tone 0/OFF 1/TONE 2/TSQL;CTCSS TX Hz;CTCSS SQL Hz. Writing does not tune the active VFO.
Zakres|Range
Format: dolna granica MHz;górna granica MHz. Puste pole odczytu oznacza niezdefiniowany zakres.|Format: lower edge MHz;upper edge MHz. An empty reading indicates an undefined range.
Zmienia granice pasm użytkownika używane przez sygnalizację i opcjonalny limit TX. Nie zmienia sprzętowego zakresu radia.|Changes user band edges used by beeps and the optional TX limit. Does not change the hardware frequency range.
Podaj adres https://github.com/właściciel/repozytorium|Enter https://github.com/owner/repository
Repozytorium lub opublikowane wydanie nie jest jeszcze dostępne.|The repository or a published release is not available yet.
Nie można porównać wersji:|Cannot compare version:
Dostępna nowa wersja:|New version available:
Masz aktualną lub nowszą wersję:|You have the latest or a newer version:
Wersja:|Version:
Aplikacja nie zbiera żadnych informacji o użytkowniku.|The application does not collect any information about the user.
Aplikacja jest w pełni darmowa.|The application is completely free of charge.
Aplikacja nie wymaga rejestracji.|The application does not require registration.
Lokalne kopie pamięci i dzienniki pozostają na komputerze. Sprawdzanie aktualizacji kontaktuje się z GitHubem tylko po kliknięciu; otwierane linki prowadzą do zewnętrznych serwisów.|Local memory backups and logs stay on your computer. Update checks contact GitHub only when clicked; links open external services.
Repozytorium GitHub|GitHub repository
Aktualizacje są sprawdzane wyłącznie na żądanie.|Updates are checked only on request.
Sprawdzanie aktualizacji…|Checking for updates…
Nie udało się sprawdzić aktualizacji:|Could not check for updates:
Sprawdź aktualizacje|Check for updates
Otwórz stronę wydania|Open release page
Invalid memory profile|Invalid memory profile
'''
PL_EN=dict(line.split('|',1) for line in _PAIRS.strip().splitlines())
_pattern=re.compile('|'.join(('(?<!\\w)' if key[0].isalnum() else '')+re.escape(key)+('(?!\\w)' if key[-1].isalnum() else '')
                            for key in sorted(PL_EN,key=len,reverse=True)))

EN_PL={
    'Invalid memory profile':'Nieprawidłowy profil pamięci',
    'Memory lacks DATA/CTCSS fields. Read memories from the radio again.':'Brak pól DATA/CTCSS w pamięci. Odczytaj pamięci ponownie z radia.',
    'Invalid DATA/CTCSS memory fields':'Nieprawidłowe pola DATA/CTCSS pamięci',
    'DATA is not available in this mode':'DATA nie jest dostępne w tej emisji',
    'CTCSS readback mismatch':'Niezgodność odczytu CTCSS',
    'Profile readback mismatch':'Niezgodność odczytu profilu',
    'Memory recall incomplete; some parameters may have changed. Refresh the radio state. ':'Przywołanie pamięci nieukończone; część parametrów mogła się zmienić. Odśwież odczyt radia. ',
}

def tr(text):
    if not isinstance(text,str):
        return text
    if LANGUAGE=='pl':
        for english,polish in EN_PL.items():
            text=text.replace(english,polish)
        return text
    return _pattern.sub(lambda m:PL_EN[m.group()],text)

def set_language(language):
    global LANGUAGE
    if language not in ('en','pl'):
        raise ValueError('Unsupported language')
    LANGUAGE=language
