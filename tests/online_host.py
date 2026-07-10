import os, sys, threading
os.environ.setdefault("SDL_VIDEODRIVER","dummy")
os.environ.setdefault("SDL_AUDIODRIVER","dummy")
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,root); os.chdir(root)

import data.core
core = data.core.Core()
core.host(5599)
threading.Timer(8.0, lambda: setattr(core,"running",False)).start()
print("HOST READY", flush=True)
core.main()
