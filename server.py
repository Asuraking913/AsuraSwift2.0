import socket
import os 
import tqdm 

def recv_file(buffer, host, port, folder=False, sub_folder= False):
    
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

    if folder == False:
        #split gen message
        gen_message = client.recv(1024).decode()
        gen_message = gen_message.split('\n')

        conn_message = gen_message[0]
        file_name = gen_message[1]
        file_name1 = file_name.split('/')[-1]
        file_name = f'Received_{file_name}'
        file_size = gen_message[2]
        end_message = gen_message[3]

        print(conn_message)
        print(file_name1)
        print(file_size)

        global progress

        progress = tqdm.tqdm(unit = "MB", unit_scale = True, unit_divisor = 1024, 
                        total = int(file_size))
        
        done = False

        with open(file_name1, 'wb') as file:
            while not done:
                data = client.recv(buffer)
                if data:
                    file.write(data)
                else:
                    done = True
                progress.update(len(data))

        file = open(file_name, 'wb')

        while not done:
            data = client.recv(buffer)
            if data:
                file.write(data)
                progress.update(len(data))
            else:
                done = True

    else:
        gen_message = client.recv(1024).decode()
        gen_message = gen_message.split('\n')

        conn_message = gen_message[0]
        file_name = gen_message[1]
        file_size = gen_message[2]
        end_message = gen_message[3] 
        os.makedirs(file_name)
    

    client.close()
    server.close()
    print(end_message)
