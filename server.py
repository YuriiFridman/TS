import socket
import threading

class VoiceChatServer:
    def __init__(self, host='0.0.0.0', port=5000):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((host, port))
        self.server.listen()
        self.clients = []

    def handle_client(self, client_socket):
        while True:
            try:
                message = client_socket.recv(1024)
                if message:
                    self.broadcast(message, client_socket)
                else:
                    self.remove(client_socket)
            except:
                continue

    def broadcast(self, message, client_socket):
        for client in self.clients:
            if client != client_socket:
                try:
                    client.send(message)
                except:
                    self.remove(client)

    def remove(self, client_socket):
        if client_socket in self.clients:
            self.clients.remove(client_socket)

    def start(self):
        print("Server is running...")
        while True:
            client_socket, addr = self.server.accept()
            self.clients.append(client_socket)
            print(f"Connection from {addr} has been established.")
            threading.Thread(target=self.handle_client, args=(client_socket,)).start()

if __name__ == "__main__":
    server = VoiceChatServer()
    server.start()