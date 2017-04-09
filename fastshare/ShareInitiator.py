import socket
import threading

class FSServer:
    def __init__(self, port=1996):
        self.port = port
        self.keepAlive = True
        self.availableClients = []
        self.serverSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        self.serverSock.bind(('0.0.0.0', self.port))
        self.serverSock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.serverSock.listen(50)
        print("Server started at {}".format(socket.gethostbyname(socket.gethostname())))

    def startListening(self):
        while self.keepAlive:
            client, addr = self.serverSock.accept()
            client.settimeout(2)
            try:
                data = client.recv(25).decode("utf-8")
                if data == "register":
                    client.send("ACK".encode("utf-8"))
                    threading.Thread(target=self.handleRegister, args=(client, addr)).start()
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
            self.registerClient(addr[0], port)
            client.send("ACK".encode("utf-8"))
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

    def registerClient(self, ip, port):
        for c in self.availableClients:
            if c[1] == ip and c[2] == port: return
        self.availableClients.append((len(self.availableClients)+1, ip, port))

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
    fss = FSServer()
    threading.Thread(target=fss.startListening).start()
    threading.Thread(target=fss.handleInput).start()