import socket
from threading import Thread
import sys

defaultIP = "127.0.0.1"
defaultPort = 1947

initialServerIP = "127.0.0.1"
initialServerPort = 1947

if len(sys.argv) > 1:
    defaultIP = sys.argv[1]
if len(sys.argv) > 2:
    defaultPort = int(sys.argv[2])
if len(sys.argv) > 3:
    initialServerIP = sys.argv[3]
if len(sys.argv) > 4:
    initialServerPort = sys.argv[4]

SELF_SERVER_ADDR = (defaultIP, defaultPort)
INITIAL_SERVER_ADDR = (initialServerIP, initialServerPort)

class  FastShareServer:
    def __init__(self):
        self.serverSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.peersAddr = set([])
        self.listenThread = None
        self.keepAlive = True

    def startPeerServer(self, serverAddr = SELF_SERVER_ADDR, backlog=15):
        self.serverSock.bind(serverAddr)
        self.serverSock.listen(backlog)
        self.serverSock.settimeout(2)
        print("Listening to peer at: {}:{}".format(serverAddr[0], serverAddr[1]))
        while self.keepAlive:
            try:
                try:
                    client, addr = self.serverSock.accept()
                    #print(str((client, addr)))
                    self.listenThread = Thread(target=self.handlePeer, args=(client, addr))
                    self.listenThread.start()
                except socket.timeout: pass
            except KeyboardInterrupt:
                self.stopPeerServer()
                break

    def handlePeer(self, client, addr):
        print("Peer connected: {}".format(addr[0]))
        self.peersAddr.add(addr)

    def connectToPeer(self, addr):
        self.peerSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.peerSock.connect(addr)
        import time
        time.sleep(2)
        self.peerSock.shutdown(2)
        self.peerSock.close()

    def displayAllPeers(self):
        if len(self.peersAddr) == 0:
            print("No peers connected so far!")
        for i in self.peersAddr:
            print(i)

    def stopPeerServer(self):
        print("Shutting down the peer server....")
        self.keepAlive = False
        if self.serverSock is not None:
            try:
                self.serverSock.shutdown(2)
                self.serverSock.close()
            except socket.error: pass

    def handleInput(self):
        while self.keepAlive:
            try:
                command = input()
                if command is None or len(command) == 0: pass
                if command == "display":
                    self.displayAllPeers()
                if command == "exit":
                    self.stopPeerServer()
            except EOFError as e:
                break

if __name__=="__main__":
    fastShareServer = FastShareServer()
    Thread(target=fastShareServer.handleInput).start()
    #fastShareServer.connectToPeer(("192.168.77.128", 1947))
    fastShareServer.startPeerServer()
    #fastShareServer.displayAllPeers()