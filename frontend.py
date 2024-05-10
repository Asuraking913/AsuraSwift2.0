from pydoc import visiblename
import threading
import time
from tkinter.ttk import Progressbar
import PySimpleGUI as sg
from pathlib import Path
import os
from random import choice
from os import listdir
import socket
import tqdm
import shutil
import client
import server

theme = choice(['DarkPurple6', 'TanBlue', 'DarkGreen', 'BlueMono', 'DarkBlue17', 'DarkBlue3', 'lightGreen'])


spin_values = [
        ['Ports', ['9999', '9090', '8989']],
        ['Buffer', ['2mb/s', '4mb/s', '6mb/s', 'custom']],
        ['Info', ['Help', 'About']]
        ]

#functions
def recv_file(buffer, host, port, location):
    
    #socket object
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    response = "Received_handshake"

    try:
        server.bind((host, port))
    except Exception as e:
        pass
    server.listen()
    
    client, addr = server.accept()

    #hanshake
    handshake = client.recv(10).decode()
    print(handshake)
    client.send("Received_handshake".encode())

    # #progress
    # def progress_bar(new_size, total, target_file):
    #     layout = [
    #         [sg.ProgressBar(total,orientation="h",size=(50, 50), bar_color=("red","white"), key="progress")],
    #         [sg.Text(f'Transferring {200} and {400} folders')]
    #     ]

    #     progress = 0
    #     window = sg.Window("Progress Bar", layout)

    #     while True:
    #         event, value = window.read()

    #         new_size = os.path.getsize(target_file)
    #         progress += new_size
    #         window['progress'].update(progress)
    #         if new_size ==total:
    #             time.sleep(30)
    #             break


    #     window.close()

    #split gen message
    gen_message = client.recv(1024).decode()
    gen_message = gen_message.split('\n')

    conn_message = gen_message[0]
    file_name = gen_message[1]
    file_name = file_name.split('/')[-1]
    file_name = f'Received_{file_name}'
    file_size = gen_message[2]
    end_message = gen_message[3]

    print(conn_message)
    print(file_name)
    print(file_size)

    global progress

    progress = tqdm.tqdm(unit = "MB", unit_scale = True, unit_divisor = 1024, 
                    total = int(file_size))
    
    done = False

    # with open(file_name, 'wb') as file:
    #     while not done:
    #         data = client.recv(buffer)
    #         if data:
    #             file.write(data)
    #         else:
    #             done = True
    #         progress.update(len(data))

    file = open(f"{location}/{file_name}", 'wb')

    # threading.Thread(target=progress_bar, args = (os.path.getsize(gen_message[1]), file_size, gen_message[0]))


    while not done:
        data = client.recv(buffer)
        if data:
            file.write(data)
            progress.update(len(data))
        else:
            done = True
    

    client.close()
    server.close()
    print(end_message)


def send_file(connmessage, filename, lastmessage, host, port):

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    handshake = 'Hey server'
    

    #Exchange handshake
    while True:
        try:
            client.connect((host, port))
            client.send(handshake.encode())
            break
        except Exception as e:
            print("Waiting for Connection.")
            print("Waiting for Connection..")
            print("Waiting for Connection...")
            print("Waiting for Connection....")
            print("Waiting for Connection.....")
    
    reponse = client.recv(18).decode()
    print(reponse)
        
    filesize = os.path.getsize(filename)

    try:
        client.send((connmessage + '\n' + filename + '\n' + str(filesize) + '\n' + lastmessage).encode())
    except BrokenPipeError:
        pass

    progress = tqdm.tqdm(unit = "MB", unit_scale = True, unit_divisor = 1024,
                         total = int(filesize))

    with open(filename, 'rb') as file:
        while True:
            data = file.read(2000000)
            if data:
                try:
                    client.sendall(data)
                    progress.update(len(data))
                except BrokenPipeError or ConnectionResetError:
                    pass
            else:
                break


    client.close()

def create_window(theme):
    sg.theme(theme)
    font_family1 = 'TimesNewRoman 15 bold'
    font_family2 = 'Franklin 20'
    
    pad1 = ((5, 0), (20, 0))
    pad2 = ((8, 0), (20, 0))
    pad3 = ((5, 0), (10, 0))
    pad4 = ((8, 0), (10, 0))

    layout = [
        [sg.Menu(spin_values)],
    	[sg.Push(), sg.Button('Restart', key='key-image', enable_events=True)],
    	[sg.Text('Ip_Address ==>', pad=pad1, font=font_family1,  visible=False, key='key-ip'), sg.Input('127.0.1.1', pad=pad2, font=font_family2,  visible=False, key='key-ip_input')],
      	[sg.Text('Port    ====> ', font=font_family1, pad=pad3,  visible=False, key='key-port'), sg.Push(), sg.InputText('9999', font=font_family2, pad=pad4, disabled=True, visible=False, key='key-port_input', text_color='black')], 
      	[sg.VPush()],
      	[sg.Text('Speed(buffer): ', font=font_family1, pad=(5, 20), visible=False, key='key-buffer'), sg.Input('2mb/s', key='key-buffer_input', pad=(0, 20),  visible=False, font=font_family2, disabled=True)],
      	[sg.Input('File_name',  visible=False, size=(10, 30), font=font_family2, key='key-file_input', disabled=True, text_color='black'), sg.Button('Select_file',  visible=False, font='Arial 16 bold', key='key-file')],
      	[sg.Input('Folder_name',  visible=False, size=(10, 30), font=font_family2, key='key-folder_input', disabled=True, text_color='black'), sg.Button('Select_folder',  visible=False, font='Arial 16 bold', key='key-folder')],
      	[sg.VPush()],
        [sg.Input('Select Destination', visible = False, size = (20, 40), font=font_family2, key = 'key-dest_input', text_color='black', disabled=True), sg.Button('Location', visible = False, font = 'Arial 16 bold', key = 'key-dest')],
        [sg.Text('sdfsdf', key='key-progress', text_color="red")],
        [sg.Button('Select Location?', key='key-dest_btn', enable_events=True, visible=False, font="young 10 italic")],
        [sg.Button('Ready', key='key-ready', visible=False, font="young 10 bold")],
        [sg.Button('Recv-file', key='key-recv_file', visible=False, size = (10, 1), font='Arial 16 italic'), sg.Button('Recv-folder', key='key-recv_folder', visible=False, size = (10, 1), font='Arial 16 italic')],
      	[sg.Button('SEND', key='key-send', font='Arial 16 bold'), sg.Push(), sg.Button('RECEIVE', key='key-recv', font='Arial 16 bold')]
    	]


    return sg.Window('AsuraSwift', layout, size=(350, 450), element_justification='center')


#global Variable
window = create_window(theme)
reverse = False
send = False
recv = False
ready_recv = False
ready_send = False
ready_send2 = False
folder_set = False
file_list = []
folder_list2 = []
dest_folder = "NO"
running = True
folder_ready = False
total_files = 0 



while True:

    event, value = window.read()

    if event == sg.WINDOW_CLOSED:
        break

    if event in spin_values[0][1]:
        window['key-port_input'].update(event)

    if event in spin_values[1][1] and recv == True:
        window['key-buffer_input'].update(event)
    
    if event == 'Help':
        file = Path('Help.txt')
        # sg.popup('How to use the app', file.read_text())
        sg.popup("""AsuraSwift 1.0 User Guide

For the Sender:

Ensure a third device (e.g., phone with a hotspot) is available.
Both computers connect to the same hotspot.
In the app, set the IP address and port on both computers to match the hotspot's values.
The IP address and port should be that of the device creating the hotspot.
Select the file to send and initiate the transfer.
Note: Receiver must click "Receive" before the sender clicks "send"

For the Receiver:

Set the IP address and port to match the sender's values.
Optionally adjust the speed (buffer) for large files, but avoid unnecessary increases.
Click "Ready" and wait for the color indicator to turn green.
The sender can now press "Send" to initiate the transfer.
Note: Avoid excessive speed increases to prevent system glitches.

This guide facilitates seamless file transfer without relying on internet or data connections.""", no_titlebar=True)
    
    if event == 'About':
        file = Path('About.txt')
        sg.popup("""AsuraSwift 1.0 Information

Developed by AsuraKing913 (Israel Shedrack)

AsuraSwift 1.0 is a graphical user interface (GUI) application crafted by AsuraKing913, an aspiring coder with ambitions to reach god-level proficiency in the tech realm. The app is currently in its prototype phase, acknowledging the possibility of errors or bugs during operation.

Contact for Feedback:

Email: israelshedrack913@gmail.com
Users are encouraged to provide valuable feedback in the event of encountering any issues with the application. Your input is instrumental in enhancing the performance and reliability of AsuraSwift.""", no_titlebar=True)


    #updating send changes: opening file path
    if send:
        if event == 'key-file':
            window['key-folder'].update(visible = False)
            window['key-folder_input'].update(visible = False)
            file = sg.popup_get_file('Select file', no_window=True)
            file = file
            try:
                file_path = Path(file)
            except TypeError:
                continue
            file_path = file_path.resolve()
            ready_send = True
            
            #cient parameters
            if dest_folder == "NO":
                file_name = file_path
            else:
                file_path = file.split('/')
                file_name = file_path[-1]
                new_path = f"{dest_folder}/{file_name}"
                file_name = new_path
            try:
                file_size = os.path.getsize(file)
            except FileNotFoundError:
                continue
            file_size = str(file_size)
            conn_message = "Connection Initiated"
            end_message = "Connection Terminated"
            window['key-file_input'].update(str(file_name).split('/')[-1])


    #folder send changes
    if event == 'key-folder':
        conn_message = "Connection Initiated"
        end_message = "Connection Terminated"
        window['key-file'].update(visible = False)
        window['key-file_input'].update(visible = False)
        folder = sg.popup_get_folder("Select folder", no_window=True)
        try:
            folder_list = listdir(folder)
        except TypeError:
            continue
        except FileNotFoundError:
            continue
            
        window['key-dest_input'].update(str(folder.split('/')[-1]))
        
        
                    
        folder_ready = True

    if event == 'key-send' and reverse == False:
        reverse = True
        send = True
        window['key-ip'].update(visible = True)
        window['key-ip_input'].update(visible = True)
        window['key-port'].update(visible = True)
        window['key-port_input'].update(visible = True)
        window['key-file'].update(visible = True)
        window['key-file_input'].update(visible = True)
        window['key-folder'].update(visible = True)
        window['key-folder_input'].update(visible = True)
        window['key-recv'].update(visible = False)

        #running external scripts
        def exec_send_script():
            send_file(conn_message, str(file_name), end_message, str(value['key-ip_input']), int(value['key-port_input']))
        
    if event == 'key-send' and ready_send == True:
        # exec_send_script()
        threading.Thread(target=exec_send_script).start()

    if event == 'key-send' and folder_ready == True:

        #Seperating root folder
        main_root_folder = folder.split('/')[-1]

        #define file_sending_script
        def exec_send_script2(filename, Folder):
            client.send_files(conn_message, str(filename), end_message, str(value['key-ip_input']), int(value['key-port_input']), root_folder=main_root_folder, folder = Folder)
        
        # #Define dir transfer
        def Render_root(root_folder):
            #Render each path to client socket thorough each iteration and create copy starting from the root folder at the destination
            def Render_folder_paths(folderX, path):
                new_folder = folderX.split('/')[-1]
                index = path.find(new_folder)
                relative_path = path[index + len(new_folder):]
                final_path = new_folder + relative_path
                return final_path

            def send_folder_paths():
                sub_paths = Render_folder_paths(root_folder, path)
                # print(dest_folder)
                dir = f'{folder}' + '\n' + str(sub_paths)
                exec_send_script2(dir, Folder="YES")
                time.sleep(2)

            # def calculate_items_sizes(target_path):
            #     list_items = os.walk(target_path)
            #     total_folder = 0
            #     total_files = 0
            #     total_size = 0
            #     filesizes = 0
            #     for path, folders, filenames in list_items:
            #         total_folder += len(folders)
            #         total_files += len(filenames)
            #         for files in filenames:
            #             filesizes  = os.path.getsize(f"{path}/{files}")
            #             total_size += filesizes
            #     total_size_mb = total_size / (1024 * 1024)
            #     total_size_gb = total_size / (1024 * 1024 * 1024)
                
            #     ren_str = f"{total_folder} folders present" + "\n" + f"{total_files} files present"  + "\n" + f"{total_size_mb:.2f} MB in size" + "\n" + f"{total_size_gb:.2f} GB in size"
            #     return ren_str                
                
            # ren_str = calculate_items_sizes(root_folder)

            dir_list = list(os.walk(root_folder))
            for path, folders, filenames in dir_list:
                # Render_send_folder_path
                for folder in folders:
                    send_folder_paths()
                print("All folders sent and created")
                print("Sending files.")
                print("Sending files..")
                print("Sending files...")  
            time.sleep(1)
            exec_send_script2('END', Folder= "YES")

            for path, folders, filenames in dir_list:
                for files in filenames:
                    dir_files = f"{path}/{files}"
                    exec_send_script2(dir_files, Folder = "NO")
                    time.sleep(1)
            exec_send_script2('END', Folder= "YES")
            print("Folders Transmiteed sucessfully")
        Render_root(folder)

    if event == "key-dest_btn":  
        window['key-dest'].update(visible = True)
        window['key-dest_input'].update(visible = True)
        window['key-dest_btn'].update(visible = False)

      #updating recv changes
    if event == 'key-recv' and reverse == False:
        reverse = True
        window['key-ip'].update(visible = True)
        window['key-ip_input'].update(visible = True)
        window['key-port'].update(visible = True)
        window['key-port_input'].update(visible = True)
        # window['key-port_input'].update(visible = True)
        window['key-buffer'].update(visible = True)
        window['key-buffer_input'].update(visible = True)
        window['key-ready'].update(visible = True)
        window['key-send'].update(visible = False)
        window['key-dest_btn'].update(visible = True)
        window['key-recv'].update(visible = False)
        window['key-recv_file'].update(visible = True)
        window['key-recv_folder'].update(visible = True)
        recv = True
    
    if event == 'key-dest':
        dest_folder = sg.popup_get_folder('Select Destination Folder', no_window=True)
        window['key-dest_input'].update(dest_folder)

    #updating buffer value along with server parameters
    if event == 'key-ready' and reverse == True:
        match value['key-buffer_input']:
            case '2mb/s': 
                buffer = 2000000
                window['key-buffer_input'].update(disabled = True)
            case '4mb/s': 
                buffer = 4000000
                window['key-buffer_input'].update(disabled = True)
            case '6mb/s': 
                buffer = 6000000
                window['key-buffer_input'].update(disabled = True)
            case 'custom':
                # sg.popup("Warning: setting buffer higher than \n 60000 might lead to unintended \n consequences")
                value = sg.PopupGetText('Warning: setting buffer higher than \n 60000 might lead to unintended \n consequences')
                window['key-buffer_input'].update(int(value))
                buffer = value
        try:
            ip_addr = value['key-ip_input']
            port = value['key-port_input']
        except TypeError:
            continue

    if event == 'key-ready':
        ready_recv = True
        window['key-ready'].update(button_color = 'green')

        #creating server functions for destinations
        def exec_recv_script():
            return recv_file(int(buffer), str(ip_addr), int(port), location = dest_folder)

        def exec_recv_script2(folder, destination):
             report = server.recv_file(int(buffer), str(ip_addr), int(port), locate_folder=destination)
             return report

        def exec_recv_script3(destination):
             report = server.recv_file1(int(buffer), str(ip_addr), int(port), locate_folder=destination)
             return report

    #executing recv scripts
    if event == 'key-recv_folder' and ready_recv:
        sg.popup("Please ensure that you are \n actually receiving a folder before \n clicking this button")
        def thread1():
            running = True
            while running:
                print("Script 2 executing")
                running = exec_recv_script2(folder = 'YES', destination=dest_folder)
            time.sleep(1)
            running = True
            while running:
                print("Script 3 executing")
                running = exec_recv_script3(destination=dest_folder)
                time.sleep(0.3)
            print("Files Received sucessfully") 
            
        threading.Thread(target = thread1).start()
        window['key-ready'].update(button_color = 'Red')
    
    if event == 'key-recv_file' and ready_recv:
        sg.popup("Please ensure that you are \n actually receiving a file before \n clicking this button")
        threading.Thread(target = exec_recv_script).start()
        window['key-ready'].update(button_color = 'Red')

    #Affirming ip_value
    ip_value = value['key-ip_input']
    if event == 'key-ready':
        if ip_value[0:10] == '192.168.43' or ip_value[0:9] == '127.0.1.1':
            ready_recv = True
            ready_send = True
        else:
            ready_recv = False
            ready_send = False
    
    #restarting window
    if event == 'key-image':
        window.close()
        theme = choice(['DarkPurple6', 'TanBlue', 'DarkGreen', 'BlueMono', 'DarkBlue17', 'DarkBlue3', 'lightGreen'])
        window = create_window(theme)
        reverse = False
        send = False
        recv = False
        ready_send = False
        ready_recv = False




window.close()
