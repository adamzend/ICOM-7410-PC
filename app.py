from i18n import tr, set_language
from app_info import open_info, VERSION
import csv
import json
import logging
import queue
import sys
import threading
import time
import serial
from datetime import datetime
from decimal import Decimal
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import numpy as np
from PIL import Image, ImageTk
from serial.tools import list_ports
from radio import Radio, MODES, encode_bcd, memory_decode
from audio_engine import AudioInput, input_devices, spectrum, RATE, FFT_SIZE
from settings_catalog import SETTINGS, CATALOG, META, choices_for, TONES

ROOT = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
if getattr(sys, 'frozen', False) and (ROOT.parent / 'AGENTS.md').exists():
    ROOT = ROOT.parent
DATA = ROOT / 'dane'
DATA.mkdir(exist_ok=True)
logging.basicConfig(filename=DATA / 'program.log', level=logging.INFO, encoding='utf-8',
                    format='%(asctime)s %(levelname)s %(message)s')

def stamp():
    return datetime.now().strftime('%Y%m%d-%H%M%S-%f')

def hz_from_mhz(text):
    value = Decimal(str(text).strip().replace(',', '.')) * 1000000
    if not value.is_finite() or value != value.to_integral_value() or not 30000 <= value <= 60000000:
        raise ValueError(tr('Podaj częstotliwość 0,030000–60,000000 MHz, z dokładnością do 1 Hz.'))
    return int(value)

def build_memory(channel, name, rx, tx, mode, filt, split, original=None, extra=None):
    if not 1 <= channel <= 99 or mode not in MODES.values() or filt not in (1, 2, 3):
        raise ValueError(tr('Nieprawidłowy kanał, emisja lub filtr'))
    if not name or len(name) > 9 or any(not (c.isascii() and (c.isalnum() or c in ' /?.-')) for c in name):
        raise ValueError(tr('Nazwa: 1–9 znaków ASCII (litery, cyfry, spacja, / ? . -).'))
    for hz in (rx, tx):
        if not 30000 <= hz <= 60000000:
            raise ValueError(tr('Częstotliwość poza zakresem radia'))
    code = next(k for k, v in MODES.items() if v == mode)
    block = encode_bcd(rx, 5) + bytes([code, filt, 0, 0]) + bytes.fromhex('000885000885')
    raw = bytearray(original if original is not None and len(original) == 42 else
                    encode_bcd(channel, 2, False) + b'\x00' + block + block + b' '*9)
    raw[:2] = encode_bcd(channel, 2, False)
    raw[2] = (raw[2] & 0xf0) | int(split)
    raw[3:8], raw[18:23] = encode_bcd(rx, 5), encode_bcd(tx, 5)
    raw[8:10] = bytes([code, filt])
    raw[23:25] = bytes([code, filt])
    if extra:
        if extra['tx_mode'] not in MODES.values() or int(extra['tx_filt']) not in (1,2,3):
            raise ValueError(tr('Nieprawidłowa emisja lub filtr TX'))
        raw[23]=next(k for k,v in MODES.items() if v==extra['tx_mode'])
        raw[24]=int(extra['tx_filt'])
        for key,offset,allowed in [('rx_data',10,(0,1)),('tx_data',25,(0,1)),('rx_tone',11,(0,1,2)),('tx_tone',26,(0,1,2))]:
            if int(extra[key]) not in allowed:
                raise ValueError(tr('Niepoprawne pole ')+key)
            raw[offset]=int(extra[key])
        for key,offset in [('rx_ctcss',12),('rx_tsql',15),('tx_ctcss',27),('tx_tsql',30)]:
            if int(extra[key]) not in TONES:
                raise ValueError(tr('Niepoprawny ton ')+key)
            raw[offset:offset+3]=encode_bcd(int(extra[key]),3,False)
        if int(extra['selected']) not in (0,1):
            raise ValueError(tr('Nieprawidłowa flaga SELECT'))
        raw[2]=(int(extra['selected'])<<4)|int(split)
    raw[33:42] = name.ljust(9).encode('ascii')
    return bytes(raw)

class Worker(threading.Thread):
    def __init__(self, commands, events):
        super().__init__(daemon=True)
        self.commands, self.events = commands, events
        self.radio = None
        self.running = True
        self.connection_args = None
        self.healthy = False
        self.failures = 0
        self.reconnect_at = 0

    def drop_port(self):
        if self.radio:
            try:
                self.radio.close()
            except Exception:
                pass
        self.radio=None
        self.healthy=False

    def poll_radio(self):
        state=self.radio.state()
        self.events.put(('state',state))
        if not self.healthy:
            logging.info('CI-V connected/recovered %s',self.connection_args)
            self.events.put(('connected',tr(f'Połączono: {self.connection_args[0]} / {self.connection_args[1]} bit/s')))
        self.healthy=True
        self.failures=0

    def run(self):
        next_poll = 0
        while self.running:
            try:
                kind, args = self.commands.get(timeout=.08)
            except queue.Empty:
                kind, args = 'poll', ()
            try:
                if kind == 'stop':
                    self.running = False
                elif kind == 'disconnect':
                    self.connection_args=None
                    self.drop_port()
                    self.events.put(('offline', tr('Rozłączono radio')))
                elif kind == 'connect':
                    self.connection_args=args
                    self.drop_port()
                    self.radio = Radio(*args)
                    self.poll_radio()
                elif kind=='poll' and not self.radio and self.connection_args and time.monotonic()>=self.reconnect_at:
                    self.radio=Radio(*self.connection_args)
                    self.poll_radio()
                elif self.radio:
                    if kind == 'poll' and time.monotonic() >= next_poll:
                        self.poll_radio()
                        next_poll = time.monotonic() + .6
                    elif kind!='poll' and not self.healthy:
                        raise RuntimeError(tr('Łączność jest odzyskiwana. Operacja nie została wysłana; ponów ją po połączeniu.'))
                    elif kind == 'tune':
                        self.events.put(('state', self.radio.tune(*args)))
                    elif kind == 'mode':
                        self.events.put(('state', self.radio.set_mode(*args)))
                    elif kind == 'recall':
                        self.events.put(('state',self.radio.recall_profile(args[0])))
                        self.events.put(('recalled',args[0]['channel']))
                    elif kind == 'settings':
                        context=self.radio.state()
                        self.events.put(('settings_context',context))
                        values = {}
                        for spec in SETTINGS:
                            try:
                                values[spec[0]] = {'value': self.radio.read_setting(spec[0])}
                            except (RuntimeError, ValueError) as exc:
                                values[spec[0]] = {'error': str(exc)}
                        (DATA/f'ustawienia-{stamp()}.json').write_text(json.dumps(values,indent=2,ensure_ascii=False),encoding='utf-8')
                        self.events.put(('settings', values))
                    elif kind == 'setting':
                        key,value,expected_context = args
                        context=self.radio.state()
                        if key in ('bandwidth','data','agc_time') and (context['mode'],context['filter']) != expected_context:
                            raise RuntimeError(tr('Emisja lub filtr zmieniły się od odczytu. Odśwież ustawienia przed zapisem.'))
                        old = self.radio.read_setting(key)
                        record = {'key':key,'before':old,'requested':value,'verified':False}
                        path = DATA/f'zmiana-ustawienia-{stamp()}.json'
                        path.write_text(json.dumps(record,indent=2),encoding='utf-8')
                        actual = self.radio.write_setting(key,value)
                        record.update(verified=True,after=actual)
                        path.write_text(json.dumps(record,indent=2),encoding='utf-8')
                        self.events.put(('settings_context',self.radio.state()))
                        self.events.put(('setting', (key,actual)))
                    elif kind == 'memories':
                        rows = []
                        for channel in range(1, 102):
                            rows.append(self.radio.read_memory(channel))
                            self.events.put(('progress', tr(f'Odczyt pamięci {channel}/101')))
                        path = DATA / f'pamieci-{stamp()}.json'
                        path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding='utf-8')
                        self.events.put(('memories', rows))
                        self.events.put(('info', tr(f'Odczytano 101 pamięci. Kopia: {path.name}')))
                    elif kind == 'write':
                        channel, changes = args
                        old = self.radio.read_memory(channel)
                        path = DATA / f'przed-zapisem-{channel:02}-{stamp()}.json'
                        path.write_text(json.dumps(old, indent=2, ensure_ascii=False), encoding='utf-8')
                        raw = build_memory(channel, **changes, original=bytes.fromhex(old['raw']))
                        result = self.radio.write_memory(raw)
                        self.events.put(('memory_written', result))
                        self.events.put(('info', tr(f'Pamięć {channel}: zapis i weryfikacja OK. Kopia: {path.name}')))
                elif kind not in ('poll', 'stop'):
                    raise RuntimeError(tr('Najpierw połącz radio'))
            except Exception as exc:
                logging.exception('Operacja %s', kind)
                self.events.put(('error', str(exc)))
                if isinstance(exc,(TimeoutError,serial.SerialException,OSError)) or kind in ('poll','connect'):
                    self.healthy=False
                    self.failures+=1
                    if isinstance(exc,(serial.SerialException,OSError)) or self.failures>=3 or kind=='connect':
                        self.drop_port()
                    self.reconnect_at=time.monotonic()+min(10,2*self.failures)
                    next_poll=time.monotonic()+1
                    self.events.put(('recovering',tr('Brak bieżącego odczytu — automatycznie odzyskuję połączenie')))
        if self.radio:
            self.radio.close()

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.language='en'
        set_language('en')
        self.title('ICOM-7410-PC')
        self.geometry(f'1100x{min(800, self.winfo_screenheight()-110)}')
        self.minsize(880, 650)
        self.state('zoomed')
        self.configure(bg='#20262d')
        self.commands, self.events = queue.Queue(), queue.Queue()
        self.worker = Worker(self.commands, self.events)
        self.worker.start()
        self.audio = None
        self.last_audio = 0
        self.rows = {}
        self.memory_picker = None
        self.memory_extra=None
        self.connected = False
        self.busy = False
        self.current = None
        self.history = np.zeros((220, 850, 3), dtype=np.uint8)
        self.history[:] = (8, 15, 30)
        self.photo = None
        self.build_ui()
        self.after(100,self.tick)

    def build_ui(self):
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('TFrame', background='#20262d')
        style.configure('TLabel', background='#20262d', foreground='#edf2f6', font=('Segoe UI', 10))
        style.configure('TButton', padding=7, font=('Segoe UI', 10))
        style.configure('TButton',background='#225ea8',foreground='#ffffff',bordercolor='#327ad1')
        style.map('TButton',background=[('active','#307dd1'),('disabled','#263b51')],foreground=[('disabled','#8798aa')])
        style.configure('TEntry',fieldbackground='#152b41',foreground='#eff6ff',insertcolor='#ffffff')
        style.configure('TCombobox',fieldbackground='#152b41',background='#225ea8',foreground='#eff6ff',arrowcolor='#eff6ff')
        style.map('TCombobox',fieldbackground=[('readonly','#152b41')],foreground=[('readonly','#eff6ff')])
        style.configure('TSpinbox',fieldbackground='#152b41',foreground='#eff6ff',background='#225ea8',arrowcolor='#eff6ff')
        style.configure('Treeview',background='#142538',fieldbackground='#142538',foreground='#e5effb',rowheight=30)
        style.configure('Treeview.Heading',background='#215b82',foreground='#ffffff',font=('Segoe UI',10,'bold'))
        style.map('Treeview',background=[('selected','#126f8a')],foreground=[('selected','#ffffff')])
        style.configure('TNotebook', background='#20262d', borderwidth=0)
        style.configure('TNotebook.Tab', padding=(18, 9), font=('Segoe UI', 10))
        style.configure('TNotebook.Tab',background='#193d5d',foreground='#d4edff')
        style.map('TNotebook.Tab',background=[('selected','#087f8c'),('active','#24658c')],foreground=[('selected','#ffffff')])
        style.configure('TCheckbutton',background='#20262d',foreground='#d4edff')
        self.option_add('*TCombobox*Listbox.background','#152b41')
        self.option_add('*TCombobox*Listbox.foreground','#eff6ff')
        self.status = tk.StringVar(value=tr('Radio niepołączone. Waterfall zatrzymany.'))
        bar = ttk.Frame(self, padding=12)
        bar.pack(fill='x')
        ttk.Label(bar, text='ICOM-7410-PC', font=('Segoe UI', 15, 'bold')).pack(side='left', padx=(0, 20))
        self.port = tk.StringVar(value='COM8')
        self.baud = tk.StringVar(value='19200')
        ttk.Label(bar, text='Port').pack(side='left')
        ttk.Combobox(bar, textvariable=self.port, values=[p.device for p in list_ports.comports()], width=8).pack(side='left', padx=6)
        ttk.Combobox(bar, textvariable=self.baud, values=['19200','9600','4800','1200','300'], width=8, state='readonly').pack(side='left')
        self.connect_btn = ttk.Button(bar, text=tr('Połącz'), command=self.connect)
        self.connect_btn.pack(side='left', padx=8)
        self.disconnect_btn = ttk.Button(bar, text=tr('Rozłącz'), command=lambda:self.submit('disconnect'))
        self.disconnect_btn.pack(side='left')
        ttk.Button(bar,text='Info',command=lambda:open_info(self)).pack(side='right',padx=(8,0))
        self.flag_images={}
        for language in ('pl','en'):
            flag=ImageTk.PhotoImage(Image.open(Path(__file__).resolve().parent/'assets'/f'{language}.png'))
            self.flag_images[language]=flag
            ttk.Button(bar,text=language.upper(),image=flag,compound='left',
                       command=lambda lang=language:self.change_language(lang)).pack(side='right',padx=3)
        self.book = ttk.Notebook(self)
        self.book.pack(fill='both', expand=True, padx=12)
        self.panel = ttk.Frame(self.book, padding=12)
        self.mem = ttk.Frame(self.book, padding=12)
        self.book.add(self.panel, text=tr('Panel i waterfall'))
        self.book.add(self.mem, text=tr('Baza i pamięci'))
        self.build_panel()
        self.build_memories()
        self.build_settings()
        ttk.Label(self, textvariable=self.status, wraplength=1050, padding=12).pack(fill='x')
        self.protocol('WM_DELETE_WINDOW', self.close)

    @staticmethod
    def display_choices(key,mode='USB'):
        choices=choices_for(key,mode)
        return {k:tr(v) for k,v in choices.items()} if choices is not None else None

    def change_language(self,language):
        if language==self.language:
            return
        names=('port','baud','freq_entry','mode_entry','filter_entry','device','span','floor','split')
        values={name:getattr(self,name).get() for name in names}
        edit={key:value.get() for key,value in self.edit.items()}
        settings=dict(self.setting_values)
        errors=dict(self.setting_errors)
        context=self.settings_context
        selected=self.settings_tree.selection()
        draft=self.setting_draft.get()
        enum_value=None
        if selected and selected[0] in CATALOG:
            choices=self.display_choices(selected[0],(context or {}).get('mode','USB'))
            if choices is not None:
                enum_value=next((k for k,v in choices.items() if v==draft),None)
        tab=self.book.index(self.book.select())
        show_info=getattr(self,'info_window',None) is not None and self.info_window.winfo_exists()
        for widget in self.winfo_children():
            widget.destroy()
        self.memory_picker=None
        self.info_window=None
        self.language=language
        set_language(language)
        self.build_ui()
        for name,value in values.items():
            getattr(self,name).set(value)
        for key,value in edit.items():
            self.edit[key].set(value)
        self.setting_values=settings
        self.setting_errors=errors
        self.settings_context=context
        self.fill_table()
        self.fill_settings_tree()
        if selected and self.settings_tree.exists(selected[0]):
            self.settings_tree.selection_set(selected)
            self.render_setting_editor()
            choices=self.display_choices(selected[0],(context or {}).get('mode','USB')) if selected[0] in CATALOG else None
            self.setting_draft.set(choices[enum_value] if choices is not None and enum_value in choices else draft)
        self.book.select(tab)
        if self.connected and self.current:
            self.freq_display.configure(text=f"{self.current['hz']:,}".replace(',','.'))
            self.mode_display.configure(text=f"{self.current['mode']}    FIL{self.current['filter']}    • "+tr('ODCZYT Z RADIA'))
            self.status.set(tr('Połączono: ')+self.port.get())
        if self.audio:
            self.audio_btn.configure(text=tr('Zatrzymaj waterfall'))
            self.draw_waterfall()
        if show_info:
            open_info(self)

    def submit(self, kind, *args):
        if self.busy and kind not in ('poll', 'stop'):
            self.status.set(tr('Poczekaj na zakończenie operacji pamięci.'))
            return
        if not self.connected and kind not in ('connect','disconnect','stop','poll'):
            self.status.set(tr('Brak aktualnego połączenia. Zaczekaj na jego odzyskanie.'))
            return
        self.commands.put((kind, args))

    def connect(self):
        if self.connected:
            return
        self.connect_btn.configure(state='disabled')
        self.status.set(tr('Łączenie z radiem…'))
        self.submit('connect', self.port.get().strip(), int(self.baud.get()))

    def build_panel(self):
        lcd = tk.Frame(self.panel, bg='#102a43', padx=22, pady=12, highlightthickness=3, highlightbackground='#1595a2')
        lcd.pack(fill='x')
        self.mode_display = tk.Label(lcd, text=tr('RADIO ODŁĄCZONE'), bg='#102a43', fg='#4edbd0', font=('Consolas', 15))
        self.mode_display.pack(anchor='w')
        self.freq_display = tk.Label(lcd, text='--.---.---', bg='#102a43', fg='#ffcf70', font=('Consolas', 43, 'bold'))
        self.freq_display.pack(anchor='w')
        tk.Label(lcd, text=tr('CZĘSTOTLIWOŚĆ [MHz]     •     CI-V / USB'), bg='#102a43', fg='#a5c6df', font=('Consolas', 11)).pack(anchor='w')
        controls = ttk.Frame(self.panel, padding=(0, 12))
        controls.pack(fill='x')
        self.freq_entry = tk.StringVar(value='26.943000')
        ttk.Label(controls, text='MHz').pack(side='left')
        ttk.Entry(controls, textvariable=self.freq_entry, width=14).pack(side='left', padx=5)
        ttk.Button(controls, text=tr('Ustaw częstotliwość'), command=self.tune).pack(side='left')
        ttk.Button(self.panel, text=tr('Wybierz częstotliwość z pamięci…'), command=self.open_memory_picker).pack(anchor='w', pady=(0,8))
        self.mode_entry = tk.StringVar(value='AM')
        self.filter_entry = tk.StringVar(value='2')
        ttk.Combobox(controls, textvariable=self.mode_entry, values=list(MODES.values()), width=7, state='readonly').pack(side='left', padx=(18,5))
        ttk.Label(controls, text='FIL').pack(side='left')
        ttk.Combobox(controls, textvariable=self.filter_entry, values=['1','2','3'], width=3, state='readonly').pack(side='left', padx=5)
        ttk.Button(controls, text=tr('Ustaw emisję / filtr'), command=lambda:self.submit('mode', self.mode_entry.get(), int(self.filter_entry.get()))).pack(side='left')
        audio_bar = ttk.Frame(self.panel)
        audio_bar.pack(fill='x', pady=(2,8))
        self.devices = input_devices()
        names = [f'{i}: {name}' for i, name in self.devices]
        preferred = next((s for s in names if 'USB Audio CODEC' in s), '')
        self.device = tk.StringVar(value=preferred)
        ttk.Label(audio_bar, text=tr('Wejście audio')).pack(side='left')
        ttk.Combobox(audio_bar, textvariable=self.device, values=names, width=40, state='readonly').pack(side='left', padx=8)
        self.audio_btn = ttk.Button(audio_bar, text=tr('Uruchom waterfall'), command=self.toggle_audio)
        self.audio_btn.pack(side='left')
        self.audio_status = tk.StringVar(value=tr('Audio zatrzymane'))
        ttk.Label(audio_bar, textvariable=self.audio_status).pack(side='left', padx=12)
        self.plot = tk.Canvas(self.panel, bg='#080f1e', height=105, highlightthickness=0)
        self.plot.pack(fill='x')
        self.waterfall = tk.Canvas(self.panel, bg='#080f1e', height=220, highlightthickness=0)
        self.waterfall.pack(fill='both', expand=True)
        self.image_item = self.waterfall.create_image(0,0,anchor='nw')
        settings = ttk.Frame(self.panel)
        settings.pack(fill='x', pady=(10,0))
        self.span = tk.StringVar(value='5000')
        ttk.Label(settings, text=tr('Zakres audio [Hz]')).pack(side='left')
        spanbox = ttk.Combobox(settings, textvariable=self.span, values=['3000','5000','10000'], width=7, state='readonly')
        spanbox.pack(side='left', padx=8)
        spanbox.bind('<<ComboboxSelected>>', lambda e:self.clear_waterfall())
        self.floor = tk.DoubleVar(value=-100)
        ttk.Label(settings, text=tr('Tło [dBFS]')).pack(side='left', padx=(12,4))
        ttk.Scale(settings, from_=-130, to=-40, variable=self.floor, length=150).pack(side='left')
        ttk.Button(settings, text=tr('Wyczyść'), command=self.clear_waterfall).pack(side='left', padx=10)
        ttk.Label(self.panel, text=tr('Waterfall AUDIO: częstotliwość dźwięku, nie panorama RF. Nowe dane u góry. Brak obsługi nadawania w wersji 0.1.'), wraplength=1000).pack(anchor='w', pady=(8,0))

    def build_memories(self):
        bar = ttk.Frame(self.mem)
        bar.pack(fill='x', pady=(0,12))
        ttk.Button(bar, text=tr('Odczytaj 101 pamięci + kopia'), command=self.read_memories).pack(side='left')
        ttk.Button(bar, text=tr('Eksport CSV'), command=self.export_csv).pack(side='left', padx=8)
        ttk.Button(bar, text=tr('Import CSV do biblioteki'), command=self.import_csv).pack(side='left')
        ttk.Button(bar, text=tr('Wybierz częstotliwość…'), command=self.open_memory_picker).pack(side='left',padx=8)
        columns = ('channel','name','rx','tx','mode','filter','split')
        self.table = ttk.Treeview(self.mem, columns=columns, show='headings', selectmode='browse', height=16)
        for key, title, width in zip(columns, [tr('Kanał'),tr('Nazwa'),'RX [MHz]','TX [MHz]',tr('Emisja'),tr('Filtr'),'Split'], [65,170,140,140,80,60,70]):
            self.table.heading(key, text=title)
            self.table.column(key, width=width, stretch=True)
        scroll = ttk.Scrollbar(self.mem, orient='vertical', command=self.table.yview)
        self.table.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        self.table.pack(fill='both', expand=True)
        self.table.bind('<<TreeviewSelect>>', self.select_memory)
        form = ttk.Frame(self.mem, padding=(0,12))
        form.pack(fill='x')
        self.edit = {}
        for col, (key, title, default, width) in enumerate([
            ('channel',tr('Kanał 1–99'),'1',8),('name',tr('Nazwa (9 znaków)'),'',14),
            ('rx','RX [MHz]','14.200000',14),('tx','TX [MHz]','14.200000',14),
            ('mode',tr('Emisja'),'USB',8),('filter',tr('Filtr'),'2',5)]):
            ttk.Label(form, text=title).grid(row=0,column=col,sticky='w',padx=4)
            self.edit[key] = tk.StringVar(value=default)
            if key in ('mode','filter'):
                values = list(MODES.values()) if key == 'mode' else ['1','2','3']
                widget = ttk.Combobox(form,textvariable=self.edit[key],values=values,state='readonly',width=width)
            else:
                widget = ttk.Entry(form,textvariable=self.edit[key],width=width)
            widget.grid(row=1,column=col,padx=4)
        self.split = tk.BooleanVar(value=False)
        ttk.Checkbutton(form,text='Split',variable=self.split).grid(row=1,column=6,padx=8)
        actions = ttk.Frame(self.mem)
        actions.pack(fill='x')
        ttk.Button(actions,text=tr('Zapisz ten kanał do radia…'),command=self.write_memory).pack(side='left')
        ttk.Button(actions,text=tr('DATA, CTCSS i osobne ustawienia TX…'),command=self.edit_memory_extra).pack(side='left',padx=10)
        ttk.Label(self.mem,text=tr('Import CSV nie zapisuje niczego w radiu. Zapis pojedynczego kanału wymaga potwierdzenia. P1/P2 tylko do odczytu.\nUstawienia dodatkowe: osobna emisja/filtr TX, DATA, ton i TSQL dla obu części pamięci oraz SELECT.'),wraplength=1000).pack(anchor='w',pady=12)

    def edit_memory_extra(self):
        default={'tx_mode':self.edit['mode'].get(),'tx_filt':int(self.edit['filter'].get()),'rx_data':0,'tx_data':0,'rx_tone':0,'tx_tone':0,
                 'rx_ctcss':885,'rx_tsql':885,'tx_ctcss':885,'tx_tsql':885,'selected':0}
        values=dict(self.memory_extra or default)
        dialog=tk.Toplevel(self)
        dialog.title(tr('Pamięć — DATA, CTCSS i ustawienia TX'))
        dialog.configure(bg='#20262d')
        dialog.transient(self)
        dialog.grab_set()
        fields={}
        specs=[('tx_mode',tr('Emisja TX'),list(MODES.values())),('tx_filt',tr('Filtr TX'),[1,2,3]),
               ('rx_data','DATA RX',[0,1]),('tx_data','DATA TX',[0,1]),('rx_tone',tr('Ton RX: 0 OFF / 1 TONE / 2 TSQL'),[0,1,2]),
               ('tx_tone',tr('Ton TX: 0 OFF / 1 TONE / 2 TSQL'),[0,1,2]),('rx_ctcss',tr('CTCSS w części RX [Hz]'),TONES),
               ('rx_tsql',tr('TSQL w części RX [Hz]'),TONES),('tx_ctcss',tr('CTCSS w części TX [Hz]'),TONES),('tx_tsql',tr('TSQL w części TX [Hz]'),TONES),
               ('selected',tr('SELECT do skanowania'),[0,1])]
        for row,(key,label,choices) in enumerate(specs):
            tonal=key.endswith(('ctcss','tsql'))
            display=[f'{v/10:.1f}' for v in choices] if tonal else [str(v) for v in choices]
            fields[key]=tk.StringVar(value=f'{values[key]/10:.1f}' if tonal else str(values[key]))
            ttk.Label(dialog,text=label).grid(row=row,column=0,padx=16,pady=6,sticky='w')
            ttk.Combobox(dialog,textvariable=fields[key],values=display,state='readonly',width=18).grid(row=row,column=1,padx=16,pady=6)
        def accept():
            extra={key:(fields[key].get() if key=='tx_mode' else int(Decimal(fields[key].get())*(10 if key.endswith(('ctcss','tsql')) else 1))) for key in fields}
            self.memory_extra=extra
            dialog.destroy()
            self.status.set(tr('Dane dodatkowe przygotowane. Dopiero Zapisz ten kanał zmieni pamięć radia.'))
        ttk.Button(dialog,text=tr('Zachowaj w formularzu'),command=accept).grid(row=len(specs),column=0,padx=16,pady=16)
        ttk.Button(dialog,text=tr('Anuluj'),command=dialog.destroy).grid(row=len(specs),column=1,padx=16,pady=16)

    def tune(self):
        try:
            self.submit('tune', hz_from_mhz(self.freq_entry.get()))
        except Exception as exc:
            messagebox.showerror(tr('Częstotliwość'),str(exc))

    def build_settings(self):
        panel=ttk.Frame(self.book,padding=12)
        self.book.add(panel,text=tr('Ustawienia radia'))
        top=ttk.Frame(panel)
        top.pack(fill='x',pady=(0,12))
        ttk.Button(top,text=tr('Odczytaj wszystkie ustawienia'),command=self.read_settings).pack(side='left')
        self.settings_status=tk.StringVar(value=tr('Odczytaj konfigurację z radia. Wybierz grupę lub wyszukaj funkcję.'))
        ttk.Label(top,textvariable=self.settings_status).pack(side='left',padx=14)
        body=ttk.Panedwindow(panel,orient='horizontal')
        body.pack(fill='both',expand=True)
        left=ttk.Frame(body)
        right=ttk.Frame(body,padding=22)
        body.add(left,weight=2)
        body.add(right,weight=3)
        self.settings_search=tk.StringVar()
        ttk.Label(left,text=tr('Szukaj funkcji, np. CTCSS, DATA, filtr, USB')).pack(anchor='w',pady=(0,5))
        ttk.Entry(left,textvariable=self.settings_search).pack(fill='x',pady=(0,8))
        tree_area=ttk.Frame(left)
        tree_area.pack(fill='both',expand=True)
        self.settings_tree=ttk.Treeview(tree_area,columns=('value',),show='tree headings',selectmode='browse')
        self.settings_tree.heading('#0',text=tr('Funkcja radia'))
        self.settings_tree.heading('value',text=tr('Odczyt'))
        self.settings_tree.column('#0',width=265)
        self.settings_tree.column('value',width=170)
        scrollbar=ttk.Scrollbar(tree_area,orient='vertical',command=self.settings_tree.yview)
        scrollbar.pack(side='right',fill='y')
        self.settings_tree.configure(yscrollcommand=scrollbar.set)
        self.settings_tree.pack(fill='both',expand=True)
        self.settings_tree.bind('<<TreeviewSelect>>',lambda e:self.render_setting_editor())
        self.settings_search.trace_add('write',lambda *a:self.fill_settings_tree())
        self.setting_values={}
        self.setting_errors={}
        self.settings_context=None
        self.settings_widgets={}
        self.setting_title=tk.StringVar(value=tr('Wybierz ustawienie z listy'))
        self.setting_hint=tk.StringVar(value=tr('Zmiany są wysyłane pojedynczo i sprawdzane odczytem.'))
        self.setting_current=tk.StringVar(value=tr('Stan radia: —'))
        self.setting_draft=tk.StringVar()
        self.setting_warning=tk.StringVar()
        ttk.Label(right,textvariable=self.setting_title,font=('Segoe UI',20,'bold'),foreground='#5ddad5',wraplength=640).pack(anchor='w',pady=(0,18))
        ttk.Label(right,textvariable=self.setting_hint,wraplength=640).pack(anchor='w',pady=(0,18))
        ttk.Label(right,textvariable=self.setting_current,font=('Segoe UI',13),foreground='#ffcf70',wraplength=640).pack(anchor='w',pady=(0,20))
        self.setting_choice=ttk.Combobox(right,textvariable=self.setting_draft,state='readonly',width=48)
        self.setting_spin=ttk.Spinbox(right,textvariable=self.setting_draft,width=20)
        self.setting_text=ttk.Entry(right,textvariable=self.setting_draft,width=60)
        self.setting_apply=ttk.Button(right,text=tr('Zastosuj i sprawdź odczyt'),command=self.apply_selected_setting,state='disabled')
        self.setting_apply.pack(anchor='w',pady=18)
        ttk.Label(right,textvariable=self.setting_warning,foreground='#ffaf87',wraplength=640).pack(anchor='w',pady=15)
        ttk.Label(right,text=tr('Odczyt jest migawką. Po zmianie emisji lub FIL odśwież konfigurację. Zmiana pola nie zmienia radia.'),foreground='#a7bbce',wraplength=640).pack(anchor='w',pady=20)
        self.fill_settings_tree()

    def fill_settings_tree(self):
        selected=self.settings_tree.selection()
        opened={i:self.settings_tree.item(i,'open') for i in self.settings_tree.get_children()}
        self.settings_tree.delete(*self.settings_tree.get_children())
        term=self.settings_search.get().strip().casefold()
        for spec in SETTINGS:
            key,group,label,command,_,hint=spec
            group,label,hint=tr(group),tr(label),tr(hint)
            if term and term not in (group+' '+label+' '+hint+' '+command).casefold():
                continue
            parent='group:'+group
            if not self.settings_tree.exists(parent):
                self.settings_tree.insert('', 'end',iid=parent,text=group,open=bool(term) or opened.get(parent,False))
            value=self.setting_values.get(key)
            choices=self.display_choices(key,(self.settings_context or {}).get('mode','USB'))
            display=(choices.get(value,str(value)) if choices is not None else str(value)) if value is not None else (tr('niedostępne') if key in self.setting_errors else '—')
            self.settings_tree.insert(parent,'end',iid=key,text=label,values=(display,))
        if selected and self.settings_tree.exists(selected[0]):
            self.settings_tree.selection_set(selected)

    def render_setting_editor(self):
        selection=self.settings_tree.selection()
        for widget in (self.setting_choice,self.setting_spin,self.setting_text):
            widget.pack_forget()
        self.setting_apply.configure(state='disabled')
        if not selection or selection[0] not in CATALOG:
            return
        key=selection[0]
        spec,meta=CATALOG[key],META[key]
        mode=(self.settings_context or {}).get('mode','USB')
        choices=self.display_choices(key,mode)
        self.setting_title.set(tr(spec[2]))
        self.setting_hint.set(tr(spec[5])+'\nCI-V: '+spec[3].upper()+' • '+tr(spec[1]))
        self.setting_warning.set(tr(meta.get('warning','')))
        current=self.setting_values.get(key)
        if key in self.setting_errors:
            self.setting_current.set(tr('Odczyt: ')+self.setting_errors[key])
        elif current is None:
            self.setting_current.set(tr('Stan radia: nie odczytano'))
        else:
            self.setting_current.set(tr('Stan radia: ')+(choices.get(current,str(current)) if choices is not None else str(current)))
        if meta['codec'] in ('text','band','edges'):
            widget=self.setting_text
        elif choices is None:
            widget=self.setting_spin
            widget.configure(from_=meta['limits'][0],to=meta['limits'][1])
        else:
            widget=self.setting_choice
            widget.configure(values=list(choices.values()))
        widget.pack(before=self.setting_apply,anchor='w',fill='x')
        self.setting_draft.set((choices.get(current,'') if choices is not None else str(current)) if current is not None else '')
        if self.connected and current is not None and (choices is None or choices):
            self.setting_apply.configure(state='normal')

    def read_settings(self):
        if not self.connected or self.busy:
            self.status.set(tr('Najpierw połącz radio i zaczekaj na zakończenie bieżącej operacji.'))
            return
        self.submit('settings')
        self.busy=True
        self.settings_status.set(tr('Odczytywanie wszystkich ustawień…'))

    def show_setting(self,key,value):
        self.setting_values[key]=value
        self.setting_errors.pop(key,None)
        self.fill_settings_tree()
        self.render_setting_editor()

    def apply_selected_setting(self):
        selected=self.settings_tree.selection()
        if selected and selected[0] in CATALOG:
            self.apply_setting(selected[0])

    def apply_setting(self,key):
        if not self.connected or self.busy or key not in self.setting_values:
            return
        try:
            meta=META[key]
            text=self.setting_draft.get()
            choices=self.display_choices(key,(self.settings_context or {}).get('mode','USB'))
            value=text if meta['codec'] in ('text','band','edges') else (int(text) if choices is None else next(k for k,v in choices.items() if v==text))
            if choices is None and meta['codec'] not in ('text','band','edges') and not meta['limits'][0]<=value<=meta['limits'][1]:
                raise ValueError(tr('Wartość poza zakresem ')+str(meta['limits']))
            if meta.get('warning') and not messagebox.askyesno(tr('Potwierdź zmianę'),tr(CATALOG[key][2])+'\n\n'+tr(meta['warning'])+tr('\n\nZastosować wybraną wartość?')):
                return
            context=self.settings_context or self.current
            self.submit('setting',key,value,(context['mode'],context['filter']))
            self.busy=True
            self.settings_status.set(tr('Wysyłanie i sprawdzanie: ')+tr(CATALOG[key][2]))
        except Exception as exc:
            messagebox.showerror(tr('Ustawienie'),str(exc))

    def read_memories(self):
        if not self.connected or self.busy:
            self.status.set(tr('Najpierw połącz radio i zaczekaj na zakończenie bieżącej operacji.'))
            return
        self.submit('memories')
        self.busy = True

    def open_memory_picker(self):
        if self.memory_picker is not None and self.memory_picker.winfo_exists():
            self.memory_picker.lift()
            return
        window=self.memory_picker=tk.Toplevel(self)
        window.title(tr('Wybierz częstotliwość z pamięci'))
        window.geometry('820x520')
        window.minsize(650,380)
        window.configure(bg='#20262d')
        window.transient(self)
        body=ttk.Frame(window,padding=16)
        body.pack(fill='both',expand=True)
        bar=ttk.Frame(body)
        bar.pack(fill='x',pady=(0,12))
        ttk.Label(bar,text=tr('Szukaj nazwy, kanału lub MHz')).pack(side='left')
        self.picker_search=tk.StringVar()
        search=ttk.Entry(bar,textvariable=self.picker_search,width=24)
        search.pack(side='left',padx=8)
        ttk.Button(bar,text=tr('Odczytaj pamięci z radia'),command=self.read_memories).pack(side='right')
        table_area=ttk.Frame(body)
        table_area.pack(fill='both',expand=True)
        self.picker_table=ttk.Treeview(table_area,columns=('channel','name','rx','mode','filter'),show='headings',selectmode='browse')
        for key,title,width in zip(('channel','name','rx','mode','filter'),(tr('Kanał'),tr('Nazwa'),'RX [MHz]',tr('Emisja'),tr('Filtr')),(65,220,150,85,60)):
            self.picker_table.heading(key,text=title)
            self.picker_table.column(key,width=width,minwidth=50)
        scroll=ttk.Scrollbar(table_area,orient='vertical',command=self.picker_table.yview)
        self.picker_table.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right',fill='y')
        self.picker_table.pack(fill='both',expand=True)
        self.picker_info=tk.StringVar()
        ttk.Label(body,textvariable=self.picker_info,wraplength=760).pack(anchor='w',pady=10)
        ttk.Label(body,text=tr('Przywołuje RX, emisję, filtr i DATA; w FM także CTCSS/TSQL. Nie zmienia częstotliwości TX ani split.'),wraplength=760).pack(anchor='w')
        actions=ttk.Frame(body)
        actions.pack(fill='x',pady=(12,0))
        ttk.Button(actions,text=tr('Przywołaj ustawienia pamięci'),command=self.choose_memory_frequency).pack(side='left')
        ttk.Button(actions,text=tr('Zamknij'),command=window.destroy).pack(side='right')
        self.picker_search.trace_add('write',lambda *args:self.refresh_memory_picker())
        self.picker_table.bind('<Double-1>',self.choose_memory_frequency)
        self.picker_table.bind('<Return>',self.choose_memory_frequency)
        window.bind('<Escape>',lambda e:window.destroy())
        self.refresh_memory_picker()
        search.focus_set()
        if not self.rows and self.connected and not self.busy:
            self.read_memories()
            self.picker_info.set(tr('Trwa odczyt pamięci z radia…'))

    def refresh_memory_picker(self):
        if self.memory_picker is None or not self.memory_picker.winfo_exists():
            return
        selected=self.picker_table.selection()
        self.picker_table.delete(*self.picker_table.get_children())
        query=self.picker_search.get().strip().casefold().replace(',','.')
        for ch,row in sorted(self.rows.items()):
            if row.get('empty'):
                continue
            channel={100:'P1',101:'P2'}.get(ch,str(ch))
            values=(channel,row['name'],f"{row['rx']/1e6:.6f}",row['mode'],f"FIL{row['filter']}")
            if query in ' '.join(map(str,values)).casefold():
                self.picker_table.insert('','end',iid=str(ch),values=values)
        if selected and self.picker_table.exists(selected[0]):
            self.picker_table.selection_set(selected[0])
        count=len(self.picker_table.get_children())
        self.picker_info.set(tr(f'Widoczne pamięci: {count}. Zaznacz pozycję i kliknij Ustaw lub naciśnij Enter.') if count else
            tr('Brak pasujących pamięci. Odczytaj pamięci z radia, zaimportuj CSV w zakładce Baza i pamięci lub zmień wyszukiwanie.'))

    def choose_memory_frequency(self,event=None):
        selected=self.picker_table.selection()
        if not selected:
            self.picker_info.set(tr('Najpierw zaznacz pamięć na liście.'))
            return
        if not self.connected or self.busy:
            self.picker_info.set(tr('Połącz radio i zaczekaj na zakończenie bieżącej operacji.'))
            return
        row=self.rows.get(int(selected[0]))
        if not row or row.get('empty'):
            self.refresh_memory_picker()
            return
        self.freq_entry.set(f"{row['rx']/1e6:.6f}")
        self.setting_values.clear()
        self.fill_settings_tree()
        self.render_setting_editor()
        self.submit('recall',dict(row))
        self.busy=True
        self.picker_info.set(tr('Przywoływanie i sprawdzanie ustawień pamięci…'))

    def fill_table(self):
        self.table.delete(*self.table.get_children())
        for ch, row in sorted(self.rows.items()):
            values = (ch,tr('— pusta —'),'','','','','') if row.get('empty') else (
                ch,row['name'],f"{row['rx']/1e6:.6f}",f"{row['tx']/1e6:.6f}",row['mode'],row['filter'],tr('TAK') if row['flags'] & 1 else tr('NIE'))
            self.table.insert('', 'end', iid=str(ch), values=values)
        self.refresh_memory_picker()

    def select_memory(self, event=None):
        selected = self.table.selection()
        if not selected:
            return
        row = self.rows[int(selected[0])]
        self.memory_extra=row.get('extra')
        self.edit['channel'].set(str(row['channel']))
        if row.get('empty'):
            self.edit['name'].set('')
            return
        for key in ('name','mode','filter'):
            self.edit[key].set(str(row[key]))
        for key in ('rx','tx'):
            self.edit[key].set(f"{row[key]/1e6:.6f}")
        self.split.set(bool(row['flags'] & 1))

    def write_memory(self):
        if not self.connected or self.busy:
            messagebox.showinfo(tr('Pamięci'),tr('Połącz radio i zaczekaj na zakończenie bieżącej operacji.'))
            return
        try:
            ch = int(self.edit['channel'].get())
            changes = {'name':self.edit['name'].get(),'rx':hz_from_mhz(self.edit['rx'].get()),
                       'tx':hz_from_mhz(self.edit['tx'].get()),'mode':self.edit['mode'].get(),
                       'filt':int(self.edit['filter'].get()),'split':self.split.get(),'extra':self.memory_extra}
            build_memory(ch, **changes)
        except Exception as exc:
            messagebox.showerror(tr('Dane pamięci'),str(exc))
            return
        if messagebox.askyesno(tr('Zapis do radia'),tr(f"Nadpisać pamięć {ch}: {changes['name']}?\nRX {changes['rx']/1e6:.6f} MHz • TX {changes['tx']/1e6:.6f} MHz\n{changes['mode']} • FIL{changes['filt']} • Split: {changes['split']}\n\nPrzed zapisem powstanie kopia dotychczasowej pamięci.")):
            self.submit('write', ch, changes)
            self.busy = True

    def export_csv(self):
        path = filedialog.asksaveasfilename(initialdir=DATA,defaultextension='.csv',filetypes=[('CSV','*.csv')])
        if not path:
            return
        try:
            with open(path,'w',newline='',encoding='utf-8-sig') as file:
                writer = csv.DictWriter(file,fieldnames=['channel','name','rx_mhz','tx_mhz','mode','filter','split'],delimiter=';')
                writer.writeheader()
                for ch,row in sorted(self.rows.items()):
                    if not row.get('empty') and ch <= 99:
                        writer.writerow(dict(channel=ch,name=row['name'],rx_mhz=f"{row['rx']/1e6:.6f}",tx_mhz=f"{row['tx']/1e6:.6f}",mode=row['mode'],filter=row['filter'],split=int(bool(row['flags']&1))))
            self.status.set(tr('Zapisano CSV. Pełne kopie JSON zachowują również tony i pozostałe pola.'))
        except Exception as exc:
            messagebox.showerror(tr('Eksport'),str(exc))

    def import_csv(self):
        path = filedialog.askopenfilename(initialdir=ROOT,filetypes=[('CSV','*.csv')])
        if not path:
            return
        try:
            rows = {}
            with open(path,newline='',encoding='utf-8-sig') as file:
                for row in csv.DictReader(file,delimiter=';'):
                    ch = int(row['channel'])
                    if ch in rows or row['split'] not in ('0','1'):
                        raise ValueError(tr('Powtórzony kanał lub nieprawidłowe pole split'))
                    raw = build_memory(ch,row['name'],hz_from_mhz(row['rx_mhz']),hz_from_mhz(row['tx_mhz']),row['mode'],int(row['filter']),row['split']=='1')
                    rows[ch] = memory_decode(raw)
            self.rows = rows
            self.fill_table()
            (DATA / f'import-{stamp()}.json').write_text(json.dumps(list(rows.values()),indent=2),encoding='utf-8')
            self.status.set(tr(f'Wczytano {len(rows)} pozycji do biblioteki. Nie zmieniono pamięci radia.'))
        except Exception as exc:
            messagebox.showerror(tr('Import CSV'),str(exc))

    def clear_waterfall(self):
        self.history[:] = (8,15,30)
        self.draw_waterfall()

    def toggle_audio(self):
        if self.audio:
            self.audio.close()
            self.audio = None
            self.audio_btn.configure(text=tr('Uruchom waterfall'))
            self.audio_status.set(tr('Audio zatrzymane'))
            return
        try:
            if not self.device.get():
                raise ValueError(tr('Wybierz wejście audio radia. Jeśli nie ma USB Audio CODEC, podłącz radio i uruchom program ponownie.'))
            index = int(self.device.get().split(':',1)[0])
            self.audio = AudioInput(index)
            self.last_audio = time.monotonic()
            self.audio_btn.configure(text=tr('Zatrzymaj waterfall'))
            self.audio_status.set(tr('Przechwytywanie audio…'))
        except Exception as exc:
            self.audio=None
            self.audio_status.set(tr('BŁĄD USB AUDIO — odłącz/podłącz USB i uruchom program ponownie'))
            self.status.set(str(exc))
            logging.exception(tr('Nie udało się uruchomić audio USB'))

    def draw_waterfall(self):
        size = (max(1,self.waterfall.winfo_width()),max(1,self.waterfall.winfo_height()))
        self.photo = ImageTk.PhotoImage(Image.fromarray(self.history).resize(size))
        self.waterfall.itemconfigure(self.image_item,image=self.photo)

    def draw_audio(self, samples):
        db = spectrum(samples)
        limit = int(self.span.get())
        xs = np.linspace(0,limit,850)
        line = np.interp(xs,np.fft.rfftfreq(FFT_SIZE,1/RATE),db)
        intensity = np.clip((line-self.floor.get())/(-10-self.floor.get()),0,1)
        anchors = np.array([[8,15,30],[15,35,95],[0,115,180],[30,210,180],[250,220,75],[255,250,240]])
        positions = intensity * (len(anchors)-1)
        low = np.minimum(positions.astype(int),len(anchors)-2)
        rgb = anchors[low]*(1-(positions-low)[:,None])+anchors[low+1]*(positions-low)[:,None]
        self.history[1:] = self.history[:-1].copy()
        self.history[0] = rgb.astype(np.uint8)
        self.draw_waterfall()
        width,height = max(self.plot.winfo_width(),100),105
        self.plot.delete('all')
        for n in range(6):
            x=40+(width-50)*n/5
            self.plot.create_line(x,6,x,82,fill='#243247')
            self.plot.create_text(x,94,text=f'{limit*n/5000:g}k',fill='#becddd',font=('Segoe UI',9))
        self.plot.create_text(3,12,text='dBFS',anchor='w',fill='#becddd',font=('Segoe UI',9))
        points=[]
        for x,y in zip(np.linspace(40,width-10,850),80-np.clip((line+130)/130,0,1)*72):
            points.extend((float(x),float(y)))
        self.plot.create_line(*points,fill='#78d8e5',width=1)
        peak = float(np.max(np.abs(samples)))
        rms = float(np.sqrt(np.mean(samples**2)))
        level=20*np.log10(max(rms,1e-7))
        self.audio_status.set(f'{level:.0f} dBFS • {self.audio.backend}' + (tr(' • PRZESTEROWANIE') if peak>=.99 else '') + (tr(f' • przerwy: {self.audio.overflows}') if self.audio.overflows else ''))

    def tick(self):
        try:
            while True:
                kind,data=self.events.get_nowait()
                if kind=='state':
                    self.current=data
                    self.freq_display.configure(text=f"{data['hz']:,}".replace(',','.'))
                    self.mode_display.configure(text=tr(f"{data['mode']}    FIL{data['filter']}    •    ODCZYT Z RADIA"),fg='#4edbd0')
                elif kind=='connected':
                    self.connected=True
                    self.status.set(data)
                elif kind in ('offline','recovering'):
                    self.connected=False
                    self.connect_btn.configure(state='normal')
                    self.mode_display.configure(text=tr('ODCZYT NIEAKTUALNY • ')+(tr('PONAWIANIE') if kind=='recovering' else tr('ROZŁĄCZONO')),fg='#ff9770')
                    self.status.set(data)
                    self.settings_status.set(tr('Radio odłączone — odczyt nieaktualny'))
                    self.setting_values.clear()
                    self.setting_current.set(tr('Odczyt nieaktualny — brak połączenia'))
                    self.setting_apply.configure(state='disabled')
                    self.fill_settings_tree()
                elif kind=='settings_context':
                    self.settings_context=data
                elif kind=='settings':
                    self.busy=False
                    self.setting_values={}
                    self.setting_errors={}
                    for key,item in data.items():
                        if 'value' in item:
                            self.setting_values[key]=item['value']
                        else:
                            self.setting_errors[key]=item['error']
                    self.fill_settings_tree()
                    self.render_setting_editor()
                    count=sum('value' in item for item in data.values())
                    self.settings_status.set(tr(f'Odczytano {count}/{len(SETTINGS)} • {datetime.now():%H:%M:%S}'))
                    self.status.set(tr('Ustawienia odczytane. Nie zmieniono radia.'))
                elif kind=='setting':
                    self.busy=False
                    key,value=data
                    self.show_setting(key,value)
                    self.settings_status.set(tr('Zapis i odczyt OK: ')+tr(CATALOG[key][2]))
                    self.status.set(tr('Zmieniono ')+tr(CATALOG[key][2])+tr('. Wynik potwierdzony odczytem.'))
                elif kind=='memories':
                    self.rows={r['channel']:r for r in data}
                    self.fill_table()
                    self.busy=False
                elif kind=='memory_written':
                    self.rows[data['channel']]=data
                    self.fill_table()
                    self.busy=False
                elif kind=='recalled':
                    self.busy=False
                    self.setting_values.clear()
                    self.fill_settings_tree()
                    self.render_setting_editor()
                    self.status.set(tr('Przywołano profil pamięci i potwierdzono odczyt.'))
                    if self.memory_picker is not None and self.memory_picker.winfo_exists():
                        self.picker_info.set(self.status.get())
                elif kind=='error':
                    self.busy=False
                    self.status.set(tr('Błąd: ')+tr(data))
                    if self.memory_picker is not None and self.memory_picker.winfo_exists():
                        self.picker_info.set(self.status.get())
                    self.settings_status.set(tr('Błąd operacji — sprawdź komunikat i odśwież odczyt.'))
                else:
                    self.status.set(data)
        except queue.Empty:
            pass
        if self.audio:
            latest=None
            try:
                while True:
                    latest=self.audio.frames.get_nowait()
            except queue.Empty:
                pass
            if latest is not None:
                self.last_audio=time.monotonic()
                self.draw_audio(latest)
            elif time.monotonic()-self.last_audio>2:
                self.audio_status.set(tr('BRAK DANYCH AUDIO — sprawdź USB'))
        self.after(100,self.tick)

    def close(self):
        if self.busy:
            messagebox.showinfo(tr('Operacja w toku'),tr('Zaczekaj na zakończenie operacji pamięci.'))
            return
        if self.audio:
            self.audio.close()
        self.commands.put(('stop',()))
        self.worker.join(timeout=2)
        self.destroy()

def self_test(app):
    started = time.monotonic()
    requested = False
    settings_requested = False
    result = {}
    def check():
        nonlocal requested, settings_requested
        if app.connected and not requested:
            requested = True
            app.read_memories()
        if app.rows and not app.busy and not settings_requested:
            settings_requested=True
            app.read_settings()
        done = bool(app.rows and app.setting_values and app.audio and app.photo is not None and not app.busy)
        if done or time.monotonic()-started > 30:
            result.update(ok=done, version=VERSION, state=app.current, memories=len(app.rows),
                          audio_signal=bool(app.audio and 'USB Audio CODEC' in app.device.get() and (app.history[:,:,1]>40).any()),
                          audio_input=app.device.get(), settings=len(app.setting_values), status=app.status.get())
            (ROOT/'wynik-testu-exe.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
            app.busy=False
            app.close()
        else:
            app.after(250,check)
    app.connect()
    app.toggle_audio()
    app.after(250,check)
    return result

if __name__=='__main__':
    application=App()
    outcome={}
    if '--self-test' in sys.argv:
        def start_test():
            global outcome
            outcome=self_test(application)
        application.after(300,start_test)
    elif '--start' in sys.argv:
        application.after(300,application.connect)
        application.after(700,application.toggle_audio)
    if '--info' in sys.argv:
        application.after(1000,lambda:open_info(application))
    application.mainloop()
    if '--self-test' in sys.argv:
        sys.exit(0 if outcome.get('ok') and outcome.get('audio_signal') else 1)
