import socket
import threading
import random
import hashlib
import time

class FSServer:
    def __init__(self, port=1996):
        self.port = port
        self.keepAlive = True
        self.availableClients = []
        self.nParts = 0
        self.fileParts = []
        self.serverSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        self.serverSock.bind(('0.0.0.0', self.port))
        self.serverSock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.serverSock.listen(50)
        print("Server started at {}".format(socket.gethostbyname(socket.gethostname())))

    def prepareFile(self):
        self.nParts = 5
        self.fileParts = [0] * self.nParts
        for i in range(0, self.nParts):
            self.fileParts[i] = set()
            self.fileParts[i].add(0)

    def startListening(self):
        self.registerClient(socket.gethostbyname(socket.gethostname()), self.port)
        ## 3 Options: register, getNextChunk, ackFileChunk
        while self.keepAlive:
            client, addr = self.serverSock.accept()
            client.settimeout(2)
            try:
                data = client.recv(25).decode("utf-8")
                if data == "register":
                    client.send("ACK".encode("utf-8"))
                    threading.Thread(target=self.handleRegister, args=(client, addr)).start()
                elif data == "getNextChunk":
                    client.send("ACK".encode("utf-8"))
                    threading.Thread(target=self.handleGetFileChunk, args=(client, addr)).start()
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

    def handleGetFileChunk(self, client, addr):
        print("Received request for next chunk from: {}".format(addr[0]))
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
            print("Client ID: {}".format(id))
            chunkNumber = self.getNextChunk(id)
            clientList = self.whoHas(chunkNumber)
            selected = random.randint(0, len(clientList)-1)
            print("Chunk Number: {}".format(chunkNumber))
            msg = [chunkNumber, clientList[selected][1], clientList[selected][2]]
            client.send(str(msg).encode("utf-8"))
            self.fileParts[chunkNumber].add(self.getIndexOfID(id))
        except socket.error:
            client.send("NACK".encode("utf-8"))
        client.close()

    def getNextChunk(self, id):
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
        print("Registered new client: {}, {}, {}".format(id, ip, port))
        return id

    def getIndexOfID(self, id):
        for i in range(0, len(self.availableClients)):
            if self.availableClients[i][0] == id: return i
        return -1

    def handleInput(self):
        while self.keepAlive:
            try:
                command = input("").strip()
                if command == "": print(self.fileParts); continue
                if command == "list" or command == "list clients" or command == "whoall":
                    if len(self.availableClients) == 0:
                        print("No hosts discovered yet")
                    else:
                        for host in self.availableClients: print(host)
                elif command == "list data" or command == "whatall" or command == "ld":
                    for i in range(0, self.nParts):
                        print("{}: {}".format(i, self.fileParts[i]))
                elif command.startswith("whois "):
                    try:
                        index = int(command.split(" ")[1])
                        print(self.availableClients[index])
                    except Exception:
                        print("Client does not exist!")
                elif command.startswith("whohas "):
                    t = command.split(" ")
                    for i in self.whoHas(int(t[1])):
                        print(i)
                elif command.startswith("add "):
                    t = command.split(" ")
                    cn = int(t[1])
                    idin = int(t[2])
                    self.fileParts[cn].add(idin)
            except Exception as e:
                print(e)

    def shutdown(self):
        self.keepAlive = False
        self.serverSock.shutdown(socket.SHUT_RDWR)
        self.serverSock.close()
        print("Shutting down server")

if __name__=="__main__":
    fss = FSServer()
    fss.prepareFile()
    threading.Thread(target=fss.startListening).start()
    threading.Thread(target=fss.handleInput).start()