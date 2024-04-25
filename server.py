import socket
import os 
import tqdm 

host = socket.gethostbyname(socket.gethostname())
port = 9999
response = "Received_handshake"

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    server.bind((host, port))
except Exception as e:
    print(f"Error as {e}")
    
server.listen()

while True:
    client, addr = server.accept()
    handshake = client.recv(10).decode()
    print(handshake)
    break
client.send("Received_handshake".encode())
