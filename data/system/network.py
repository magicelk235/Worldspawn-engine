import json, socket, struct, threading, queue

MAX_MESSAGE_SIZE = 16 * 1024 * 1024  # refuse absurd length prefixes from bad peers

def sendMessage(sock, data) -> None:
    payload = json.dumps(data).encode()
    sock.sendall(struct.pack(">I", len(payload)) + payload)

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

class HostNetwork:
    def __init__(self, port:int):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(("", port))
        self.server.listen()
        self.clients:dict[str,socket.socket] = {}
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
            sock = self.clients.pop(clientID, None)
        if sock != None:
            try:
                sock.close()
            except OSError:
                pass

    def sendTo(self, clientID, data):
        with self.lock:
            sock = self.clients.get(clientID)
        if sock != None:
            try:
                sendMessage(sock, data)
            except OSError:
                self.dropClient(clientID)
                self.messages.put((clientID, {"type": "disconnected"}))

    def broadcast(self, data):
        with self.lock:
            clients = list(self.clients.keys())
        for clientID in clients:
            self.sendTo(clientID, data)

    def close(self):
        try:
            self.server.close()
        except OSError:
            pass
        with self.lock:
            socks = list(self.clients.values())
            self.clients.clear()
        for sock in socks:
            try:
                sock.close()
            except OSError:
                pass

class ClientNetwork:
    def __init__(self, ip:str, port:int):
        self.sock = socket.create_connection((ip, port), timeout=5)
        self.sock.settimeout(None)
        self.messages = queue.Queue()
        self.connected = True
        threading.Thread(target=self.readLoop, daemon=True).start()

    def readLoop(self):
        while True:
            try:
                message = receiveMessage(self.sock)
            except (OSError, ValueError):
                message = None
            if message == None:
                self.connected = False
                return
            self.messages.put(message)

    def send(self, data):
        try:
            sendMessage(self.sock, data)
        except OSError:
            self.connected = False

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass
        self.connected = False
