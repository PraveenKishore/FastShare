import socket
import threading

SERVER_ADDR = ("127.0.0.1", 1990)

class FSClient:
    def __init__(self, port=1996):
        self.port = port
        self.keepAlive = True
        self.id = None
        self.serverSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        self.serverSock.bind(('0.0.0.0', self.port))
        self.serverSock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.serverSock.listen(50)
        self.ipAddress = socket.gethostbyname(socket.gethostname())
        print("File peer started at {}:{}".format(self.ipAddress, self.port))

    def startListening(self):
        while self.keepAlive:
            client, addr = self.serverSock.accept()
            threading.Thread(target=self.handlePeer, args=(client, addr)).start()

    def register(self):
        try:
            clientSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
            clientSock.settimeout(5)
            clientSock.connect(SERVER_ADDR)
            clientSock.send("register".encode("utf-8"))
            clientSock.recv(5).decode("utf-8")
            clientSock.send(str(self.port).encode("utf-8"))
            id = clientSock.recv(35).decode("utf-8")
            if id:
                print("Registration successful with the server. ID received: {}\t{}:{}".format(id, self.ipAddress, self.port))
                self.id = id
            else:
                raise socket.error
            clientSock.close()
        except socket.error:
            print("Registration unsuccessful with the server")

    def getNextChunk(self):
        if not self.id:
            print("Please register first!")
            return
        print("({}:{}): Requesting next chunk.. ".format(self.ipAddress, self.port), end="")
        clientSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        clientSock.connect(SERVER_ADDR)
        clientSock.send("getNextChunk".encode("utf-8"))
        clientSock.recv(5).decode("utf-8")
        clientSock.send(self.id.encode("utf-8"))
        data = clientSock.recv(50).decode("utf-8")
        # print(data)
        temp = data.replace("\'", "").replace("[", "").replace("]", "").split(", ")
        chunkNumber = int(temp[0])
        ip = str(temp[1])
        port = int(temp[2])
        print("Chunk number: {}, from ip: {}, port: {}".format(chunkNumber, ip, port))
        return (chunkNumber, ip, port)

    def handlePeer(self, client, addr):
        print("Peer connected: {}".format(addr[0]))
        client.close()

    def handleInput(self):
        while self.keepAlive:
            command = input("").strip()
            if command == "": continue

if __name__=="__main__":
    # fsc = FSClient(1990)
    # threading.Thread(target=fsc.startListening).start()
    # fsc.register()
    # l = []
    # for i in range(0, 6):
    #     l.append(fsc.getNextChunk())

    # for i in l:
    #   print(i)
    f = []
    for i in range(1995, 2000):
        temp = FSClient(port=i)
        temp.register()
        f.append(temp)

    for i in range(0, 1):
        for c in f:
            c.getNextChunk()