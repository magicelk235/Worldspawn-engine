import os, sys, threading
os.environ.setdefault("SDL_VIDEODRIVER","dummy")
os.environ.setdefault("SDL_AUDIODRIVER","dummy")
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,root); os.chdir(root)

import data.core
core = data.core.Core()
core.host(5599, password="hunter2", sendRate=2)
# a sprite the visibility filter hides from every client
secret = core.getGroup1("object1")(core,(300,300,"word"))
core.addObjectByID(secret,"secret")
def filterVisible(self,clientID,sprites):
    return {id:obj for id,obj in sprites.items() if id != "secret"}
core.createFunction("filterVisible",filterVisible)

threading.Timer(60.0, lambda: setattr(core,"running",False)).start()
print("HOST READY", flush=True)
core.main()
