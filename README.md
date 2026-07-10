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
- **Online play (v2)** — a host runs the world, clients join it:

```python
core.host(5599)               # host: your world accepts clients
core.join("192.168.1.10", 5599)  # client: join a host's world
```

The wire format is JSON over TCP. There is no authentication or encryption yet — only play with people you trust, on networks you trust.

## Checks

No test framework; plain scripts:

```bash
python tests/test_boot.py
python tests/test_animation.py
python tests/test_errors.py
python tests/test_network.py
python tests/test_online.py
```
