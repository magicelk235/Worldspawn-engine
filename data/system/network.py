import json, socket, struct, threading, queue

MAX_MESSAGE_SIZE = 16 * 1024 * 1024  # refuse absurd length prefixes from bad peers
# how much may be waiting to go out to one peer before it counts as gone:
# room for a message of the largest size and as much again
MAX_BACKLOG = 2 * MAX_MESSAGE_SIZE
# how long a dropped peer gets to take what was still queued for it - the
# reason it was kicked, say - before its socket is closed regardless
DROP_GRACE = 5.0

def closeSocket(sock):
    # shutdown wakes any thread blocked in recv and pushes the FIN out
    # immediately; on Linux a bare close() can leave both hanging
    try:
        sock.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass
    try:
        sock.close()
    except OSError:
        pass

def encodeMessage(data) -> bytes:
    payload = json.dumps(data).encode()
    return struct.pack(">I", len(payload)) + payload

def recvall(sock, n):
    data = bytearray()
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data.extend(packet)
    return bytes(data)

def receiveMessage(sock):
    rawSize = recvall(sock, 4)
    if rawSize == None:
        return None
    size = struct.unpack(">I", rawSize)[0]
    if size > MAX_MESSAGE_SIZE:
        return None
    raw = recvall(sock, size)
    if raw == None:
        return None
    return json.loads(raw.decode())

class Sender:
    """The outgoing half of one connection, written out on a thread of its own.

    A peer that stops reading - a laptop shut mid-game, a window held still -
    fills the socket's buffers, and a send made from the game loop then waits
    for it, with everybody else's game waiting too. Messages queue here
    instead, and a peer that falls MAX_BACKLOG behind is cut off rather than
    waited for.
    """
    def __init__(self, sock):
        self.sock = sock
        self.queue = queue.Queue()
        self.backlog = 0
        self.lock = threading.Lock()
        self.timer = None    # the DROP_GRACE deadline, once finish() has run
        self.done = False    # the writer has stopped and closed the socket
        threading.Thread(target=self.writeLoop, daemon=True).start()

    def send(self, payload:bytes) -> bool:
        """Queue one encoded message; False when the peer is too far behind."""
        with self.lock:
            if self.backlog + len(payload) > MAX_BACKLOG:
                return False
            self.backlog += len(payload)
        self.queue.put(payload)
        return True

    def finish(self) -> None:
        """Close once what is queued has gone out, or after DROP_GRACE at most.

        Safe to call more than once, and after the writer has already stopped.
        """
        with self.lock:
            if self.done or self.timer != None:
                return
            self.timer = threading.Timer(DROP_GRACE, closeSocket, args=(self.sock,))
        self.timer.daemon = True
        self.timer.start()
        self.queue.put(None)

    def writeLoop(self):
        while True:
            payload = self.queue.get()
            if payload == None:
                break
            try:
                self.sock.sendall(payload)
            except OSError:
                break
            with self.lock:
                self.backlog -= len(payload)
        # also wakes the reader, which is what reports the peer gone
        closeSocket(self.sock)
        with self.lock:
            self.done = True
            timer = self.timer
        if timer != None:
            timer.cancel()

class HostNetwork:
    def __init__(self, port:int):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(("", port))
        self.server.listen()
        self.clients:dict[str,socket.socket] = {}
        self.senders:dict[str,Sender] = {}
        self.messages = queue.Queue()
        self.nextClient = 0
        self.lock = threading.Lock()
        threading.Thread(target=self.acceptLoop, daemon=True).start()

    def acceptLoop(self):
        while True:
            try:
                sock, _ = self.server.accept()
            except OSError:
                return
            with self.lock:
                clientID = f"client{self.nextClient}"
                self.nextClient += 1
                self.clients[clientID] = sock
                self.senders[clientID] = Sender(sock)
            self.messages.put((clientID, {"type": "connected"}))
            threading.Thread(target=self.readLoop, args=(clientID, sock), daemon=True).start()

    def readLoop(self, clientID, sock):
        while True:
            try:
                message = receiveMessage(sock)
            except (OSError, ValueError):
                message = None
            if message == None:
                self.dropClient(clientID)
                self.messages.put((clientID, {"type": "disconnected"}))
                return
            self.messages.put((clientID, message))

    def dropClient(self, clientID):
        with self.lock:
            self.clients.pop(clientID, None)
            sender = self.senders.pop(clientID, None)
        if sender != None:
            # what was queued before still goes out, so a refused join or a
            # kick arrives with its reason, and then the socket closes
            sender.finish()

    def sendTo(self, clientID, data):
        with self.lock:
            sender = self.senders.get(clientID)
        if sender == None:
            return
        if not sender.send(encodeMessage(data)):
            # it has stopped reading: that costs this client its connection,
            # not everybody else their game
            self.dropClient(clientID)
            self.messages.put((clientID, {"type": "disconnected"}))

    def broadcast(self, data):
        with self.lock:
            clients = list(self.clients.keys())
        for clientID in clients:
            self.sendTo(clientID, data)

    def close(self):
        # on Linux closing a listening socket does not wake the thread
        # blocked in accept on it; shutting it down first does
        closeSocket(self.server)
        with self.lock:
            senders = list(self.senders.values())
            self.clients.clear()
            self.senders.clear()
        for sender in senders:
            sender.finish()

class ClientNetwork:
    def __init__(self, ip:str, port:int):
        self.sock = socket.create_connection((ip, port), timeout=5)
        self.sock.settimeout(None)
        self.messages = queue.Queue()
        self.connected = True
        self.sender = Sender(self.sock)
        threading.Thread(target=self.readLoop, daemon=True).start()

    def readLoop(self):
        while True:
            try:
                message = receiveMessage(self.sock)
            except (OSError, ValueError):
                message = None
            if message == None:
                self.connected = False
                # the writer would otherwise wait on its queue forever and
                # keep the socket open with it
                self.sender.finish()
                return
            self.messages.put(message)

    def send(self, data):
        if not self.sender.send(encodeMessage(data)):
            # a host that has stopped reading is as good as gone
            self.close()

    def close(self):
        # what was sent just before still goes out, as it does for a peer the
        # host drops
        self.sender.finish()
        self.connected = False
