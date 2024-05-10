from fileinput import filename
import socket
import os
import time 
import tqdm 
<<<<<<< HEAD
import PySimpleGUI as sg
import threading
=======
>>>>>>> origin/master

def recv_file(buffer, host, port, locate_folder = "NO"):
    
    #socket object
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    response = "Received_handshake"

<<<<<<< HEAD

=======
>>>>>>> origin/master
    try:
        server.bind((host, port))
    except Exception as e:
        pass
    server.listen()
    
    client, addr = server.accept()

    #hanshake
    handshake = client.recv(10).decode()
    print(handshake)
    # client.send(f"Received_handshakes".encode())

    def recv_folder_path():
        gen_message1 = client.recv(1024).decode()
        if gen_message1 == "END":
            print("Transmission terminated")
            return False
        else:
            gen_message = gen_message1.split('\n')
            folder = gen_message[0]
            sub_paths = gen_message[1]
            root_folder = gen_message[-1]
            if locate_folder == "NO":
                os.makedirs(f'{root_folder}', exist_ok=True)
                os.makedirs(f'{sub_paths}/{folder}', exist_ok= True)
                print(f'Created new_dir:{sub_paths}/{folder}')
            else:
                os.makedirs(f'{locate_folder}/{root_folder}', exist_ok=True)
                os.makedirs(f'{locate_folder}/{sub_paths}/{folder}', exist_ok= True)
                print(f'Created new_dir:{locate_folder}/{sub_paths}/{folder}')
                time.sleep(1)
            return True

    report = recv_folder_path()
    return report

def recv_file1(buffer, host, port, locate_folder = "NO"):
    
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
    # client.send(f"Received_handshakes".encode())    

    gen_message1 = client.recv(1024).decode()
    if gen_message1 == "END":
        return False
    else:
        gen_message = gen_message1.split('\n')
        conn_message = gen_message[0]
        file_name = gen_message[1]
        file_name1 = file_name.split('/')[-1]
        # file_name1 = f'Received_{file_name1}'
        file_size = gen_message[2]
        end_message = gen_message[3]
        root_folder = gen_message[4]

        print(conn_message)
        print(file_size)

        global progress

        progress = tqdm.tqdm(unit = "MB", unit_scale = True, unit_divisor = 1024, 
                                total = int(file_size))
                
        done = False

        str1 = file_name
        str2 = root_folder
        index = str1.find(str2)
        relative_path = str1[index + len(str2):]
        final_path = str2 + relative_path

        with open(f"{locate_folder}/{final_path}", 'wb') as file:
            while not done:
                data = client.recv(buffer)
                if data:
                    file.write(data)
                else:
                    done = True
                progress.update(len(data))

        # while not done:
        #     data = client.recv(buffer)
        #     if data:
        #         file.write(data)
        #         progress.update(len(data))
        #     else:
        #         done = True
        print(f"Created {file_name1} at {locate_folder}/{final_path}")
        print(end_message)
        return True