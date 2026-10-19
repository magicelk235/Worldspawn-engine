import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import harness

ROOT = harness.buildRoot()

from data.system.network import HostNetwork, ClientNetwork

host = HostNetwork(5598)
client = ClientNetwork("127.0.0.1", 5598)

clientID, message = host.messages.get(timeout=2)
assert message == {"type": "connected"} and clientID == "client0"

client.send({"type": "input", "keys": ["d"], "mouse": [0, 0]})
clientID, message = host.messages.get(timeout=2)
assert message["type"] == "input" and message["keys"] == ["d"]

host.broadcast({"type": "snapshot", "sprites": {}})
message = client.messages.get(timeout=2)
assert message["type"] == "snapshot"

client.close()
clientID, message = host.messages.get(timeout=2)
assert message == {"type": "disconnected"}
host.close()

# --- what a sprite hands over for streaming ---------------------------------

# A host keeps what each client was last sent and diffs the next sync against
# it, so the data a sprite hands over has to be a copy. A list passed along as
# itself is the live one: changed in place, it changed in the host's record
# too, the diff never saw it, and the client never heard about it.
import data.core

core = data.core.Core()
banner = core.getGroup1("object1")(core, (5, 5, "word"))
banner.tags = ["a"]
banner.objectData.clientData.append("tags")
streamed = banner.toData()
banner.tags.append("b")
assert streamed["tags"] == ["a"], f"streamed data follows the live list: {streamed['tags']}"

# --- a peer that stops reading ----------------------------------------------

# A guest whose machine goes to sleep stops reading but stays connected. A send
# to it used to wait for room in its socket, so once the buffers were full the
# host's loop stood still for everybody. Sends queue now, and a peer that
# falls far enough behind is let go instead of waited for.
import queue, socket, threading, time
from data.system import network

stalled = HostNetwork(0)
sleeper = socket.create_connection(("127.0.0.1", stalled.server.getsockname()[1]))
sleeperID, message = stalled.messages.get(timeout=2)
assert message == {"type": "connected"}
blob = {"type": "delta", "padding": "x" * (1024 * 1024)}
# The kernel takes as much as the two socket buffers hold before anything
# backs up in the queue, and those differ from one machine to the next.
# Enough sends to fill both and the backlog, with room to spare for buffers
# that grow while in use; once the peer is dropped the rest do nothing.
kernel = (sleeper.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)
          + stalled.clients[sleeperID].getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF))
sends = (network.MAX_BACKLOG + kernel) // len(blob["padding"]) + 64
sending = threading.Thread(target=lambda: [stalled.sendTo(sleeperID, blob) for _ in range(sends)],
                           daemon=True)
sending.start()
sending.join(10)
assert not sending.is_alive(), "sending to a peer that does not read held the sender up"
deadline = time.time() + 5
released = False
while not released and time.time() < deadline:
    try:
        clientID, message = stalled.messages.get(timeout=0.5)
    except queue.Empty:
        continue
    released = clientID == sleeperID and message == {"type": "disconnected"}
assert released, "a peer that stopped reading was never let go"
sleeper.close()
stalled.close()

# A client whose host goes away stops its writer and closes its socket; left
# waiting on its queue, the writer kept both for as long as the program ran.
baseline = threading.active_count()
clients = []
for _ in range(3):
    leaving = HostNetwork(0)
    client = network.ClientNetwork("127.0.0.1", leaving.server.getsockname()[1])
    leaving.messages.get(timeout=2)
    leaving.close()
    deadline = time.time() + 5
    while client.connected and time.time() < deadline:
        time.sleep(0.01)
    assert not client.connected, "the client never noticed its host was gone"
    clients.append(client)
deadline = time.time() + 5
while (threading.active_count() > baseline or any(client.sock.fileno() != -1 for client in clients)) \
        and time.time() < deadline:
    time.sleep(0.02)
assert threading.active_count() <= baseline, \
    f"a client left threads behind: {threading.active_count()} running, {baseline} before"
assert all(client.sock.fileno() == -1 for client in clients), "a client kept its socket open"

print("network OK")
