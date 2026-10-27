# ICOM-7410-PC

ICOM-7410-PC is a Windows application for local USB control of an Icom
IC-7410, memory management and an audio waterfall display. The project is
under active development.

## How It Works

The application controls the radio through a virtual serial USB port using
Icom CI-V commands and memory formats specifically implemented for the IC-7410.
Other Icom models can use different commands, addresses and data formats.
Compatibility with other models is not guaranteed.

Protocol reference: IC-7410 Instruction Manual, chapter 14, “Control commands”,
printed pages 101–108:
https://icomuk.co.uk/files/icom/PDF/productManual/IC-7410_ENG.pdf#page=108

Audio is captured separately from the radio's USB Audio CODEC and analysed
using an FFT. The waterfall displays AUDIO frequencies within the receiver
passband. It is not a wideband RF panorama or an SDR IQ display. Its usable
bandwidth depends on the radio's mode and filters.

## Current Features

- Read and set frequency, operating mode and filter over local USB.
- Colour interface, maximized window and audio waterfall.
- Read 101 memories (1–99 and P1/P2) with full local JSON backups.
- Search memories and recall the RX frequency, mode, FIL1/2/3, DATA where
  supported, and CTCSS/TSQL in FM. TX frequency and split are not recalled.
  FIL1/2/3 selects a filter slot, not a backup of its configured bandwidth.
- Edit/write individual memories 1–99 with a backup and readback verification.
- Import/export basic memory fields as CSV; JSON backups retain full fields.
  CSV does not include DATA or CTCSS, so imported entries use default values.
- 206 configuration entries, including 90 SET MODE entries, filters, CTCSS,
  DATA, audio levels, CW configuration, band registers and user band edges.
  Availability depends on the operating mode and installed radio options.
- Stale-reading indicators, read retries and CI-V reconnection. Write commands
  are not automatically replayed.
- Manual GitHub release checks in Info. No automatic downloading or installing.

## Getting Started

Run uruchom.cmd or ICOM-7410-PC\ICOM-7410-PC.exe. Keep the complete release
directory, including _internal. Turn on the radio and select the correct
COM port and baud rate. This version uses the IC-7410 CI-V address 80h.
The tested setup used COM8 at 19200 bit/s; your port number may differ.

Your USB cable/interface may require the appropriate radio or USB-to-serial
driver to be installed. The tested setup uses Silicon Labs CP210x and USB
Audio CODEC. Obtain drivers appropriate to your actual hardware from its
manufacturer. Check both the serial and audio devices in Windows.
A faulty cable, USB port or USB enumeration can interrupt both control and
audio; application reconnection cannot repair a hardware connection fault.

## Current Limitations

No transmit/PTT control or command to start antenna tuning. No PC speaker
monitoring or PC microphone audio transmission. No home-network operation,
wideband RF/IQ waterfall, complete scan control, bulk memory writing,
automatic JSON backup restoration or writing of P1/P2 memories.

The settings menu includes transmitter, VOX, BK-IN and tuner configuration,
but does not provide a transmit or start-tuning button. Enabling VOX/BK-IN or
tuner automation can affect the radio's own response to external audio, a
key or PTT; the application displays warnings for these settings.

## Planned Development

- Transmit control, including PTT and a microphone audio path.
- Starting and controlling antenna tuning.
- Communication with the radio over a home network: control, memories,
  listening and, in a later stage, remote transmission.
These are plans, not features available in this version.

## Privacy And Availability

The application does not collect any information about the user.
The application is completely free of charge.
The application does not require registration.

There is no telemetry, analytics or user-account system. Memory/settings
backups and diagnostic logs stay locally in the dane directory.
Checking for updates contacts GitHub only after you click the button.
GitHub receives normal connection information such as your IP address.
The author's website and BuyCoffee links open external services in your
browser, subject to their own policies. Donations do not unlock features.

## Technology And Building

Written in Python, with tkinter/ttk for the interface, pyserial for CI-V,
sounddevice/PortAudio for audio capture, NumPy for FFT and Pillow for images.
PyInstaller packages the Windows executable with its Python interpreter.
Users of the packaged release do not need a separate Python installation.

For source development, install Python with tkinter and requirements.txt.
Tested environment: Windows 10 Pro 22H2 x64, Python 3.14.2.

```powershell
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe app.py
```

Run buduj.cmd to execute the tests and package the EXE. Include assets and LICENSE.
Write/recall paths have simulated tests; these do not replace testing on real
hardware. CI-V reads, memory reads and the USB audio path have been hardware-tested.

## License And Author

Application source: GNU General Public License version 3 (GPL-3.0-only).
See LICENSE. Third-party libraries and artwork retain their own licenses
and notices; see THIRD_PARTY_NOTICES.txt. Provided without warranty under
the terms of the license.

ICOM-7410-PC
(C) Adam Wojcieszonek 2026
adam@eksploracja.org.pl
http://eksploracja.org.pl
