# python -m uvicorn main:app --port 5000

import socketio
import asyncio
import threading
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import os
import base64

# lista de clienti si app-urile pe care le-au descarcat
app_list = {}
# lista cu toate aplicatiile
all_apps = []

# instantiez server-ul concurent
sio = socketio.AsyncServer(async_mode='asgi')


# functie care notifica clientii ca o aplicatie s-a modificat
async def notify_update(path):
    print(path)
    path=path.replace("~", "")
    filename = os.path.basename(os.path.normpath(path))

    # pentru fiecare client verific daca a descarcat sau nu aplicatia si trimitem update
    for client in app_list[filename]:
        await bundle_app(filename, client, update=True)

    print("sucesfully sent app update")

# variabile auxiliare
# variabila care notifica thread-ul daca trebuie sa fie inchis sau nu
shutdown_flag = False
thread = None


# clasa care monitorizeaza folder-ul de aplicatii si
# notifica atunci cand un fisier e modificat
class Watcher:
    DIRECTORY_TO_WATCH = "./static"

    def __init__(self):
        self.observer = Observer()

    def run(self):
        global shutdown_flag

        event_handler = Handler()
        self.observer.schedule(event_handler, self.DIRECTORY_TO_WATCH, recursive=True)
        self.observer.start()
        try:
            while True:
                # verific daca thread-ul trebuie inchis sau nu
                time.sleep(1)
                if shutdown_flag:
                    break
        except:
            self.observer.stop()

        self.observer.stop()
        self.observer.join()

# handler de evenimente
class Handler(FileSystemEventHandler):

    @staticmethod
    def on_any_event(event):
        if event.is_directory:
            return None

        elif event.event_type == 'modified':
            asyncio.run(notify_update(event.src_path))

# functia constructor watchdog
async def watchdog():
    global shutdown_flag

    w = Watcher()
    w.run()

def initialize_watchdog():
    global thread, app_list, all_apps

# daca e fisier se da toate numele fisierelor
    apps = [f for f in os.listdir('./static') if os.path.isfile(os.path.join('./static', f))]

# initializare lista clienti
    for app in apps:
        app_list[app] = []

    all_apps = apps
    os.environ['all_apps'] = str(all_apps)

# initializare thread cu monitorul de fisiere
    thread = threading.Thread(target=asyncio.run, args=(watchdog(),))
    thread.start()

# functie de oprire monitor
def shutdown_watchdog():
    global shutdown_flag, thread

    shutdown_flag = True

    thread.join()


# functia care trimite update la clienti
async def bundle_app(app_name, sid, update=False):
    try:
        data = open(f"./static/{app_name}", "r").read()

        # encodez fisierul
        encoded_data = base64.b64encode(data.encode())

        # trimit update-ul
        await sio.emit("app_download", {"app_data": encoded_data, "app_name": app_name, "update": update}, sid)
    except Exception as e:
        print(e)


# initializez server-ul
app = socketio.ASGIApp(sio, on_startup=initialize_watchdog, on_shutdown=shutdown_watchdog)

# evenimentul de connect
@sio.event
async def connect(sid, environ):
    print("connect ", sid)
    await sio.emit('app_list', {"apps": all_apps}, room=sid)

# eveniment de test
@sio.event
async def message(sid, data):
    print("message ", data)

# disconnect
@sio.event
def disconnect(sid):
    print('disconnect ', sid)

# eveniment in care clientul cere descarea unei aplicatii
@sio.event
async def download(sid, data):
    print("received app download request")
    app_list[data["app_name"]].append(sid)
    await bundle_app(data["app_name"], sid)
    print("sucessfully sent app download")