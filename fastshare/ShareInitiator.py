import socket
import threading
import random
import hashlib
import time
import os
import sys


class FSServer:
    def __init__(self, port=1996, chunkSize=512):   # Specify chunkSize in terms of KB
        self.port = port
        self.keepAlive = True
        self.availableClients = []
        self.nParts = 0
        self.fileParts = []
        self.chunkData = []
        self.rand = random
        self.fileName = None
        self.uploadCacheDir = ".Upload_Temp"
        self.CHUNK_SIZE = chunkSize * 1024   # In bytes
        self.serverSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        self.serverSock.bind(('0.0.0.0', self.port))
        self.serverSock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.serverSock.listen(50)
        self.serverSock.settimeout(1)   # Wait for time out while shutting down
        print("Server started at {}:{}".format(socket.gethostbyname(socket.gethostname()), self.port))

    def cleanupTempDir(self):
        if not os.path.exists(self.uploadCacheDir):
            return
        tempFiles = os.listdir(self.uploadCacheDir)
        for l in tempFiles:
            os.remove(os.path.join(self.uploadCacheDir, l))
        os.removedirs(self.uploadCacheDir)

    def prepareFile(self, filePath=""):
        if not os.path.exists(filePath):
            raise FileNotFoundError
        if not os.path.exists(self.uploadCacheDir):
            os.mkdir(self.uploadCacheDir)
        self.fileName = os.path.basename(filePath)
        file = open(filePath, "rb")
        n = 0
        while True:
            data = file.read(self.CHUNK_SIZE)
            if not data: break
            outFileName = "{}.dat".format(n)
            outFilePath = os.path.join(self.uploadCacheDir, outFileName)
            out = open(outFilePath, "wb")
            out.write(data)
            out.close()
            n = n+1
        file.close()
        self.nParts = n
        self.fileParts = [0] * self.nParts
        for i in range(0, self.nParts):
            self.fileParts[i] = set()
            self.fileParts[i].add(0)

    def startListening(self):
        self.registerClient(socket.gethostbyname(socket.gethostname()), self.port)
        ## 3 Options: register, getNextChunk, ackFileChunk
        while self.keepAlive:
            try:
                client, addr = self.serverSock.accept()
            except socket.timeout: continue
            client.settimeout(1)
            try:
                data = client.recv(25).decode("utf-8")
                if data == "register":
                    client.send("ACK".encode("utf-8"))
                    threading.Thread(target=self.handleRegister, args=(client, addr)).start()
                elif data == "getNextChunk":
                    client.send("ACK".encode("utf-8"))
                    threading.Thread(target=self.handleGetFileChunk, args=(client, addr)).start()
                elif data == "fetchChunk":
                    client.send("ACK".encode("utf-8"))
                    threading.Thread(target=self.handleChunkTransfer, args=(client, addr)).start()
                elif data == "notifyReceived":
                    client.send("ACK".encode("utf-8"))
                    threading.Thread(target=self.handleNotifyReceived, args=(client, addr)).start()
                else:
                    raise socket.error
            except socket.timeout:
                pass
            except socket.error:
                client.send("NACK".encode("utf-8"))
                client.close()
                pass

    def handleRegister(self, client, addr):
        print("Client discovered: {}".format(addr[0]))
        try:
            data = client.recv(20)
            port = int(data.decode("utf-8"))
            if port < 0 or port > 65536:
                raise ValueError
            print("PORT: {}".format(port))
            id = self.registerClient(addr[0], port)
            client.send(id.encode("utf-8"))
            client.recv(5)
            client.send(self.fileName.encode("utf-8"))
        except ValueError:
            client.send("NACK".encode("utf-8"))
        except TypeError:
            client.send("NACK".encode("utf-8"))
        except socket.timeout:
            client.send("NACK".encode("utf-8"))
            pass
        except socket.error:
            pass
        client.close()
        pass

    def handleChunkTransfer(self, client, addr):
        print("Request for chunk from: {} ".format(addr[0]), end="")
        try:
            chunkNumber = int(client.recv(10).decode("utf-8"))
            if chunkNumber >= self.nParts or chunkNumber < 0: raise ValueError
            print("Chunk Number: {}".format(chunkNumber))
            client.send("ACK".encode("utf-8"))
        except ValueError as e:
            print(e)
            client.send("NACK".encode("utf-8"))
            client.close()
            return
        chunkPath = os.path.join(self.uploadCacheDir, "{}.dat".format(chunkNumber))
        file = open(chunkPath, "rb")
        client.sendfile(file)
        file.close()
        client.close()

    def handleNotifyReceived(self, client, addr):
        print("Notified of chunk received from: {}".format(addr[0]))
        try:
            id = client.recv(35).decode("utf-8")
            client.send("ACK".encode("utf-8"))
            chunkNumber = int(client.recv(5).decode("utf-8"))
            if chunkNumber >= self.nParts and chunkNumber < 0:
                raise ValueError
            index = self.getIndexOfID(id)
            if index < 0: raise ValueError
            client.send("ACK".encode("utf-8"))
        except ValueError as e:
            print(e)
            client.send("NACK".encode("utf-8"))
            return
        self.fileParts[chunkNumber].add(index)
        client.close()

    def handleGetFileChunk(self, client, addr):
        print("Received request for next chunk data from: {}: ".format(addr[0]), end="")
        try:
            id = client.recv(35).decode("utf-8")
            i = 0
            for l in self.availableClients:
                if id != l[0]:
                    i = i+1
                    continue
            if i == len(self.availableClients):
                print("Client not registered")
                raise socket.error
            print("Client ID: {}, ".format(id), end="")
            chunkNumber = self.getNextChunk(id)
            clientList = self.whoHas(chunkNumber)
            selected = self.rand.randint(0, len(clientList)-1)
            print("Returning Chunk Number: {}".format(chunkNumber))
            msg = [chunkNumber, clientList[selected][1], clientList[selected][2]]
            client.send(str(msg).encode("utf-8"))
            # self.fileParts[chunkNumber].add(self.getIndexOfID(id))
        except socket.error:
            client.send("NACK".encode("utf-8"))
        client.close()

    def getNextChunk(self, id):
        if self.fileParts == None:
            return
        index = self.getIndexOfID(id)
        # print("INDEX: {}".format(index))
        pending = self.getPendingChunksOf(index)
        # print(pending)
        if len(pending) > 0:
            rand = self.rand.randint(0, len(pending)-1)
            return pending[rand]
        else: return -1

    def oldGetNextChunk(self, id):
        if self.fileParts == None:
            return
        index = self.getIndexOfID(id)
        print("INDEX: {}".format(index))
        for i in range(0, self.nParts):
            print("Inspecting: {}".format(self.fileParts[i]))
            j = 0
            for p in self.fileParts[i]:
                if p != index: j = j+1
            if j == len(self.fileParts[i]): return i
        return -1

    def whoHas(self, chunkNumber):
        clients = []
        ids = self.fileParts[chunkNumber]
        for i in ids:
            clients.append(self.availableClients[i])
        return clients

    def registerClient(self, ip, port):
        for c in self.availableClients:
            if c[1] == ip and c[2] == port: return c[0]
        id = hashlib.md5(str(time.time()+random.random()).encode()).hexdigest()
        self.availableClients.append((id, ip, port))
        print("Registered new client: {}, {}:{}".format(id, ip, port))
        return id

    def getPendingChunksOf(self, index):
        pending = []
        for i in range(0, self.nParts):
            if index not in self.fileParts[i]: pending.append(i)
        return pending


    def getIndexOfID(self, id):
        for i in range(0, len(self.availableClients)):
            if self.availableClients[i][0] == id: return i
        return -1

    def handleInput(self):
        while self.keepAlive:
            try:
                command = input("").strip()
                if command == "": print(self.fileParts); continue
                if command == "list" or command == "list clients" or command == "whoall" or command == "lc":
                    if len(self.availableClients) == 0:
                        print("No hosts discovered yet")
                    else:
                        for host in self.availableClients: print(host)
                elif command == "list data" or command == "whatall" or command == "ld":
                    for i in range(0, self.nParts):
                        print("{}: {}".format(i, self.fileParts[i]))
                elif command == "list files" or command == "whichall" or command == "lf":
                    print("Chunk data files: ")
                    for i in range(0, self.nParts):
                        path = os.path.join(self.uploadCacheDir, "{}.dat".format(i))
                        print(path)
                    print("File to transfer: {}".format(self.fileName))
                elif command.startswith("whois "):
                    try:
                        index = int(command.split(" ")[1])
                        print(self.availableClients[index])
                    except ValueError:
                        print("Client does not exist!")
                elif command.startswith("whohas "):
                    t = command.split(" ")
                    for i in self.whoHas(int(t[1])):
                        print(i)
                elif command.startswith("remaining ") or command.startswith("p "):
                    remaining = self.getPendingChunksOf(int(command.split(" ")[1]))
                    print(remaining)
                elif command == "cleanup":
                    self.cleanupTempDir()
                elif command == "exit":
                    self.shutdown()
                elif command == "clear" or command == "cls":
                    if os.name == "nt": os.system("cls")
                    else: os.system("clear")
                elif command.startswith("e "):
                    os.system(command[2:])
                elif command.startswith("add "):
                    t = command.split(" ")
                    cn = int(t[1])
                    idin = int(t[2])
                    self.fileParts[cn].add(idin)
            except EOFError:
                self.shutdown()
                sys.exit(0)
            except Exception as e:
                print("Exception: {}".format(e))

    def shutdown(self):
        print("Shutting down server")
        self.keepAlive = False
        time.sleep(1.2) # Server socket time out is 1 second. Wait until startListening loop exits
        self.serverSock.close()

if __name__=="__main__":
    filePath = "C:\\Users\\PraveenHari\\Desktop\\DemiLe.mp4"
    ip = "0.0.0.0"
    port = 1990
    chunkSize = 1
    try:
        if len(sys.argv) >= 2:
            if not os.path.exists(sys.argv[1]):
                print("File not found!")
                sys.exit(-1)
            filePath = sys.argv[1]

        if len(sys.argv) >= 3:
            port = int(sys.argv[2])
        if len(sys.argv) >= 4:
            chunkSize = int(sys.argv[3])
    except ValueError:
        print("Fast Share Initiator")
        print("{} fileName [Port] [Chunk Size in MB]".format(sys.argv[0]))
        sys.exit(0)
    fss = FSServer(port=port, chunkSize=chunkSize * 1024)    # n MB chunks
    fss.cleanupTempDir()
    fss.prepareFile(filePath)
    threading.Thread(target=fss.startListening).start()
    threading.Thread(target=fss.handleInput).start()