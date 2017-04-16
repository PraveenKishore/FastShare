import threading
from fastshare import FastShareClient
import sys

f = []

def run():
    for i in range(1995, 2000):
        temp = FastShareClient.FSClient(port=i)
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
        temp = FastShareClient.FSClient(port=i)
        threading.Thread(target=temp.startListening).start()
        temp.cleanupTempDir()
        if not temp.register():
            sys.exit(0)
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