from i18n import tr
"""Input-only USB audio capture and calibrated relative dBFS FFT."""
import queue
import logging
import numpy as np
import sounddevice as sd

RATE = 48000
FFT_SIZE = 4096

def spectrum(samples):
    samples = np.asarray(samples, dtype=np.float32).reshape(-1)
    if len(samples) != FFT_SIZE:
        raise ValueError(tr('Nieprawidłowy rozmiar FFT'))
    window = np.hanning(FFT_SIZE)
    amplitude = np.abs(np.fft.rfft((samples - samples.mean()) * window)) * 2 / window.sum()
    return 20 * np.log10(np.maximum(amplitude, 1e-7))

def input_devices():
    apis=sd.query_hostapis()
    devices=[(i, d['name']+' ['+apis[d['hostapi']]['name']+']')
             for i,d in enumerate(sd.query_devices()) if d['max_input_channels'] > 0]
    return sorted(devices,key=lambda item: ('WASAPI' not in item[1],item[0]))

class AudioInput:
    def __init__(self, device):
        self.frames = queue.Queue(maxsize=3)
        self.overflows = 0
        self.stream=None
        devices=sd.query_devices()
        selected=sd.query_devices(device)
        # Only fall back to another API for the same named input, never a PC microphone.
        candidates=[device]+[i for i,d in enumerate(devices)
            if i!=device and d['max_input_channels']>0
            and d['name'].strip()==selected['name'].strip()
            and sd.query_hostapis(d['hostapi'])['name'] in ('Windows WASAPI','MME','Windows DirectSound')]
        failures=[]
        for candidate in candidates:
            stream=None
            try:
                stream=sd.InputStream(device=candidate,channels=1,samplerate=RATE,
                    dtype='float32',blocksize=FFT_SIZE,callback=self.callback)
                stream.start()
                self.stream=stream
                self.device=candidate
                self.backend=sd.query_hostapis(devices[candidate]['hostapi'])['name']
                break
            except Exception as exc:
                if stream is not None:
                    stream.close()
                failures.append(str(exc))
                logging.warning('Audio input %s: %s',candidate,exc)
        if self.stream is None:
            raise RuntimeError(tr('Nie można otworzyć wejścia USB audio. Zamknij inne programy audio, '
                'odłącz i podłącz USB, a następnie uruchom program ponownie. '
                'Sterowanie CI-V może nadal działać. Szczegóły zapisano w dane/program.log. ')
                + ' | '.join(failures))

    def callback(self, data, frames, timing, status):
        if status:
            self.overflows += 1
        try:
            self.frames.put_nowait(data[:, 0].copy())
        except queue.Full:
            pass

    def close(self):
        self.stream.stop()
        self.stream.close()
