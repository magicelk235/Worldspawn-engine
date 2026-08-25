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
- **Packages** — modular game content under `packages/`, each with `settings.yaml`, `domains.yaml`, and a core extension (see the package API below)
- **Saved worlds** — `core.saveWorld(name)` / `core.loadWorld(name)` write a world folder under `save/` (sprites as JSON, settings as YAML, banned players included); packages persist their own state through optional `saveState`/`loadState` hooks
- **Rendering** — camera follows the player, render-order layering with y-sorting, and automatic culling of sprites that are offscreen or in another dimension
- **Online play (v3)** — a host runs the world, clients join it:

```python
core.host(5599, password="hunter2", sendRate=2)    # host: optional password, sync every 2nd cycle
core.join("192.168.1.10", 5599, identity=myId, password="hunter2")
```

The host streams per-client delta snapshots: only changed sprite fields travel, and a missing id means the sprite is gone. What each client sees is decided by `filterVisible(clientID, sprites)`, which packages can replace (`core.createFunction("filterVisible", fn)`) for distance or dimension culling. Clients send held keys, mouse position, and discrete events (key presses, mouse buttons, wheel); the host feeds them into a per-client `InputManager`. Packages exchange their own messages with `core.send(data, clientID=None)` and read them from the `networkMessage` event.

The wire format is JSON over length-prefixed TCP. Hosts can require a password and can `core.kick(clientID)` or `core.ban(clientID)` players; bans persist with the saved world. There is no encryption — play on networks you trust.

## Checks

Every push runs the suite on GitHub Actions. Locally they are plain scripts (headless — no window will open):

```bash
for t in tests/test_*.py; do python "$t"; done
```
