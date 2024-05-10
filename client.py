import socket
import os
import time
import tqdm

host = socket.gethostbyname(socket.gethostname())
port = 9999

def send_files(conn_message, filename, end_message, host, port, root_folder, folder ='NO'):

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    handshake = 'Hey server'

    def send_file(filename_par):
        print(filename_par.split('/')[-1])
        filesize = os.path.getsize(filename)
<<<<<<< HEAD
        while True:
            try:
                client.send((conn_message + '\n' + filename_par + '\n' + str(filesize)+ '\n' + end_message + '\n' + root_folder).encode())
                time.sleep(1)
                break
            except BrokenPipeError:
                print(f"waiting for connection.{e}")
                print(f"waiting for connection..{e}")
                print(f"waiting for connection...{e}")
                print(f"waiting for connection....{e}")
                print(f"waiting for connection.....{e}")
                print(f"waiting for connection......{e}")
                time.sleep(2)
                client.send((conn_message + '\n' + filename_par + '\n' + str(filesize)+ '\n' + end_message + '\n' + root_folder).encode())

        
=======
        try:
            client.send((conn_message + '\n' + filename_par + '\n' + str(filesize)+ '\n' + end_message + '\n' + root_folder).encode())
            time.sleep(1)
        except Exception as e:
            time.sleep(2)
        # except BrokenPipeError:
        #     pass
        
        # except ConnectionRefusedError:
        #     time.sleep(2)
>>>>>>> origin/master
        progress = tqdm.tqdm(unit = "MB", unit_scale = True, unit_divisor = 1024,
                            total = int(filesize))

        with open(filename_par, 'rb') as file:
            while True:
                data = file.read(1024)
                if data:
                    try:
                        client.sendall(data)
                        progress.update(len(data))
                    except Exception as e:
                        time.sleep(2)
                else:
                    break

    def send_folder_path(filename1_par):
        print("Sending.")
        print("Sending..")
        print("Sending...")
        try:
            client.send((f"{filename1_par}").encode())
            file_name1 = filename1_par.split('\n')[0]
            print(f'Sent folder |{file_name1}| to Recv socket')
        except BrokenPipeError:
            pass

    
    #Exchange handshake
    while True:
        try:
            client.connect((host, port))
            client.send(handshake.encode())
            break
        except Exception as e:
            print(f"Waiting for Connection.    {e}")
            print(f"Waiting for Connection..   {e}")
            print(f"Waiting for Connection...  {e}")
            print(f"Waiting for Connection.... {e}")
            print(f"Waiting for Connection.....{e}")

    try:
        if folder == 'NO':
            send_file(filename)
        else:
            send_folder_path(filename)
    finally:
        client.close()