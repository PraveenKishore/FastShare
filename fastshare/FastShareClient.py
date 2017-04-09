import socket
import threading

class FSClient:
    def __init__(self, port=1996):
        self.port = port
        self.keepAlive = True
        self.availableClients = set()
        self.serverSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        self.serverSock.bind(('0.0.0.0', self.port))
        self.serverSock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.serverSock.listen(50)
        print("Server started at {}".format(socket.gethostbyname(socket.gethostname())))

    def startListening(self):
        while self.keepAlive:
            client, addr = self.serverSock.accept()
            threading.Thread(target=self.handleClient, args=(client, addr)).start()

    def handleClient(self, client, addr):
        print("Client discovered: {}".format(addr[0]))
        self.availableClients.add(addr[0])
        client.close()

    def handleInput(self):
        while self.keepAlive:
            command = input("").strip()
            if command == "": continue
            if command == "list":
                if len(self.availableClients) == 0:
                    print("No hosts discovered yet")
                else:
                    for host in self.availableClients: print(host)

if __name__=="__main__":
    clientSock = socket.socket()
    clientSock.connect(("127.0.0.1", 1996))