import socket
import os

host = socket.gethostbyname(socket.gethostname())
port = 9999

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
handshake = 'Hey server'
conn_message = "Connected"
end_message = "Terminated"
filename = 'Help.txt'
filesize = os.path.getsize(filename)

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

client.send((conn_message, '\n' + filename + '\n' + str(filesize) + end_message))
    

    
