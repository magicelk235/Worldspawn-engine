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
