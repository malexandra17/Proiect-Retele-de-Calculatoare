import asyncio
import socketio
import threading
import signal
import sys
import time
import base64

# variabile auxiliare
shutdown_flag = False
all_aps = []
client_name = ""

def signal_handler(sig, frame):
    global shutdown_flag

    shutdown_flag = True
    sys.exit(0)

# functie care instaleaza o aplicatie
def install_app(app_data, app_name):
    app_data = base64.b64decode(app_data).decode()

    f = open(f"./apps/{app_name}", "w+")

    f.write(app_data)
    f.close()

    print("sucessfully installed app")

# initializez client socket
sio = socketio.AsyncClient()

# eveniment conectare
@sio.event
async def connect():
    print('connection established')

# eveniment test
@sio.event
async def message(data):
    print('message received with ', data)
    await sio.emit('my response', {'response': 'my response'})

# evenimentul de deconectare
@sio.event
async def disconnect():
    print('disconnected from server')

# eveniment descarcare aplicatie
@sio.event
async def app_download(data):
    if data["update"] == True:
        print("app update received")
    else:
        print("app download received")
    print("installing app...")
    install_app(data["app_data"], data["app_name"])

# evenimentul in care primesc lista de aplicatii
@sio.event
async def app_list(data):
    global all_apps
    apps = data['apps']

    all_apps = apps

    for idx, app in enumerate(apps):
        print(f"{idx}. {app}")

# functie care cere descarcarea de aplicatie la server
async def request_app_download(all_apps, client_name, app_no):
    try:
        app_name = all_apps[app_no]

        await sio.emit("download", {"app_name": app_name, "client_name": client_name})
        print("requested app download...")
    except Exception as e:
        print(e)
        print("app doesn't exist!")


async def main():
    global shutdown_flag

    await sio.connect('http://localhost:5000')

    while not shutdown_flag:
        await sio.sleep(1)

    await sio.disconnect()

if __name__ == '__main__':
    client_name = input("input client name: ")

    signal.signal(signal.SIGINT, signal_handler)

    thread = threading.Thread(target=asyncio.run, args=(main(),))
    thread.start()
    time.sleep(5)
    while True:
        x = int(input("choose number of app to download: "))
        asyncio.run(request_app_download(all_apps, client_name, x))
        time.sleep(5)

