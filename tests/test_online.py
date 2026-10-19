import os, subprocess, sys, time
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

host = subprocess.Popen([sys.executable, os.path.join(root,"tests","online_host.py")],
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
try:
    # the engine prints package-loading noise first; scan for the ready marker
    ready = False
    deadline = time.time() + 15
    while time.time() < deadline:
        line = host.stdout.readline()
        if not line:
            break
        if "HOST READY" in line:
            ready = True
            break
    assert ready, "host failed to start"
    time.sleep(1.0)
    client = subprocess.run([sys.executable, os.path.join(root,"tests","online_client.py")],
                            capture_output=True, text=True, timeout=90)
    print(client.stdout)
    print(client.stderr, file=sys.stderr)
    assert "online OK" in client.stdout, "client checks failed"
finally:
    host.kill()
print("online e2e OK")

# --- host and client logic, in this process ----------------------------------
#
# One core is taken through hosting and joining by hand. Most messages go
# straight into its queue, where a wire would only make the checks slower.

import json, socket, struct
sys.path.insert(0, os.path.join(root, "tests"))
import harness

ROOT = harness.buildRoot()
# a prefab a client cannot rebuild from (core, pos) alone
with open(os.path.join(ROOT,"packages","package","sprites","group1","coin.py"),"w") as f:
    f.write("import data.sprites.sprite\n"
            "class coin(data.sprites.sprite.Sprite):\n"
            "    def __init__(self, core, pos, value):\n"
            "        self.value = value\n"
            "        super().__init__(core, pos)\n"
            "def getObject():\n"
            "    return coin\n")

import data.core
from data.system import network

def freePort():
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    return port

def frame(message):
    payload = json.dumps(message).encode()
    return struct.pack(">I", len(payload)) + payload

def hostFor(seconds):
    for _ in range(int(seconds / 0.02)):
        core.hostUpdate()
        time.sleep(0.02)

core = data.core.Core()

# kick and ban with nobody connected used to look for state only host() made
core.ban("cheater")
core.kick("nobody")
assert core.bannedPlayers == {"cheater"}
core.bannedPlayers = set()

# a broadcast goes to the clients that were let in, not to a socket that has
# connected and never said hello, let alone given the password
port = freePort()
assert core.host(port, password="pw")
lurker = socket.create_connection(("127.0.0.1", port))
guest = socket.create_connection(("127.0.0.1", port))
guest.sendall(frame({"type":"hello","identity":"guest","password":"pw"}))
deadline = time.time() + 5
while "guest" not in core.clientTransports and time.time() < deadline:
    hostFor(0.02)
assert "guest" in core.clientTransports, "the guest was not let in"
core.send({"kind":"chat","text":"members only"})
lurker.settimeout(0.5)
try:
    leaked = lurker.recv(4096)
except socket.timeout:
    leaked = None
assert leaked == None, f"a broadcast reached a socket that never gave the password: {leaked!r}"

# whatever a client sends, the host keeps running: messages that are not an
# object, or input of the wrong shape, used to raise out of hostUpdate. (A bare
# null never gets that far; the transport takes it for a closed socket.)
for message in ([1,2], "text", 5, {"type":"input"},
                {"type":"input","keys":5,"mouse":[0,0]},
                {"type":"input","keys":[["d"]],"mouse":[0,0]},
                {"type":"input","keys":["d"],"mouse":7},
                {"type":"input","keys":["d"],"mouse":[1,2,3]},
                {"type":"input","keys":[],"mouse":[0,0],"events":[{"type":[1]}]},
                {"type":"custom"}):
    guest.sendall(frame(message))
hostFor(0.5)
assert "guest" in core.clientTransports, "a malformed message cost the guest its place"
assert core.getInputManager("guest").keys == set(), "input of the wrong shape reached the input manager"

# Joining another world while hosting this one ends the hosting. The port and
# the guests used to stay open with nothing serving them, their input piling
# up in a queue nobody read.
elsewhere = network.HostNetwork(freePort())
assert core.join("127.0.0.1", elsewhere.server.getsockname()[1], identity="visitor")
guest.settimeout(2)
try:
    while guest.recv(65536):
        pass
    guestReleased = True
except socket.timeout:
    guestReleased = False
assert guestReleased, "the guests of a world no longer hosted were left connected"
try:
    socket.create_connection(("127.0.0.1", port), timeout=1).close()
    stillListening = True
except OSError:
    stillListening = False
assert not stillListening, "the hosting port stayed open after joining elsewhere"
assert "guest" not in core.inputMangers and "guest" not in core.clientTransports

# Welcomed, a client hands its world over to the host. A sprite built here
# before joining, or kept from an earlier session, used to stay on screen for
# good whenever the host never streamed that id - a filterVisible hiding the
# host's own player was enough.
local = core.getGroup1("object1")(core,(5,5,"word"))
core.addObjectByID(local,"local")
streamed = {"rect":{"x":20,"y":20,"w":0,"h":0,"dimension":"word"},
            "currentAnimation":"default","drawIndex":3}
core.network.messages.put({"type":"welcome","clientID":"visitor"})
core.network.messages.put({"type":"delta","removed":[],"changed":{
    "visitor":{"prefabPath":"group1.object1","data":streamed},
    "coin":{"prefabPath":"group1.coin","data":streamed}}})
core.clientNetworkUpdate()
assert core.userID == "visitor"
assert core.getObject("local") == None and core.getObject("main") == None, \
    "the client kept sprites the host never sent"
assert core.getObject("visitor") != None, "the streamed sprite did not arrive"
# one sprite the client cannot rebuild costs that sprite, not the client
core.clearEvents()
assert core.getObject("coin") == None and core.errorHappened("spriteNotRestored")
# nor does one whose prefab does not exist here, and it is named in an error
core.network.messages.put({"type":"delta","removed":[],"changed":{
    "ghost":{"prefabPath":"group1.gone","data":streamed}}})
core.clientNetworkUpdate()
core.clearEvents()
assert core.getObject("ghost") == None
assert any("ghost (group1.gone)" in event.message for event in core.getErrors("spriteNotRestored")), \
    "a streamed sprite of an unknown prefab was dropped without an error"

# back to hosting, recording what would be sent instead of sending it
assert core.host(freePort())
elsewhere.close()
sent = []
core.network.sendTo = lambda transportID, data: sent.append((transportID, json.loads(json.dumps(data))))

# A field whose value comes out of its own toDict and is changed in place.
# The host's record of what a client was sent held the same list, so the
# next diff compared it with itself and the change never left.
class Trail:
    def __init__(self):
        self.points = []
    def toDict(self):
        return {"points": self.points}
    def fromDict(self, data):
        self.points = list(data["points"])

walker = core.getGroup1("object1")(core,(0,0,"word"))
walker.trail = Trail()
walker.objectData.clientData = walker.objectData.clientData + ["trail"]
core.addObjectByID(walker,"walker")
core.network.messages.put(("t1", {"type":"hello","identity":"watcher"}))
core.hostUpdate()
walker.trail.points.append([1,2])
sent.clear()
core.syncClients()
deltas = [data for _, data in sent if data["type"] == "delta"]
trail = deltas[-1]["changed"].get("walker",{}).get("data",{}).get("trail") if deltas else None
assert trail == {"points":[[1,2]]}, f"a change made in place was never sent: {deltas}"

# Dropped and straight back: the old socket's end and the new hello are read
# in the same cycle. The client used to be reported gone and back at once,
# and a package that despawns on the one left it with no character.
core.clearEvents()
core.network.messages.put(("t1", {"type":"disconnected"}))
core.network.messages.put(("t2", {"type":"hello","identity":"watcher"}))
core.hostUpdate()
core.clearEvents()
assert [event.clientID for event in core.getEventList("clientConnected")] == ["watcher"]
assert core.getEventList("clientDisconnected") == [], "a client that came straight back was reported gone"
assert core.clientTransports == {"watcher": "t2"}

# Kicked, a client's messages that nobody has read yet go with it. They name
# the client and not the connection, so a second "kick me" read before the
# first was acted on used to kick the player again once they were back.
core.network.messages.put(("t2", {"type":"custom","data":{"kind":"kick-me"}}))
core.network.messages.put(("t2", {"type":"custom","data":{"kind":"kick-me"}}))
core.hostUpdate()
core.clearEvents()
core.network.messages.put(("t2", {"type":"custom","data":{"kind":"kick-me"}}))
core.hostUpdate()          # the package kicks on the first; the last is still unread
assert "watcher" not in core.clientTransports, "the package did not kick"
core.clearEvents()
core.network.messages.put(("t3", {"type":"hello","identity":"watcher"}))
core.hostUpdate()
core.clearEvents()
core.hostUpdate()
assert core.clientTransports.get("watcher") == "t3", "a message from the kicked connection kicked the new one"

core.endNetworkSession()
lurker.close()
guest.close()
print("online logic OK")
