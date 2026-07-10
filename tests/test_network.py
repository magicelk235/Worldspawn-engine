import os, sys, time
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,root); os.chdir(root)

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
