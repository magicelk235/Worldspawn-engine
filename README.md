# Worldspawn Engine

A 2D game engine built on pygame. Worldspawn started in April 2024 as a sandbox game and slowly turned into the engine underneath it; the game itself now lives on separately as Worldspawn-game. The engine takes care of images, object lifecycle, the camera, draw order, input, saving, and online play. Your game goes in a package.

## Setup

```bash
pip install -r requirements.txt
python main.py
```

## What you get

- Sprites and animations: data-driven images, gif animations through gif_pygame, weighted animation transitions with countdown timers
- Movement: time-based direction vectors that merge opposite directions automatically
- Events: register your own events on top of pygame's. Errors are events too, raised with `core.raiseError(name, message, fatal=False)`
- Saved worlds: `core.saveWorld(name)` and `core.loadWorld(name)` write a world folder under `save/`, sprites as JSON and settings as YAML, ban list included. Packages can persist their own state with `saveState`/`loadState` hooks
- Rendering: the camera follows the player, sprites draw in layers with y-sorting, and anything offscreen or in another dimension gets culled

## Online play

A host runs the world and clients join it:

```python
core.host(5599, password="hunter2", sendRate=2)
core.join("192.168.1.10", 5599, identity=myId, password="hunter2")
```

The host streams per-client delta snapshots. Only changed sprite fields travel, and a missing id means the sprite is gone. Which sprites a client sees is decided by `filterVisible(clientID, sprites)`; packages can replace it through `core.createFunction("filterVisible", fn)` to cull by distance or dimension. Clients send held keys, the mouse position, and discrete events (key presses, mouse buttons, wheel), which the host feeds into a per-client `InputManager`. For everything else there is `core.send(data, clientID=None)`, delivered on the other side as a `networkMessage` event.

Identity is a string you pass to `join`. It becomes the client id and survives reconnects, so a player who drops can come back as themselves. Hosts can require a password, `core.kick(clientID)`, or `core.ban(clientID)`; bans persist with the saved world. The wire format is JSON over length-prefixed TCP. There is no encryption, so only play on networks you trust.

## Packages

Game content lives in `packages/<name>/` with three parts: `settings.yaml` (name, dependencies, used domains), `domains.yaml` (which sprite groups exist), and `core.py`, a class that gets grafted onto the engine core. That class can define lifecycle hooks (`serverUpdate`, `clientUpdate`, `saveState`, `loadState`) and react to events like `clientConnected` or `networkMessage`. The committed `packages/package/` is a small working example that the test suite runs against.

## Tests

Plain scripts, no framework. They run headless, so no window will open or steal focus:

```bash
for t in tests/test_*.py; do python "$t"; done
```

GitHub Actions runs the same suite on every push.

## License

MIT. See [LICENSE](LICENSE).
