import threading
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import harness

ROOT = harness.buildRoot()

import data.core
core = data.core.Core()
core.host(5599, password="hunter2", sendRate=2)
# a sprite the visibility filter hides from every client
secret = core.getGroup1("object1")(core,(300,300,"word"))
core.addObjectByID(secret,"secret")
def filterVisible(self,clientID,sprites):
    return {id:obj for id,obj in sprites.items() if id != "secret"}
core.createFunction("filterVisible",filterVisible)

# has to outlive the client subprocess, which test_online gives 90 seconds and
# which spends up to 6 seconds on each of its waits. A host that shuts down
# mid run closes the socket and fails whichever wait happens to be open, which
# looks like a networking bug rather than a busy machine.
threading.Timer(150.0, lambda: setattr(core,"running",False)).start()
print("HOST READY", flush=True)
core.main()
