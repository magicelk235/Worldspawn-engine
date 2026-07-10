import os, sys
os.environ.setdefault("SDL_VIDEODRIVER","dummy")
os.environ.setdefault("SDL_AUDIODRIVER","dummy")
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,root); os.chdir(root)

import data.core

core = data.core.Core()
core.raiseError("testError","something broke")
core.clearEvents()  # errors become visible next cycle, like every event
assert core.errorHappened("testError")
assert not core.errorHappened("otherError")
assert core.getErrors("testError")[0].message == "something broke"
assert core.running == True

core.raiseError("fatalError","dead",fatal=True)
assert core.running == False, "fatal error must stop the engine"
print("errors OK")
