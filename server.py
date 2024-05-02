import socket
import os
import time 
import tqdm 

def recv_file(buffer, host, port, Folder = 'NO', locate_folder = "NO"):
    
    print(locate_folder)
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

    def recv_file1():

        #split gen message
        gen_message1 = client.recv(1024).decode()
        gen_message = gen_message1.split('\n')
        conn_message = gen_message[0]
        file_name = gen_message[1]
        file_name1 = file_name.split('/')[-1]
        # file_name1 = f'Received_{file_name1}'
        file_size = gen_message[2]
        end_message = gen_message[3]

        print(conn_message)
        print(f"Created {file_name1} at {file_name}")
        print(file_size)

        global progress

        progress = tqdm.tqdm(unit = "MB", unit_scale = True, unit_divisor = 1024, 
                            total = int(file_size))
            
        done = False

        with open(file_name, 'wb') as file:
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

        print(end_message)

    def recv_folder_path():
        gen_message1 = client.recv(1024).decode()
        if gen_message1 == "END":
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

    if Folder == 'NO':
        recv_file1()
    else:
        report = recv_folder_path()
        return report