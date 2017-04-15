import socket
import threading
import os
import time

SERVER_ADDR = ("127.0.0.1", 1990)

class FSClient:
    def __init__(self, port=1996):
        self.port = port
        self.keepAlive = True
        self.id = None
        self.receivedChunks = []
        self.fileToReceiveName = "outfile.py"
        self.downloadCacheDir = ".DownloadCache-{}".format(port)
        self.serverSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        self.serverSock.bind(('0.0.0.0', self.port))
        self.serverSock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.serverSock.listen(50)
        self.serverSock.settimeout(1)
        self.ipAddress = socket.gethostbyname(socket.gethostname())
        self.prepareTempDir()
        print("File peer started at {}:{}".format(self.ipAddress, self.port))

    def startListening(self):
        while self.keepAlive:
            try:
                client, addr = self.serverSock.accept()
            except socket.error:
                continue
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
            clientSock.send("ACK".encode("utf-8"))
            self.fileToReceiveName = clientSock.recv(150).decode("utf-8")
            print("File name to receive: {}".format(self.fileToReceiveName))
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

    def cleanupTempDir(self):
        if not os.path.exists(self.downloadCacheDir): return
        files = os.listdir(self.downloadCacheDir)
        for f in files:
            os.remove(os.path.join(self.downloadCacheDir, f))
        os.removedirs(self.downloadCacheDir)

    def handlePeer(self, client, addr):
        print("{}:{} >> Peer connected: {}".format(self.ipAddress, self.port, addr[0]))
        try:
            data = client.recv(25).decode("utf-8")
            if data == "fetchChunk":
                client.send("ACK".encode("utf-8"))
                threading.Thread(target=self.handleChunkTransfer, args=(client, addr)).start()
            else:
                raise socket.error
        except socket.timeout:
            pass
        except socket.error:
            client.send("NACK".encode("utf-8"))
            client.close()

    def handleChunkTransfer(self, client, addr):
        print("Request for chunk from: {} ".format(addr[0]), end="")
        try:
            chunkNumber = int(client.recv(5).decode("utf-8"))
            # print(self.receivedChunks)
            # if chunkNumber in self.receivedChunks: raise IndexError
            # print("Chunk Number to send: {}".format(chunkNumber))
            client.send("ACK".encode("utf-8"))
        except Exception as e:
            print(e)
            client.send("NACK".encode("utf-8"))
            client.close()
            return
        chunkPath = os.path.join(self.downloadCacheDir, "{}.dat".format(chunkNumber))
        file = open(chunkPath, "rb")
        client.sendfile(file)
        file.close()
        client.close()

    def notifyChunkReceived(self, chunkNumber):
        clientSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        clientSock.connect(SERVER_ADDR)
        clientSock.send("notifyReceived".encode("utf-8"))
        data = clientSock.recv(5).decode("utf-8")
        # print("sent command: " + data)
        clientSock.send(self.id.encode("utf-8"))
        data = clientSock.recv(5).decode("utf-8")
        # print("Sent ID: " + data)
        clientSock.send("{}".format(chunkNumber).encode("utf-8"))
        data = clientSock.recv(5).decode("utf-8")
        # print("Send chunk id: " + data)
        clientSock.close()

    def fetchChunk(self, chunkNumber, ip, port):
        clientSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        clientSock.connect((ip, port))
        clientSock.send("fetchChunk".encode("utf-8"))
        clientSock.recv(5).decode("utf-8")
        clientSock.send(str(chunkNumber).encode("utf-8"))
        data = clientSock.recv(5).decode("utf-8")
        # print(data)
        if data != "ACK":
            print("Error while fetching chunk {}".format(chunkNumber))
            clientSock.close()
            return
        chunkFilePath = os.path.join(self.downloadCacheDir, "{}.dat".format(chunkNumber))
        chunkFile = open(chunkFilePath, "wb")
        while True:
            data = clientSock.recv(1024)
            # print("REceived{}".format(data))
            if not data:
                break
            chunkFile.write(data)
        chunkFile.close()
        clientSock.close()
        self.notifyChunkReceived(chunkNumber)
        if chunkNumber != -1 and chunkNumber not in self.receivedChunks:
            self.receivedChunks.append(chunkNumber)

    def prepareTempDir(self):
        if not os.path.exists(self.downloadCacheDir):
            os.mkdir(self.downloadCacheDir)

    def assembleFile(self):
        if len(self.receivedChunks) <= 0:
            # print("Nothing to merge!")
            return
        self.receivedChunks.sort()
        # print(self.receivedChunks)
        outfilePath = os.path.join(self.downloadCacheDir, self.fileToReceiveName)
        outfile = open(outfilePath, "wb")
        for f in self.receivedChunks:
            chunkPath = os.path.join(self.downloadCacheDir, "{}.dat".format(f))
            chunkFile = open(chunkPath, "rb")
            data = chunkFile.read()
            outfile.write(data)
            chunkFile.close()
        outfile.close()
        print("{}:{} >> File finished downloading: {}".format(self.ipAddress, self.port, outfilePath))

    def shutdown(self):
        self.keepAlive = False
        print("Shutting down client: {}:{}".format(self.ipAddress, self.port))
        time.sleep(1.2)
        try:
            self.serverSock.shutdown(socket.SHUT_RDWR)
            self.serverSock.close()
        except socket.error:
            pass

    def startReceiving(self):
        start = time.time()
        while True:
            (chunkNumber, ip, port) = self.getNextChunk()
            if chunkNumber == -1: break
            self.fetchChunk(chunkNumber, ip, port)
        self.assembleFile()
        end = time.time()
        elapsed = end - start
        print("Elapsed time: {}".format(elapsed))

    def handleInput(self):
        while self.keepAlive:
            command = input("").strip()
            if command == "": continue
            elif command == "exit":
                self.shutdown()

f = []

def run():
    for i in range(1995, 2000):
        temp = FSClient(port=i)
        threading.Thread(target=temp.startListening).start()
        temp.cleanupTempDir()
        temp.register()
        temp.prepareTempDir()
        f.append(temp)

    done = []

    for i in range(0, 5):
        for c in f:
            # c.getNextChunk()
            if c in done: continue
            (chunkNumber, ip, port) = c.getNextChunk()
            if chunkNumber == -1:
                done.append(c)
                c.assembleFile()
            else:
                c.fetchChunk(chunkNumber, ip, port)
            # input("Press any key to fetch next chunks")

    for c in f:
        c.shutdown()

def runMultiple():
    for i in range(1995, 2000):
        temp = FSClient(port=i)
        threading.Thread(target=temp.startListening).start()
        temp.cleanupTempDir()
        temp.register()
        temp.prepareTempDir()
        f.append(temp)
        threading.Thread(target=temp.startReceiving).start()

if __name__=="__main__":
    # fsc = FSClient(1990)
    # threading.Thread(target=fsc.startListening).start()
    # fsc.register()
    # l = []
    # for i in range(0, 6):
    #     l.append(fsc.getNextChunk())

    # for i in l:
    #   print(i)
    threading.Thread(target=runMultiple).start()
    while True:
        command = input("").strip()
        if command == "":
            continue
        elif command == "exit":
            for c in f:
                c.shutdown()
            break

