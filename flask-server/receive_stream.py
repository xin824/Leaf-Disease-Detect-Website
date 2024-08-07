import asyncio
import websockets
from io import BytesIO
from PIL import Image, UnidentifiedImageError
import os
from datetime import datetime
import control
from config import app
import subprocess
import signal

Clients= set()
device_id_directory = 'device_ip.txt'
image_directory = "../plant/build/image"
image_directory2 = "../plant/public/image"
if not os.path.exists(image_directory):
    os.makedirs(image_directory)
    
def read_device_ip():
    lines = []
    with open(device_id_directory, 'r', encoding = 'utf-8') as file:
        for line in file:
            line = line.strip()
            lines.append(line)
    return lines

def read_model_result(lines):
    class_names = ['blight','citrus' ,'healthy', 'measles', 'mildew', 'mite', 'mold', 'rot', 'rust', 'scab', 'scorch', 'spot', 'virus']
    lines_array = lines.splitlines()
    print(lines_array)
    for line in lines_array:
        if(line in class_names):
            return line
    return 'No leaf'

def add_device_ip(new_ip):
    with open(device_id_directory, 'a', encoding = 'utf-8') as file:
        file.write(new_ip + '\n')

def is_valid_image(image_bytes):
    try:
        Image.open(BytesIO(image_bytes))
        return True
    except UnidentifiedImageError:
        print("image invalid")
        return False

async def broadcast():
    while True:
        for ws in Clients:
            await ws.send("ping")
        await asyncio.sleep(5)

async def dir_check(path):
    if not os.path.exists(path):
        os.makedirs(path)
        print('add new folder: ', path)

async def handle_disconnect(ip_address):
    file_path_new = os.path.join(image_directory, ip_address, f"new.jpg")
    image = Image.open(file_path_new)
    image = image.resize((128*3, 128*3), Image.LANCZOS)
    
    path = os.path.join(image_directory, ip_address)
    await dir_check(path)
    for i in range(60):
        file_path = os.path.join(image_directory, ip_address, f"{i}.jpg")
        image.save(file_path)
        
    path = os.path.join(image_directory2, ip_address)
    await dir_check(path)
    for i in range(60):
    
        file_path = os.path.join(image_directory2, ip_address, f"{i}.jpg")
        image.save(file_path)
        
    with app.app_context():
        control.set_plant_disconnect(ip_address)

async def handle_connection(websocket, path):
    last_saved_time = datetime.now()
    connected_clients = set()
    Clients.add(websocket)
    
    ''' read previously connected devices '''
    if not connected_clients:
        with open(device_id_directory, 'r', encoding = 'utf-8') as file:
        
            for line in file:
                line = line.strip()
                connected_clients.add(line)
    ip_address = websocket.remote_address[0]
    
    ''' add a column to the website and add a new image folder '''
    if(ip_address not in connected_clients):
        connected_clients.add(ip_address)
        with app.app_context():
            new_plant = control.add_plant(ip_address)
            add_device_ip(ip_address)
        print('add new device: ', ip_address)
        path = os.path.join(image_directory, ip_address)
        folder_path = os.path.dirname(path)
        os.makedir(folder_path)
        print('add new image folder: ', ip_address)
    
    ''' set this device's icon to connect '''
    with app.app_context():
        control.set_plant_connect(ip_address)
    print(ip_address, 'connect')
    
    folder_path = os.path.join(image_directory, ip_address)
    await dir_check(folder_path)
    
    while True:
        try:
            message = await websocket.recv()
            
            
            ''' determine whether the message is a image '''
            if len(message) > 5000:
                if is_valid_image(message):
                    current_time = datetime.now()
                    time_diff = (current_time - last_saved_time).total_seconds()
                    time_thre = 3
                    ''' save a image every five seconds '''
                    if time_diff >= time_thre: 
                        
                        file_path_new = os.path.join(image_directory, ip_address, f"new.jpg")
                        save_path_new = os.path.join(image_directory, ip_address, f"annotation.jpg")
                        
                        if os.path.exists(save_path_new):
                            os.remove(save_path_new)
                            print(f"File '{save_path_new}' has been deleted.")
                        else:
                            print(f"File '{save_path_new}' does not exist.")
                        
                        with open(file_path_new, "wb") as f:
                            f.write(message)
                            
                        ''' run the model with the new image '''
                        os.chdir('./model')
                        result = subprocess.run(['python3', './bound_seg_detect.py', '--image-path', '../'+file_path_new, '--save-path','../'+save_path_new], capture_output=True, text=True)
                        os.chdir('../')
                        
                        if(os.path.exists(save_path_new)):
                            print("Found a saved image: " + save_path_new)
                            image = Image.open(save_path_new)
                        else:
                            image = Image.open(file_path_new)
                        
                        image = image.resize((128*3, 128*3), Image.LANCZOS)
                        
                        file_path = ""
                        
                        for i in range(time_thre + 1):
                            st = ((datetime.now().second+1+i) if (datetime.now().second+1+i)<60 else (datetime.now().second+1+i-60))
                            file_path = os.path.join(image_directory, ip_address, f"{str(st)}.jpg")
                            image.save(file_path)
                            print(f"Saved image: {file_path}")
                        
                        if result.stdout:
                        
                            state = read_model_result(result.stdout)
                            print(result.stdout)
                            print(f"Device: {ip_address} detect result: {state}")
                            if(state):
                                with app.app_context():
                                    updated_plant = control.update_plant_ip(ip_address, state, current_time.strftime('%Y/%m/%d %H:%M:%S'))
                        else:
                            print(f"pic not found: {file_path}")
                        last_saved_time = current_time
        except websockets.exceptions.ConnectionClosed:
            ip_address = websocket.remote_address[0]
            await handle_disconnect(ip_address)
            print(ip_address, 'disconnect')
            break    
            
async def main():
    server = await websockets.serve(handle_connection, '0.0.0.0', 3001)
    
    stop_event = asyncio.Event()
    
    def handle_signal():
        stop_event.set()
    
    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGINT, handle_signal)
    loop.add_signal_handler(signal.SIGTERM, handle_signal)
    
    try:
        await stop_event.wait()
    finally:
        ''' set device disconnect when websocket close'''
        device_ip = read_device_ip()
        for ip in device_ip:
            handle_disconnect(ip)
            print(f"set device: {ip} disconnect")
        server.close()
        await server.wait_closed()
    
    


asyncio.run(main())
