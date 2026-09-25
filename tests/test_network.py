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
print("network OK")
