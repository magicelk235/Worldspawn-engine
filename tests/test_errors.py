import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import harness

ROOT = harness.buildRoot()

import data.core

core = data.core.Core()
core.raiseError("testError","something broke")
core.clearEvents()  # errors become visible next cycle, like every event
assert core.errorHappened("testError")
assert not core.errorHappened("otherError")
assert core.getErrors("testError")[0].message == "something broke"
assert core.running == True

# A handled error is reported to the player by whoever raised it, so the log
# gets one line and no traceback: a refused connection that prints a stack
# reads like a crash to anyone running the game.
import contextlib, io

captured = io.StringIO()
with contextlib.redirect_stderr(captured):
    core.raiseError("connectionFailed","no route to host")
quiet = captured.getvalue()
assert "connectionFailed: no route to host" in quiet, quiet
assert "Traceback" not in quiet and "File \"" not in quiet, \
    f"a handled error must not print a stack:\n{quiet}"

captured = io.StringIO()
with contextlib.redirect_stderr(captured):
    core.raiseError("fatalError","dead",fatal=True)
loud = captured.getvalue()
assert "File \"" in loud, f"a fatal error should still say where it came from:\n{loud}"
assert core.running == False, "fatal error must stop the engine"

# --- event names --------------------------------------------------------------

# A package registering its own "error" or "timer" event used to get a second
# id under the engine's name: raised errors went to the new id while
# errorHappened kept listening on the old one, and the main loop, which waits
# for "timer", stopped ticking. The name is refused instead.
from data.system import events
for taken in ("error", "timer"):
    try:
        events.EventRegister.register(taken, lambda: None)
        refused = False
    except ValueError:
        refused = True
    assert refused, f"a second event named {taken} was registered"
core.raiseError("stillHeard","after a refused registration")
core.clearEvents()
assert core.errorHappened("stillHeard"), "errors stopped arriving"
print("errors OK")
