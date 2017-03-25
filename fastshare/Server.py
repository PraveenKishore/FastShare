import socket
from threading import Thread

SELF_SERVER_ADDR = ("127.0.0.1", 1947)

class  FastShareServer:
    def __init__(self):
        self.serverSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.peersAddr = set([])
        self.listenThread = None
        self.keepAlive = True

    def startPeerServer(self, serverAddr = SELF_SERVER_ADDR, backlog=15):
        self.serverSock.bind(serverAddr)
        self.serverSock.listen(backlog)
        while self.keepAlive:
            client, addr = self.serverSock.accept()
            self.listenThread = Thread(target=self.handlePeer, args=(client, addr))

    def handlePeer(self, client, addr):
        self.peersAddr.add(addr)
        print("Peer connected: {}".format(addr[0]))

    def displayAllPeers(self):
        for i in self.peersAddr:
            print(i)


if __name__=="__main__":
    fastShareServer = FastShareServer()
    fastShareServer.startPeerServer()
    fastShareServer.displayAllPeers()