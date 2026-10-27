from i18n import tr
"""IC-7410 CI-V. No transmit/PTT commands are implemented."""
import time
import logging
from decimal import Decimal
import serial
from settings_catalog import CATALOG, META, choices_for, TONES

MODES = {0: 'LSB', 1: 'USB', 2: 'AM', 3: 'CW', 4: 'RTTY', 5: 'FM', 7: 'CW-R', 8: 'RTTY-R'}

def encode_band(text):
    fields=text.split(';')
    if len(fields)!=7:
        raise ValueError(tr('Rejestr wymaga 7 pól oddzielonych średnikiem; zobacz opis.'))
    mhz,mode,filt,data,tone,ctcss,tsql=[f.strip() for f in fields]
    frequency=Decimal(mhz.replace(',','.'))*1000000
    if not frequency.is_finite() or frequency!=int(frequency) or not 30000<=frequency<=60000000:
        raise ValueError(tr('Nieprawidłowa częstotliwość rejestru'))
    filt,data,tone=int(filt),int(data),int(tone)
    if mode not in MODES.values() or filt not in (1,2,3) or data not in (0,1) or tone not in (0,1,2):
        raise ValueError(tr('Nieprawidłowa emisja, filtr, DATA lub ton'))
    tones=[Decimal(t.replace(',','.'))*10 for t in (ctcss,tsql)]
    if any(t not in TONES for t in tones):
        raise ValueError(tr('Nieobsługiwana częstotliwość CTCSS'))
    code=next(k for k,v in MODES.items() if v==mode)
    return encode_bcd(int(frequency),5)+bytes([code,filt,data,tone])+b''.join(encode_bcd(int(t),3,False) for t in tones)

def decode_band(data):
    if len(data)!=15 or data[5] not in MODES:
        raise ValueError(tr('Nieznany format rejestru pasma'))
    return f'{decode_bcd(data[:5])/1e6:.6f};{MODES[data[5]]};{data[6]};{data[7]};{data[8]};{decode_bcd(data[9:12],False)/10:.1f};{decode_bcd(data[12:15],False)/10:.1f}'

def encode_edges(text):
    parts=text.split(';')
    if len(parts)!=2:
        raise ValueError(tr('Podaj dwie granice MHz oddzielone średnikiem'))
    values=[Decimal(p.strip().replace(',','.'))*1000000 for p in parts]
    if any(not v.is_finite() or v!=int(v) for v in values) or not 0<=values[0]<values[1]<=60000000:
        raise ValueError(tr('Granice muszą rosnąć i mieścić się w 0–60 MHz, dokładność 1 Hz'))
    return encode_bcd(int(values[0]),5)+b'\x2d'+encode_bcd(int(values[1]),5)

def decode_edges(data):
    if data==b'\xff':
        return ''
    if len(data)!=11 or data[5]!=0x2d:
        raise ValueError(tr('Nieznany format granic pasma'))
    return f'{decode_bcd(data[:5])/1e6:.6f};{decode_bcd(data[6:])/1e6:.6f}'

def decode_bcd(data, little=True):
    if any((v & 15) > 9 or (v >> 4) > 9 for v in data):
        raise ValueError(tr('Niepoprawne dane BCD z radia'))
    return int((data[::-1] if little else data).hex() or '0')

def encode_bcd(value, length, little=True):
    if not isinstance(value, int) or not 0 <= value < 10**(length*2):
        raise ValueError(tr('Wartość poza zakresem BCD'))
    data = bytes.fromhex(f'{value:0{length*2}d}')
    return data[::-1] if little else data

def extract_frames(buffer):
    frames = []
    while True:
        start = buffer.find(b'\xfe\xfe')
        if start < 0:
            return frames, buffer[-1:] if buffer.endswith(b'\xfe') else b''
        buffer = buffer[start:]
        # CI-V may contain extra preamble bytes or an interrupted/collided frame.
        while buffer.startswith(b'\xfe\xfe\xfe'):
            buffer = buffer[1:]
        end = buffer.find(b'\xfd', 2)
        newer = buffer.find(b'\xfe\xfe', 2)
        if newer >= 0 and (end < 0 or newer < end):
            buffer = buffer[newer:]
            continue
        if end < 0:
            return frames, buffer if len(buffer) < 4096 else b''
        frame, buffer = buffer[2:end], buffer[end+1:]
        if len(frame) >= 3:
            frames.append(frame)

def memory_decode(raw):
    if len(raw) < 3:
        raise ValueError(tr('Niepełna odpowiedź pamięci'))
    number = decode_bcd(raw[:2], False)
    if raw[2:] == b'\xff':
        return {'channel': number, 'empty': True, 'raw': raw.hex()}
    if len(raw) != 42:
        raise ValueError(tr(f'Nieznany format pamięci: {len(raw)} bajtów'))
    return {'channel': number, 'empty': False, 'name': raw[33:42].decode('ascii', errors='replace').rstrip(),
            'rx': decode_bcd(raw[3:8]), 'tx': decode_bcd(raw[18:23]),
            'mode': MODES.get(raw[8], f'0x{raw[8]:02X}'), 'filter': raw[9],
            'flags': raw[2], 'raw': raw.hex(),
            'extra': {'tx_mode':MODES.get(raw[23],'USB'),'tx_filt':raw[24],
                      'rx_data':raw[10],'tx_data':raw[25],'rx_tone':raw[11],'tx_tone':raw[26],
                      'rx_ctcss':decode_bcd(raw[12:15],False),'rx_tsql':decode_bcd(raw[15:18],False),
                      'tx_ctcss':decode_bcd(raw[27:30],False),'tx_tsql':decode_bcd(raw[30:33],False),
                      'selected':int(bool(raw[2]&0x10))}}

class Radio:
    def __init__(self, port='COM8', baud=19200, address=0x80):
        self.address = address
        self.port = serial.Serial(port=None, baudrate=baud, timeout=.04, write_timeout=.5)
        self.port.dtr = False
        self.port.rts = False
        self.port.port = port
        self.port.open()
        self.port.reset_input_buffer()
        self.buffer = b''
        self.last_request = 0
        self.read_retries = 0

    def close(self):
        self.port.close()

    def exchange(self, payload, prefix=None, ack=False):
        # Retry only reads. An unacknowledged write must never be silently replayed.
        for attempt in range(1 if ack else 3):
            try:
                return self._exchange_once(payload,prefix,ack)
            except TimeoutError:
                if ack or attempt == 2:
                    raise
                self.read_retries += 1
                time.sleep(.08 + attempt*.07)

    def _exchange_once(self, payload, prefix, ack):
        delay=.025-(time.monotonic()-self.last_request)
        if delay>0:
            time.sleep(delay)
        # Drain completed old/unsolicited frames without discarding partial frames.
        if self.port.in_waiting:
            self.buffer += self.port.read(self.port.in_waiting)
        _,self.buffer=extract_frames(self.buffer)
        self.port.write(bytes([0xfe, 0xfe, self.address, 0xe0]) + payload + b'\xfd')
        self.last_request=time.monotonic()
        deadline, trace = time.monotonic() + 1.0, bytearray()
        while time.monotonic() < deadline:
            chunk=self.port.read(max(1, self.port.in_waiting))
            trace.extend(chunk)
            self.buffer += chunk
            frames, self.buffer = extract_frames(self.buffer)
            for frame in frames:
                if frame[:2] != bytes([0xe0, self.address]):
                    continue
                body = frame[2:]
                if body == b'\xfa':
                    raise RuntimeError(tr('Radio odrzuciło komendę (NG)'))
                if ack and body == b'\xfb':
                    return body
                if not ack and body.startswith(prefix if prefix is not None else payload[:1]):
                    return body
        logging.warning('CI-V timeout request=%s received=%s',payload.hex(' '),bytes(trace[-1024:]).hex(' '))
        raise TimeoutError(tr('Brak odpowiedzi CI-V; odczyt będzie ponowiony. Sprawdź radio/USB, jeśli problem trwa.'))

    def state(self):
        freq = self.exchange(b'\x03')
        mode = self.exchange(b'\x04')
        if len(freq) != 6 or len(mode) < 3:
            raise ValueError(tr('Niepełne dane częstotliwości/emisji'))
        self.mode=MODES.get(mode[1], f'0x{mode[1]:02X}')
        return {'hz': decode_bcd(freq[1:]), 'mode': self.mode, 'filter': mode[2]}

    def tune(self, hz):
        if not 30000 <= hz <= 60000000:
            raise ValueError(tr('Zakres odbioru: 0,03–60 MHz'))
        self.exchange(b'\x05' + encode_bcd(hz, 5), ack=True)
        result = self.state()
        if result['hz'] != hz:
            raise RuntimeError(tr('Radio nie potwierdziło zadanej częstotliwości'))
        return result

    def set_mode(self, mode, filt):
        code = next(k for k, v in MODES.items() if v == mode)
        if filt not in (1, 2, 3):
            raise ValueError(tr('Nieprawidłowy filtr'))
        self.exchange(bytes([6, code, filt]), ack=True)
        result = self.state()
        if result['mode'] != mode or result['filter'] != filt:
            raise RuntimeError(tr('Radio nie potwierdziło emisji/filtra'))
        return result

    def read_memory(self, channel):
        if not 1 <= channel <= 101:
            raise ValueError(tr('Numer pamięci poza zakresem'))
        prefix = b'\x1a\x00' + encode_bcd(channel, 2, False)
        return memory_decode(self.exchange(prefix, prefix)[2:])

    def recall_profile(self, row):
        """Apply the RX profile, with readback after each write; never store a memory or key TX."""
        mode, filt, hz = row['mode'], row['filter'], row['rx']
        extra = row.get('extra')
        if row.get('empty') or mode not in MODES.values() or filt not in (1,2,3) or not 30000<=hz<=60000000:
            raise ValueError('Invalid memory profile')
        if not extra or any(k not in extra for k in ('rx_data','rx_tone','rx_ctcss','rx_tsql')):
            raise ValueError('Memory lacks DATA/CTCSS fields. Read memories from the radio again.')
        if extra['rx_data'] not in (0,1) or extra['rx_tone'] not in (0,1,2) or any(extra[k] not in TONES for k in ('rx_ctcss','rx_tsql')):
            raise ValueError('Invalid DATA/CTCSS memory fields')
        if mode not in ('LSB','USB','AM','FM') and extra['rx_data']:
            raise ValueError('DATA is not available in this mode')
        steps=[]
        try:
            self.tune(hz)
            steps.append('frequency')
            self.set_mode(mode,filt)
            steps.append('mode/filter')
            if mode in ('LSB','USB','AM','FM'):
                self.write_setting('data',256+filt if extra['rx_data'] else 0)
                steps.append('DATA')
            # CTCSS flags apply to FM; do not send unsupported flags in other modes.
            if mode=='FM':
                self.write_setting('tone',extra['rx_ctcss'])
                self.write_setting('tsql',extra['rx_tsql'])
                self.write_setting('tone_on',0)
                self.write_setting('tsql_on',0)
                if extra['rx_tone']:
                    self.write_setting('tone_on' if extra['rx_tone']==1 else 'tsql_on',1)
                for key,expected in [('tone',extra['rx_ctcss']),('tsql',extra['rx_tsql']),
                                     ('tone_on',int(extra['rx_tone']==1)),('tsql_on',int(extra['rx_tone']==2))]:
                    if self.read_setting(key)!=expected:
                        raise RuntimeError('CTCSS readback mismatch')
                steps.append('CTCSS/TSQL')
            result=self.state()
            if (result['hz'],result['mode'],result['filter'])!=(hz,mode,filt):
                raise RuntimeError('Profile readback mismatch')
            return result
        except Exception as exc:
            logging.error('Memory recall stopped after %s: %s',steps,exc)
            raise RuntimeError('Memory recall incomplete; some parameters may have changed. Refresh the radio state. '+str(exc)) from exc

    def read_setting(self, key):
        spec = CATALOG[key]
        prefix = bytes.fromhex(spec[3])
        data = self.exchange(prefix, prefix)[len(prefix):]
        codec=META[key]['codec']
        if codec=='band':
            return decode_band(data)
        if codec=='edges':
            return decode_edges(data)
        if codec=='text':
            return data.decode('ascii').rstrip()
        if codec.startswith('bcd'):
            if len(data)!=int(codec[-1]):
                raise ValueError(tr(f'Niepełny odczyt {key}: {data.hex()}'))
            value=decode_bcd(data,False)
        elif codec=='data':
            if len(data)!=2 or data[0] not in (0,1):
                raise ValueError(tr('Niepoprawny odczyt DATA'))
            value=0 if data[0]==0 else 256+data[1]
        elif codec=='offset':
            if len(data)!=4 or data[3] not in (0,1):
                raise ValueError(tr('Niepoprawny odczyt przesunięcia'))
            value=decode_bcd(data[:3])//10 * (-1 if data[3] else 1)
        else:
            if len(data)!=1:
                raise ValueError(tr('Niepełny odczyt przełącznika'))
            value = data[0]
        self.validate_setting(key,value)
        return value

    def validate_setting(self,key,value):
        meta=META[key]
        if meta['codec']=='band':
            encode_band(value)
            return
        if meta['codec']=='edges':
            encode_edges(value)
            return
        if meta['codec']=='text':
            if not isinstance(value,str) or len(value)>70 or any(not(c.isascii() and (c.isalnum() or c in ' /?,.@^*')) for c in value):
                raise ValueError(tr('Tekst CW: do 70 znaków ASCII, litery/cyfry oraz spacja / ? , . @ ^ *'))
            return
        choices=choices_for(key,getattr(self,'mode','USB'))
        if not isinstance(value,int) or (choices is not None and value not in choices) or (choices is None and not meta['limits'][0]<=value<=meta['limits'][1]):
            raise ValueError(tr('Wartość niedostępna dla tego ustawienia/emisji'))

    def write_setting(self, key, value):
        spec = CATALOG[key]
        self.validate_setting(key,value)
        codec=META[key]['codec']
        if codec=='band':
            encoded=encode_band(value)
        elif codec=='edges':
            encoded=encode_edges(value)
        elif codec.startswith('bcd'):
            encoded=encode_bcd(value,int(codec[-1]),False)
        elif codec=='text':
            encoded=value.ljust(70).encode('ascii')
        elif codec=='data':
            encoded=b'\x00\x00' if value==0 else bytes([1,value-256])
        elif codec=='offset':
            encoded=encode_bcd(abs(value)*10,3)+bytes([int(value<0)])
        else:
            encoded=bytes([value])
        self.exchange(bytes.fromhex(spec[3])+encoded, ack=True)
        actual = self.read_setting(key)
        matches=encode_band(actual)==encode_band(value) if codec=='band' else (encode_edges(actual)==encode_edges(value) if codec=='edges' else actual==value)
        if not matches:
            raise RuntimeError(tr(f'Radio zwróciło {actual} zamiast {value}. Odśwież ustawienia.'))
        return actual

    def write_memory(self, raw):
        parsed = memory_decode(raw)
        if not 1 <= parsed['channel'] <= 99:
            raise ValueError(tr('Zapis obsługuje pamięci 1–99'))
        self.exchange(b'\x1a\x00' + raw, ack=True)
        actual = self.read_memory(parsed['channel'])
        if actual['raw'] != raw.hex():
            raise RuntimeError(tr('Odczyt po zapisie różni się od wysłanych danych; sprawdź pamięć'))
        return actual
