"""Verified IC-7410 commands, instruction manual p.102. No PTT/VOX commands."""
SWITCH = {0:'Wyłączone',1:'Włączone'}
# key, group, Polish label, command prefix, choices (None means BCD 0000–0255), help
SETTINGS = [
 ('preamp','Odbiornik','Przedwzmacniacz','1602',{0:'Wyłączony',1:'P.AMP 1',2:'P.AMP 2'},'Wzmocnienie sygnału przed odbiornikiem.'),
 ('attenuator','Odbiornik','Tłumik wejściowy','11',{0:'Wyłączony',32:'20 dB'},'Tłumienie silnych sygnałów wejściowych.'),
 ('agc','Odbiornik','Automatyka AGC','1612',{1:'FAST — szybka',2:'MID — średnia',3:'SLOW — wolna'},'Szybkość regulacji wzmocnienia; dostępność zależy od emisji.'),
 ('nb','Odbiornik','Noise Blanker (NB)','1622',SWITCH,'Tłumienie zakłóceń impulsowych.'),
 ('nr','Odbiornik','Redukcja szumów (NR)','1640',SWITCH,'Cyfrowa redukcja szumów.'),
 ('auto_notch','Odbiornik','Automatyczny Notch','1641',SWITCH,'Tłumienie pojedynczych tonów zakłócających.'),
 ('af','Audio i poziomy','Głośność radia (AF)','1401',None,'Położenie regulacji 0–255; nie jest to poziom wejścia USB komputera.'),
 ('rf','Audio i poziomy','Wzmocnienie odbiornika (RF)','1402',None,'Położenie regulacji RF 0–255.'),
 ('sql','Audio i poziomy','Blokada szumów (SQL)','1403',None,'Położenie regulacji SQL 0–255.'),
 ('nr_level','Audio i poziomy','Siła redukcji NR','1406',None,'Poziom redukcji 0–255; włącz NR w zakładce Odbiornik.'),
 ('nb_level','Audio i poziomy','Poziom NB','1412',None,'Poziom 0–255; włącz NB w zakładce Odbiornik.'),
 ('pbt_inner','Filtry i CW','Twin PBT — wewnętrzny','1407',None,'Położenie 0–255; środek 128.'),
 ('pbt_outer','Filtry i CW','Twin PBT — zewnętrzny','1408',None,'Położenie 0–255; środek 128.'),
 ('cw_pitch','Filtry i CW','Ton CW (CW PITCH)','1409',None,'Skala 0–255: 0 ≈ 300 Hz, 128 ≈ 600 Hz, 255 ≈ 900 Hz.'),
 ('key_speed','Filtry i CW','Prędkość klucza CW','140c',None,'Położenie regulacji 0–255, nie bezpośrednia wartość WPM.'),
 ('notch_level','Filtry i CW','Położenie filtra Notch','140d',None,'Położenie 0–255; środek 128. Aktywność zależy od ustawienia radia.'),
 ('power','Nadajnik','Regulacja mocy RF','140a',None,'Położenie 0–255, nie waty. Zmiana nie uruchamia nadawania.'),
 ('mic','Nadajnik','Wzmocnienie mikrofonu','140b',None,'Położenie MIC 0–255.'),
 ('comp','Nadajnik','Poziom kompresora','140e',None,'Położenie COMP 0–255; aktywność kompresora zależy od ustawienia radia.'),
 ('monitor','Nadajnik','Głośność monitora','1415',None,'Położenie MONI GAIN 0–255.'),
 ('contrast','Wyświetlacz radia','Kontrast LCD','1418',None,'Zmienia wyświetlacz fizycznego radia, nie okno programu.'),
 ('brightness','Wyświetlacz radia','Podświetlenie LCD','1419',None,'Zmienia podświetlenie fizycznego radia.'),
]
META = {}
def add(key,group,label,command,choices=None,hint='',codec=None,limits=(0,255),warning=''):
    SETTINGS.append((key,group,label,command,choices,hint or label))
    META[key]={'codec':codec or ('bcd2' if choices is None else 'byte'),'limits':limits,'warning':warning}
def setting(number,group,label,choices=None,hint='',codec=None,limits=(0,255),warning=''):
    add(f'set_{number:04}',group,label,'1a05'+f'{number:04}',choices,hint,codec,limits,warning)
def options(*labels):
    return dict(enumerate(labels))

for key,group,label,command,choices in [
 ('split','VFO i strojenie','Split','0f',SWITCH),
 ('step','VFO i strojenie','Krok strojenia','10',options('10 Hz / 1 Hz','100 Hz','1 kHz','5 kHz','9 kHz','10 kHz','12,5 kHz','20 kHz','25 kHz')),
 ('antenna','Antena i tuner','Antena','12',options('ANT 1','ANT 2')),
 ('tone_on','CTCSS','Ton nadawczy','1642',SWITCH),('tsql_on','CTCSS','Blokada tonowa TSQL','1643',SWITCH),
 ('comp_on','Nadajnik','Kompresor mowy','1644',SWITCH),('monitor_on','Nadajnik','Monitor nadawania','1645',SWITCH),
 ('vox_on','VOX i BK-IN','VOX','1646',SWITCH),('break_in','VOX i BK-IN','BK-IN','1647',options('Wyłączony','Semi','Full')),
 ('manual_notch','Filtry i CW','Manual Notch','1648',SWITCH),('vsc','Odbiornik','Voice Squelch Control','164c',SWITCH),
 ('twin_peak','RTTY','Twin Peak Filter','164f',SWITCH),('dial_lock','VFO i strojenie','Blokada pokrętła','1650',SWITCH),
 ('roofing','Filtry i CW','Pierwszy filtr IF','1655',options('15 kHz','6 kHz — opcja FL-430','3 kHz — opcja FL-431')),
 ('shape','Filtry i CW','Kształt filtra DSP','1656',options('SHARP','SOFT')),
 ('notch_width','Filtry i CW','Szerokość Manual Notch','1657',options('WIDE','MID','NAR')),
 ('tbw','Nadajnik','Pasmo nadawania SSB','1658',options('WIDE','MID','NAR')),
 ('tuner','Antena i tuner','Tuner antenowy','1c01',options('Ominięty','Włączony')),
 ('xfc','VFO i strojenie','Podsłuch częstotliwości TX (XFC)','1c02',SWITCH),
]:
    warning='Włączenie może umożliwić automatyczne nadawanie pod wpływem dźwięku lub klucza.' if key in ('vox_on','break_in') else ''
    add(key,group,label,command,choices,warning=warning)
add('break_delay','VOX i BK-IN','Opóźnienie BK-IN','140f')
add('vox_gain','VOX i BK-IN','Wzmocnienie VOX','1416')
add('anti_vox','VOX i BK-IN','ANTI-VOX','1417')
add('bandwidth','Filtry i CW','Szerokość bieżącego filtra IF','1a03',{i:str(i) for i in range(50)},
    'Dotyczy aktualnej emisji i FIL1/2/3. Zmiana może wyzerować przesunięcie Twin PBT. FM ma stałe szerokości.',codec='bcd1')
add('agc_time','Odbiornik','Stała czasowa AGC','1a04',{i:str(i) for i in range(14)},codec='bcd1')
add('data','DATA i USB','Tryb DATA / filtr','1a06',{0:'DATA OFF',257:'DATA ON / FIL1',258:'DATA ON / FIL2',259:'DATA ON / FIL3'},
    'Dostępny w SSB, AM i FM. Wybiera filtr DATA niezależnie od normalnej emisji.',codec='data')
TONES=[670,693,719,744,770,797,825,854,885,915,948,974,1000,1035,1072,1109,1148,1188,1230,1273,1318,1365,1413,1462,1514,1567,1598,1622,1655,1679,1713,1738,1773,1799,1835,1862,1899,1928,1966,1995,2035,2065,2107,2181,2257,2291,2336,2418,2503,2541]
for key,cmd,label in [('tone','1b00','Częstotliwość tonu nadawczego'),('tsql','1b01','Częstotliwość blokady TSQL')]:
    add(key,'CTCSS',label,cmd,{v:f'{v/10:.1f} Hz' for v in TONES},'Ton CTCSS. Funkcja używana w FM.',codec='bcd3')

setting(1,'Wyświetlacz radia','Kontrast LCD (SET)')
setting(2,'Wyświetlacz radia','Jasność LCD (SET)')
setting(3,'Sygnalizacja','Poziom sygnałów dźwiękowych')
setting(4,'Sygnalizacja','Ogranicznik poziomu beep',SWITCH)
setting(5,'Sygnalizacja','Dźwięk potwierdzenia',SWITCH)
setting(6,'Sygnalizacja','Sygnalizacja granic pasm',options('Wyłączona','Pasma fabryczne','Pasma użytkownika','Pasma użytkownika i limit TX'))
setting(7,'Sygnalizacja','Częstotliwość beep',{v:f'{v*10} Hz' for v in range(50,201)},codec='bcd2')
setting(8,'Odbiornik','Funkcja pokrętła RF/SQL',options('AUTO','SQL','RF + SQL'))
setting(9,'Odbiornik','Zatrzymanie szczytu miernika',SWITCH)
setting(10,'Nadajnik','Limit czasu nadawania CI-V',options('Wyłączony','3 min','5 min','10 min','20 min','30 min'))
setting(11,'VFO i strojenie','Quick Split',SWITCH)
for number,label in [(12,'Przesunięcie FM Split — KF'),(13,'Przesunięcie FM Split — 50 MHz')]:
    setting(number,'CTCSS',label,None,'Podaj przesunięcie w kHz, od -9999 do +9999.',codec='offset',limits=(-9999,9999))
setting(14,'VFO i strojenie','Blokada Split',SWITCH)
setting(15,'Antena i tuner','Automatyczny start tunera',SWITCH,warning='Może uruchamiać strojenie podczas nadawania.')
setting(16,'Antena i tuner','Strojenie po PTT',SWITCH,warning='Może uruchamiać strojenie po naciśnięciu PTT.')
setting(17,'Antena i tuner','Wybór anteny',options('Wyłączony','Ręczny','Automatyczny'))
setting(18,'Syntezator mowy','Głośność syntezatora')
setting(19,'Syntezator mowy','Język',options('Angielski','Japoński'))
setting(20,'Syntezator mowy','Szybkość',options('Wolna','Szybka'))
setting(21,'Syntezator mowy','Odczyt S-metra',SWITCH)
setting(22,'Syntezator mowy','Odczyt emisji po zmianie',SWITCH)
setting(23,'VFO i strojenie','Liczba pamięci Memo Pad',options('5','10'))
setting(24,'VFO i strojenie','Automatyczny krok pokrętła',options('Wyłączony','LOW','HIGH'))
setting(25,'VFO i strojenie','Szybkość UP/DOWN mikrofonu',options('LOW','HIGH'))
setting(26,'VFO i strojenie','Szybkie zerowanie RIT/ΔTX',SWITCH)
for n,mode in [(27,'SSB'),(28,'AM')]:
    setting(n,'Filtry i CW','Rodzaj Notch — '+mode,options('Auto','Manual','Auto / Manual'))
for n,label in [(29,'Popup szerokości Notch'),(30,'Popup PBT'),(31,'Popup FIL')]:
    setting(n,'Wyświetlacz radia',label,SWITCH)
setting(32,'Filtry i CW','Synchroniczne strojenie SSB/CW',SWITCH)
setting(33,'Klucz CW','Normalna wstęga CW',options('LSB','USB'))
setting(34,'Klucz CW','Pierwsze menu klucza',options('KEYER ROOT','KEYER SEND'))
setting(35,'Klucz CW','Klawiatura zewnętrzna',options('Wyłączona','KEYER SEND'))
setting(36,'DATA i USB','Blokada szumów dla audio USB',options('Otwarta','Zgodnie z SQL'))
setting(37,'DATA i USB','Poziom modulacji USB')
for n,label in [(38,'Źródło modulacji — DATA OFF'),(39,'Źródło modulacji — DATA ON')]:
    setting(n,'DATA i USB',label,options('MIC','ACC','MIC + ACC','USB'))
setting(40,'Połączenie CI-V','CI-V Transceive',SWITCH)
setting(41,'Połączenie CI-V','Funkcja portu USB',options('CI-V','RTTY'),warning='Wybór RTTY przerywa sterowanie przez USB. Aby wrócić, ustaw CI-V na panelu radia.')
setting(42,'RTTY','Prędkość dekodera RTTY',options('300 bit/s','1200 bit/s','4800 bit/s','9600 bit/s','19200 bit/s'))
setting(43,'Kalibracja','Znacznik kalibracyjny',SWITCH,warning='Funkcja kalibracyjna; może wpłynąć na odbiór.')
setting(44,'Kalibracja','Częstotliwość odniesienia',warning='Zmienia kalibrację częstotliwości radia. Zanotuj wartość początkową.')
HPF_LPF={h*100+l:f'HPF {h*100 if h else "OFF"} / LPF {l*100 if l<25 else "OFF"} Hz' for h in range(21) for l in range(5,26) if l==25 or l>h}
for n,mode in [(45,'SSB'),(53,'AM'),(58,'FM'),(63,'CW'),(64,'RTTY')]:
    setting(n,'Korekcja audio','RX HPF/LPF — '+mode,HPF_LPF,'Ustawienie filtrów audio zeruje korekcję basów i sopranów tej emisji.',codec='bcd2')
for n,mode,direction,part in [(46,'SSB','RX','Basy'),(47,'SSB','RX','Soprany'),(48,'SSB','TX','Basy'),(49,'SSB','TX','Soprany'),(54,'AM','RX','Basy'),(55,'AM','RX','Soprany'),(56,'AM','TX','Basy'),(57,'AM','TX','Soprany'),(59,'FM','RX','Basy'),(60,'FM','RX','Soprany'),(61,'FM','TX','Basy'),(62,'FM','TX','Soprany')]:
    setting(n,'Korekcja audio',f'{part} — {mode} {direction}',{v:f'{v-5:+d}' for v in range(11)},'Korekcja RX może wyłączyć HPF/LPF tej emisji.',codec='bcd1')
for n,label in [(50,'WIDE'),(51,'MID'),(52,'NAR')]:
    setting(n,'Nadajnik','Pasmo SSB TX — '+label,{h*16+l:f'{lo}–{hi} Hz' for l,lo in enumerate([100,200,300,500]) for h,hi in enumerate([2500,2700,2800,2900])})
setting(65,'Klucz CW','Format numeru zawodów',options('Normalny','190 → ANO','190 → ANT','90 → NO','90 → NT'))
setting(66,'Klucz CW','Pamięć zwiększająca numer',{i:f'M{i}' for i in range(1,5)})
setting(67,'Klucz CW','Aktualny numer zawodów',limits=(1,9999))
setting(68,'Klucz CW','Głośność podsłuchu CW')
setting(69,'Klucz CW','Ogranicznik podsłuchu CW',SWITCH)
setting(70,'Klucz CW','Czas powtarzania',{i:f'{i} s' for i in range(1,61)},codec='bcd1')
setting(71,'Klucz CW','Opis wiadomości',options('Numer','Pierwsze znaki'))
setting(72,'Klucz CW','Stosunek kreski do kropki',{i:f'{i/10:.1f}' for i in range(28,46)},codec='bcd1')
setting(73,'Klucz CW','Czas narastania CW',options('2 ms','4 ms','6 ms','8 ms'))
setting(74,'Klucz CW','Polaryzacja łopatek',options('Normalna','Odwrócona'))
setting(75,'Klucz CW','Rodzaj klucza',options('Sztorcowy','BUG','Elektroniczny'))
setting(76,'Klucz CW','Kluczowanie UP/DOWN mikrofonu',SWITCH)
setting(77,'RTTY','Częstotliwość MARK',options('1275 Hz','1615 Hz','2125 Hz'))
setting(78,'RTTY','Przesunięcie RTTY',options('170 Hz','200 Hz','425 Hz'))
setting(79,'RTTY','Polaryzacja kluczowania',options('Normalna','Odwrócona'))
setting(80,'RTTY','USOS',SWITCH)
setting(81,'RTTY','Kod nowej linii',options('CR / LF / CR+LF','CR+LF'))
setting(82,'RTTY','Wiersze dekodera',options('2','3'))
setting(83,'Skanowanie','Szybkość skanowania',options('LOW','HIGH'))
setting(84,'Skanowanie','Wznawianie skanowania',SWITCH)
setting(85,'Odbiornik','Głębokość NB',{i:str(i+1) for i in range(10)})
setting(86,'Odbiornik','Szerokość NB')
setting(87,'VOX i BK-IN','Wzmocnienie VOX (SET)')
setting(88,'VOX i BK-IN','ANTI-VOX (SET)')
setting(89,'VOX i BK-IN','Opóźnienie VOX',{i:f'{i/10:.1f} s' for i in range(21)},codec='bcd1')
setting(90,'VOX i BK-IN','Voice Delay VOX',options('OFF','SHORT','MID','LONG'))
for index in range(1,5):
    add(f'keyer_{index}','Wiadomości CW',f'Pamięć klucza M{index}',f'1a02{index:02x}',None,
        'Maksymalnie 70 znaków. Zapisuje tekst, nie uruchamia nadawania.',codec='text',limits=(0,70))

BANDS=['1,8 MHz','3,5 MHz','7 MHz','10 MHz','14 MHz','18 MHz','21 MHz','24 MHz','28 MHz','50 MHz','GENE']
for band,label in enumerate(BANDS,1):
    for register in range(1,4):
        add(f'band_{band}_{register}','Rejestry pasm',f'{label} — rejestr {register}',f'1a01{band:02d}{register:02d}',None,
            'Format: MHz;emisja;FIL;DATA 0/1;ton 0/OFF 1/TONE 2/TSQL;CTCSS TX Hz;CTCSS SQL Hz. Zapis nie stroi aktywnego VFO.',codec='band')

for edge in range(1,31):
    add(f'edge_{edge}','Granice pasm użytkownika',f'Zakres {edge:02d}',f'1e03{edge:02d}',None,
        'Format: dolna granica MHz;górna granica MHz. Puste pole odczytu oznacza niezdefiniowany zakres.',codec='edges',
        warning='Zmienia granice pasm użytkownika używane przez sygnalizację i opcjonalny limit TX. Nie zmienia sprzętowego zakresu radia.')

CATALOG = {s[0]:s for s in SETTINGS}
for spec in SETTINGS:
    META.setdefault(spec[0],{'codec':'bcd2' if spec[4] is None else 'byte','limits':(0,255),'warning':''})

def choices_for(key,mode='USB'):
    if key=='bandwidth':
        if mode=='FM':
            return {}
        widths=list(range(200,10001,200)) if mode=='AM' else list(range(50,501,50))+list(range(600,2701 if mode.startswith('RTTY') else 3601,100))
        return {i:f'{v} Hz' for i,v in enumerate(widths)}
    if key=='agc_time':
        times=[.3,.5,.8,1.2,1.6,2,2.5,3,4,5,6,7,8] if mode=='AM' else [.1,.2,.3,.5,.8,1.2,1.6,2,2.5,3,4,5,6]
        return {0:'OFF',**{i+1:f'{v:g} s' for i,v in enumerate(times)}}
    return CATALOG[key][4]
