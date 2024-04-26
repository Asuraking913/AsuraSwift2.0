import socket
import os
import tqdm

host = socket.gethostbyname(socket.gethostname())
port = 9999

def send_files(conn_message, filename, end_message, host, port):

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
    print(filename)
        
    filesize = os.path.getsize(filename)

    try:
        client.send((conn_message + '\n' + filename + '\n' + str(filesize)+ '\n' + end_message).encode())
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
