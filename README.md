# Worldspawn Engine

Worldspawn™ Copyright 2025© — a project started 8th April 2024. Originally a sandbox game (now continued separately as Worldspawn-game), Worldspawn today is a 2D game engine built on Pygame. The engine handles the system work for you — image types, object lifecycle, camera centering, display order — everything is customizable and easy to use.

## Setup

```bash
pip install -r requirements.txt
python main.py
```

## Features

- **Sprites & animations** — data-driven images (`ImageData`), gif animations via gif_pygame, weighted animation transitions with countdown timers
- **Movement** — time-based direction vectors that auto-merge opposites
- **Events** — custom event registration on top of Pygame's event system; errors are events too (`core.raiseError(name, message, fatal=False)`)
- **Packages** — modular game content under `packages/`, each with `settings.yaml`, `domains.yaml`, and a core extension (see `CLAUDE.md` for the structure)
- **Online play (v3)** — a host runs the world, clients join it:

```python
core.host(5599)                                    # host: your world accepts clients
core.join("192.168.1.10", 5599, identity=myId)     # client: join; identity persists across reconnects
```

The host streams per-client delta snapshots: only changed sprite fields travel, and a missing id means the sprite is gone. What each client sees is decided by `filterVisible(clientID, sprites)`, which packages can replace (`core.createFunction("filterVisible", fn)`) for distance or dimension culling. Clients send held keys, mouse position, and discrete events (key presses, mouse buttons, wheel); the host feeds them into a per-client `InputManager`. Packages exchange their own messages with `core.send(data, clientID=None)` and read them from the `networkMessage` event.

The wire format is JSON over length-prefixed TCP. There is no authentication or encryption yet — only play with people you trust, on networks you trust.

## Checks

No test framework; plain scripts:

```bash
python tests/test_boot.py
python tests/test_animation.py
python tests/test_errors.py
python tests/test_network.py
python tests/test_online.py
```
