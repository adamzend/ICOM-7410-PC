"""About dialog and opt-in GitHub release checks. No telemetry or background requests."""
import json
import queue
import re
import threading
import urllib.request
import urllib.error
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from i18n import tr

VERSION='0.3.0'
REPOSITORY='https://github.com/adamzend/ICOM-7410-PC'

def repository_slug(url):
    match=re.fullmatch(r'https://github\.com/([A-Za-z0-9-]+)/([A-Za-z0-9_.-]+)/?',url.strip())
    if not match:
        raise ValueError(tr('Podaj adres https://github.com/właściciel/repozytorium'))
    return '/'.join(match.groups())

def version_tuple(tag):
    match=re.fullmatch(r'v?(\d+)\.(\d+)\.(\d+)',tag)
    return tuple(map(int,match.groups())) if match else None

def check_release(repository):
    slug=repository_slug(repository)
    request=urllib.request.Request('https://api.github.com/repos/'+slug+'/releases/latest',
        headers={'User-Agent':'ICOM-7410-PC/'+VERSION,'Accept':'application/vnd.github+json'})
    try:
        with urllib.request.urlopen(request,timeout=12) as response:
            data=json.loads(response.read(1024*1024))
    except urllib.error.HTTPError as exc:
        if exc.code==404:
            return tr('Repozytorium lub opublikowane wydanie nie jest jeszcze dostępne.'),None
        raise
    tag=str(data.get('tag_name',''))
    remote=version_tuple(tag)
    if remote is None:
        return tr('Nie można porównać wersji: ')+tag,None
    if remote>version_tuple(VERSION):
        # Construct the trusted URL instead of trusting a server-supplied link.
        return tr('Dostępna nowa wersja: ')+tag,'https://github.com/'+slug+'/releases/latest'
    return tr('Masz aktualną lub nowszą wersję: ')+VERSION,None

def open_info(app):
    existing=getattr(app,'info_window',None)
    if existing is not None and existing.winfo_exists():
        existing.lift()
        return
    window=app.info_window=tk.Toplevel(app)
    window.title('ICOM-7410-PC — Info')
    window.geometry('660x700')
    window.minsize(560,630)
    window.configure(bg='#20262d')
    window.transient(app)
    body=ttk.Frame(window,padding=20)
    body.pack(fill='both',expand=True)
    for line,font in [('ICOM-7410-PC',('Segoe UI',23,'bold')),
                      ('(C) Adam Wojcieszonek 2026',('Segoe UI',12)),
                      ('adam@eksploracja.org.pl',('Segoe UI',12)),
                      ('http://eksploracja.org.pl',('Segoe UI',12))]:
        label=ttk.Label(body,text=line,font=font,anchor='center',justify='center')
        label.pack(fill='x',pady=3)
        if line.startswith('http'):
            label.configure(cursor='hand2',foreground='#5ddad5')
            label.bind('<Button-1>',lambda e:webbrowser.open('http://eksploracja.org.pl'))
    asset=Path(__file__).resolve().parent/'assets'/'buycoffee.png'
    if asset.exists():
        window.coffee_image=ImageTk.PhotoImage(Image.open(asset).resize((406,92)))
        ttk.Button(body,image=window.coffee_image,command=lambda:webbrowser.open('https://buycoffee.to/eksploracja')).pack(pady=12)
    else:
        ttk.Button(body,text='Buy a coffee',command=lambda:webbrowser.open('https://buycoffee.to/eksploracja')).pack(pady=12)
    ttk.Label(body,text=tr('Wersja: ')+VERSION+' • GNU GPL v3.0',anchor='center').pack(fill='x',pady=5)
    for text in ['Aplikacja nie zbiera żadnych informacji o użytkowniku.',
                 'Aplikacja jest w pełni darmowa.', 'Aplikacja nie wymaga rejestracji.']:
        ttk.Label(body,text=tr(text),anchor='center',justify='center').pack(fill='x',pady=2)
    ttk.Label(body,text=tr('Lokalne kopie pamięci i dzienniki pozostają na komputerze. Sprawdzanie aktualizacji kontaktuje się z GitHubem tylko po kliknięciu; otwierane linki prowadzą do zewnętrznych serwisów.'),
              wraplength=590,justify='center',anchor='center').pack(fill='x',pady=12)
    ttk.Label(body,text=tr('Repozytorium GitHub')).pack(anchor='w')
    repository=tk.StringVar(value=REPOSITORY)
    ttk.Entry(body,textvariable=repository).pack(fill='x',pady=5)
    result=tk.StringVar(value=tr('Aktualizacje są sprawdzane wyłącznie na żądanie.'))
    events=queue.Queue()
    release_url=[None]
    actions=ttk.Frame(body)
    actions.pack(pady=8)
    def start_check():
        url=repository.get()
        try:
            repository_slug(url)
        except ValueError as exc:
            result.set(str(exc))
            return
        button.configure(state='disabled')
        release_button.configure(state='disabled')
        result.set(tr('Sprawdzanie aktualizacji…'))
        def run():
            try:
                events.put(check_release(url))
            except Exception as exc:
                events.put((tr('Nie udało się sprawdzić aktualizacji: ')+str(exc),None))
        threading.Thread(target=run,daemon=True).start()
        window.after(100,poll)
    def poll():
        if not window.winfo_exists():
            return
        try:
            message,link=events.get_nowait()
        except queue.Empty:
            window.after(100,poll)
            return
        result.set(message)
        release_url[0]=link
        button.configure(state='normal')
        release_button.configure(state='normal' if link else 'disabled')
    button=ttk.Button(actions,text=tr('Sprawdź aktualizacje'),command=start_check)
    button.pack(side='left',padx=5)
    release_button=ttk.Button(actions,text=tr('Otwórz stronę wydania'),state='disabled',
        command=lambda:webbrowser.open(release_url[0]) if release_url[0] else None)
    release_button.pack(side='left',padx=5)
    ttk.Label(body,textvariable=result,wraplength=590,justify='center',anchor='center').pack(fill='x',pady=6)
    ttk.Button(body,text=tr('Zamknij'),command=window.destroy).pack(pady=8)
