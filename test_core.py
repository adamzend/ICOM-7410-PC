import unittest
from unittest.mock import patch
import queue
import time
from decimal import InvalidOperation
import numpy as np
from radio import encode_bcd, decode_bcd, extract_frames, memory_decode, Radio, encode_band, decode_band
from audio_engine import spectrum, RATE, FFT_SIZE
from app import build_memory, hz_from_mhz, Worker
from settings_catalog import CATALOG, choices_for

class CoreTests(unittest.TestCase):
    def test_real_frequency_response(self):
        self.assertEqual(decode_bcd(bytes.fromhex('0030942600')),26943000)
        self.assertEqual(encode_bcd(26943000,5).hex(),'0030942600')
        self.assertEqual(hz_from_mhz('26,943001'),26943001)
        for invalid in ('NaN','Infinity','60.000001','0','1.0000001'):
            with self.assertRaises((ValueError,InvalidOperation)):
                hz_from_mhz(invalid)

    def test_bad_bcd(self):
        with self.assertRaises(ValueError):
            decode_bcd(b'\xfa')

    def test_fragmented_echo_and_response(self):
        frames,left=extract_frames(bytes.fromhex('00 fe fe 80 e0 03 fd fe'))
        self.assertEqual(frames,[bytes.fromhex('80e003')])
        frames,left=extract_frames(left+bytes.fromhex('fe e0 80 03 00 30 94 26 00 fd'))
        self.assertEqual(frames,[bytes.fromhex('e080030030942600')])
        self.assertEqual(left,b'')

    def test_memory_real_packet(self):
        raw=bytes.fromhex('000201000096260002020000000885000885000018270002010000000885000885434220312020202020')
        row=memory_decode(raw)
        self.assertEqual(row['name'],'CB 1')
        self.assertEqual(row['rx'],26960000)
        self.assertEqual(row['tx'],27180000)
        self.assertEqual(row['flags'],1)
        modified=build_memory(2,'TEST',14200000,14205000,'USB',2,True,raw)
        self.assertEqual(modified[10:18],raw[10:18])
        self.assertEqual(modified[25:33],raw[25:33])
        self.assertEqual(memory_decode(modified)['tx'],14205000)
        self.assertTrue(memory_decode(bytes.fromhex('0099ff'))['empty'])

    def test_memory_validation(self):
        with self.assertRaises(ValueError):
            build_memory(100,'TEST',14200000,14200000,'USB',2,False)
        with self.assertRaises(ValueError):
            build_memory(1,'ZA DŁUGA NAZWA',14200000,14200000,'USB',2,False)
        raw=build_memory(1,'TEST',14200000,14200000,'USB',2,False)
        self.assertEqual(len(raw),42)
        self.assertEqual(raw[10:12],b'\0\0')

    def test_fft_frequency_and_level(self):
        # A bin-centered sinusoid, amplitude 0.5: -6.0206 dBFS peak.
        frequency=85*RATE/FFT_SIZE
        samples=.5*np.sin(2*np.pi*frequency*np.arange(FFT_SIZE)/RATE)
        result=spectrum(samples)
        self.assertEqual(int(np.argmax(result)),85)
        self.assertAlmostEqual(float(result[85]),-6.0206,places=2)
        self.assertTrue(np.isfinite(spectrum(np.zeros(FFT_SIZE))).all())

    def test_setting_wire_format_and_verification(self):
        radio=Radio.__new__(Radio)
        sent=[]
        def exchange(payload,prefix=None,ack=False):
            sent.append(payload)
            return b'\xfb' if ack else bytes.fromhex('14020255')
        radio.exchange=exchange
        self.assertEqual(radio.write_setting('rf',255),255)
        self.assertEqual(sent,[bytes.fromhex('14020255'),bytes.fromhex('1402')])
        with self.assertRaises(ValueError):
            radio.write_setting('rf',256)
        radio.exchange=lambda *a,**k: b'\xfb' if k.get('ack') else bytes.fromhex('14020128')
        with self.assertRaises(RuntimeError):
            radio.write_setting('rf',255)

    def test_collision_resynchronization(self):
        data=bytes.fromhex('fe fe 80 e0 03 fc fc fe fe fe e0 80 03 00 30 94 26 00 fd')
        frames,left=extract_frames(data)
        self.assertEqual(frames,[bytes.fromhex('e080030030942600')])
        self.assertEqual(left,b'')

    def test_reads_retry_but_writes_never_replay(self):
        radio=Radio.__new__(Radio)
        radio.read_retries=0
        with patch.object(radio,'_exchange_once',side_effect=[TimeoutError(),b'\x03\0\0\0\0\0']) as call:
            self.assertEqual(radio.exchange(b'\x03')[0],3)
            self.assertEqual(call.call_count,2)
        with patch.object(radio,'_exchange_once',side_effect=TimeoutError()) as call:
            with self.assertRaises(TimeoutError):
                radio.exchange(bytes.fromhex('14020020'),ack=True)
            self.assertEqual(call.call_count,1)

    def test_filter_width_maps(self):
        self.assertEqual(choices_for('bandwidth','AM')[44],'9000 Hz')
        self.assertEqual(choices_for('bandwidth','USB')[28],'2400 Hz')
        self.assertEqual(choices_for('bandwidth','RTTY')[31],'2700 Hz')
        self.assertEqual(choices_for('bandwidth','FM'),{})
        self.assertEqual(choices_for('agc_time','AM')[8],'3 s')

    def test_new_setting_formats(self):
        radio=Radio.__new__(Radio)
        for key,value,response,payload in [
            ('tone',885,'1b00000885','1b00000885'),
            ('data',258,'1a060102','1a060102'),
            ('set_0012',-100,'1a05001200100001','1a05001200100001'),
            ('set_0045',1020,'1a0500451020','1a0500451020'),
            ('set_0070',60,'1a05007060','1a05007060')]:
            with self.subTest(key=key):
                sent=[]
                def exchange(data,prefix=None,ack=False):
                    sent.append(data)
                    return b'\xfb' if ack else bytes.fromhex(response)
                radio.exchange=exchange
                self.assertEqual(radio.write_setting(key,value),value)
                self.assertEqual(sent[0].hex(),payload)
        self.assertEqual(len([k for k in CATALOG if k.startswith('set_')]),90)

    def test_band_roundtrip(self):
        text='14.200000;USB;2;1;1;88.5;67.0'
        self.assertEqual(decode_band(encode_band(text)),text)
        with self.assertRaises(ValueError):
            encode_band('14.2;USB;4;1;1;88.5;67.0')

    def test_audio_fallback_same_input_only(self):
        from audio_engine import AudioInput
        from unittest.mock import MagicMock
        devices=[dict(name='USB Audio CODEC',hostapi=0,max_input_channels=1),
                 dict(name='PC microphone',hostapi=1,max_input_channels=1),
                 dict(name='USB Audio CODEC',hostapi=1,max_input_channels=1)]
        good=MagicMock()
        with patch('audio_engine.sd.query_devices',side_effect=lambda i=None: devices if i is None else devices[i]), \
             patch('audio_engine.sd.query_hostapis',side_effect=lambda i: {'name':['MME','Windows WASAPI'][i]}), \
             patch('audio_engine.sd.InputStream',side_effect=[RuntimeError('MME error'),good]) as factory:
            audio=AudioInput(0)
            self.assertEqual([call.kwargs['device'] for call in factory.call_args_list],[0,2])
            self.assertEqual(audio.backend,'Windows WASAPI')
            audio.close()
            good.close.assert_called_once()

    def test_edges_roundtrip(self):
        from radio import encode_edges, decode_edges
        self.assertEqual(decode_edges(encode_edges('1.810000;1.999999')), '1.810000;1.999999')
        self.assertEqual(decode_edges(b'\xff'), '')
        with self.assertRaises(ValueError):
            encode_edges('14;7')

    def test_advanced_memory_roundtrip(self):
        extra=dict(tx_mode='FM',tx_filt=3,rx_data=1,tx_data=0,rx_tone=1,tx_tone=2,
                   rx_ctcss=885,rx_tsql=670,tx_ctcss=1000,tx_tsql=1230,selected=1)
        raw=build_memory(2,'TEST',14200000,29500000,'USB',2,True,extra=extra)
        self.assertEqual(memory_decode(raw)['extra'],extra)
        extra['rx_data']=2
        with self.assertRaises(ValueError):
            build_memory(2,'TEST',14200000,29500000,'USB',2,True,extra=extra)

    def test_worker_automatic_reconnect(self):
        class FakeRadio:
            calls=0
            def __init__(self,*args): pass
            def close(self): pass
            def state(self):
                FakeRadio.calls+=1
                if FakeRadio.calls==1:
                    raise TimeoutError('symulowana chwilowa utrata')
                return {'hz':14200000,'mode':'USB','filter':2}
        commands,events=queue.Queue(),queue.Queue()
        with patch('app.Radio',FakeRadio):
            worker=Worker(commands,events)
            worker.start()
            commands.put(('connect',('COM8',19200)))
            seen=[]
            deadline=time.monotonic()+5
            try:
                while time.monotonic()<deadline:
                    try:
                        kind,data=events.get(timeout=.1)
                        seen.append(kind)
                        if kind=='connected': break
                    except queue.Empty: pass
            finally:
                commands.put(('stop',()))
                worker.join(timeout=2)
        self.assertIn('recovering',seen)
        self.assertIn('connected',seen)
        self.assertFalse(worker.is_alive())

if __name__=='__main__':
    unittest.main(verbosity=2)
