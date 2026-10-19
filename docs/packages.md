# Writing a game package

A Worldspawn game lives in a package: a folder under `packages/` that the engine loads when it starts. This page covers what the engine expects in that folder and the APIs a package uses. The last section builds a small coin game whose files are complete and run as shown.

Names in code are spelled the way the engine spells them, including `inputMangers` and `addExcluciveVector`.

## Running a game

The engine imports its code from `data/` and loads packages from `packages/`, both relative to the working directory. It reads every package's `assets/` folder the moment `data.core` is imported, and saved worlds go to `save/` in the same directory. A game folder looks like this:

```
mygame/
  data/        the engine's data/ folder, copied or symlinked
  packages/
    coins/     your package
  main.py
```

`main.py` is the one from the engine repository:

```python
# main.py
import data.core

core = data.core.Core()
core.main()
```

Install the engine's requirements (`pip install -r requirements.txt` in the engine repository), then start the game from inside the game folder:

```bash
cd mygame
python main.py
```

The engine clone is a game folder too, so you can also put your package in its `packages/` folder. Everything in `packages/` loads into every world. To keep a game in its own folder instead, run `ln -s /path/to/Worldspawn-engine/data data` inside it, or copy the folder.

`Core()` opens the window, loads the packages and runs each package's `__init__`. `core.main()` runs the game loop until `core.running` is False, which happens when the window is closed, when a fatal error is raised, or when your code sets it.

If the working directory is wrong but `data` still imports, the engine starts with no packages and draws every texture as the missing-texture checker. If you start the engine from a script that lives somewhere else, change into the game folder and put it on `sys.path` before the import:

```python
import os
import sys

os.chdir("/path/to/mygame")
sys.path.insert(0, os.getcwd())
import data.core
```

To run without a window, for a dedicated host or a test, set two environment variables before `data.core` is imported, for example on the command line:

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python main.py
```

## Package layout

```
packages/coins/
  settings.yaml    name and dependencies
  domains.yaml     domains this package declares; optional
  core.py          the class that is grafted onto the core; optional
  assets/
    textures/      .png and .gif
    sounds/        .ogg and .wav
    fonts/         .ttf and .otf
  sprites/         a domain folder
    base.py
    player/        a prefab folder
      base.py
      player.py    a prefab file
```

Only `settings.yaml` is required. Leave out `domains.yaml` if the package declares no domains, and `core.py` if it only adds prefabs to domains its dependencies declare. A folder in `packages/` without a `settings.yaml` isn't a package and is ignored.

### Folder names

Package and prefab folder names may only contain letters and digits (Python's `str.isalnum`). A package folder with any other character is skipped, and if it holds a `settings.yaml`, a `packageNotLoaded` error says so. A prefab folder with one is skipped without any message. The engine doesn't check domain names, but keep them to letters and digits as well.

The package folder has to match `name` in `settings.yaml`, or the package is skipped with `packageNotLoaded`.

Prefab files are imported as Python modules, so give them module names: `coin.py` or `goldcoin.py`, with no dots or dashes.

### settings.yaml

```yaml
name: coins              # required, and equal to the folder name
dependencies: [base]     # packages that load before this one; default []
used-domains: [sprites]  # domains this package has prefab folders in; default []
always-enabled: true     # default true
```

A package with `always-enabled: false` loads only when another package lists it in `dependencies`, which suits libraries. A dependency that isn't in `packages/` makes the dependent package fail with `packageNotLoaded`, and it doesn't load at all. The engine reads no other keys, so `version`, `author` and the like are free to use.

`used-domains` lists every domain this package puts prefab folders in, including the ones it declares itself. Prefab folders in a domain that isn't listed are ignored. Each listed domain must be declared by this package or one of its dependencies; an unknown name is skipped with a `domainNotFound` error.

### Load order

Loading a package takes four steps:

1. Its dependencies load, in the order listed, each with its own dependencies first.
2. The domains in its `domains.yaml` are created.
3. Its prefab files in every domain from `used-domains` are imported, and the getters and groups are made.
4. `core.py`, if there is one, is imported, its class is added to the core, and the class's `__init__` runs.

So a package's `__init__` can already use its own prefabs and everything its dependencies provide. Packages that don't depend on each other load in alphabetical order of their folder names. If the order of two packages matters, make one depend on the other rather than relying on their names.

## domains.yaml

A domain is a set of prefab folders that share one pair of add and remove rules. Most games need one domain, `sprites`, declared once:

```yaml
sprites:
  create-static-getter: true
  create-dynamic-getter: true
  add-function: |
    super(Core,self).addObjectByID(object,id)
  remove-function: |
    super(Core,self).removeObjectByID(id)
```

`create-static-getter` makes a getter `core.get<Prefab>(file)` for every prefab folder, returning the class from that file. Saved worlds and network sync find classes through the same table, so every domain whose objects go into the world needs it. Without it, the domain's sprites are dropped when a world loads, and clients never see them.

`create-dynamic-getter` keeps live groups of the objects in the world: `core.<domain>` and `core.<prefab>`, each a dict from id to object. It needs a `base.py` in the domain folder and in every prefab folder, each with a `getObject()` that returns the class the folder's objects derive from, such as `Sprite` or `AliveObject`.

`add-function` and `remove-function` hold Python source that the core runs with `exec` every time an object of this domain is added or removed. The code can use `self` (the core), `object` (the sprite) and `id`. Keep the line shown above: that call gives the object its id and puts it into the world, or takes it out. You can add your own lines before or after it. The engine reads these keys the first time an object of the domain is added or removed, and a missing one raises `KeyError` at that point.

A package that declares no domains leaves `domains.yaml` empty; a file holding only comments works too. To add prefabs to a domain that a dependency declared, list the domain in `used-domains` and don't declare it again:

```yaml
name: coinsplus
dependencies: [coins]
used-domains: [sprites]
```

Only the package that declares a domain needs the domain-level `base.py`. Every prefab folder still needs its own.

## Prefabs

A prefab file is a module at `packages/<package>/<domain>/<prefab>/<file>.py`. Every `.py` file in a prefab folder is imported at startup and has to define `getObject()`, and `base.py` counts. Files whose names start with two underscores are skipped.

```python
# packages/coins/sprites/coin/coin.py
from data.sprites.sprite import Sprite


class Coin(Sprite):
    pass


def getObject():
    return Coin
```

Define the class in the prefab file itself, even when it's a one-line subclass. The engine works out an object's domain, prefab and `prefabPath` from the module its class was defined in, so a class imported from somewhere else can't be added to the world.

`prefabPath` is `"<prefab>.<file>"`, so `"coin.coin"` here. Saves and network messages store it, and `core.getObjectByPrefabPath("coin.coin")` turns it back into the class.

### Getters and groups

```python
Coin = core.getCoin("coin")    # static getter: prefab folder coin, file coin.py
coin = Coin(core, (40, 0, "world"))
core.addObjectByID(coin, "coin1")
core.coin                      # dynamic group for the prefab: {"coin1": coin}
core.sprites                   # every object in the world, from every domain
```

A getter's name is `get` plus the folder name passed through `str.capitalize()`, which also lowercases everything after the first letter. A folder called `bigCoin` therefore gives `core.getBigcoin`, not `getBigCoin`. Lowercase, single-word folder names avoid the surprise.

`core.sprites` is the world: the core updates, draws, saves and streams what is in it. A domain named `sprites` uses that same dict as its group. A domain with any other name gets its own group, which holds only that domain's objects.

When two packages have the same prefab folder in a domain, they share one getter and one group. A file with the same name in the dependent package replaces the dependency's class, both for new objects and for loading saves.

### Name clashes

Groups and getters are attributes of the core, so a folder name can collide with something the core already has:

- A domain or prefab folder whose group would replace a core attribute (`host`, `network`, `packages`, `mode` and so on) raises `groupNameTaken`. Its prefabs still load, but `core.<name>` keeps meaning the engine's attribute.
- A prefab folder whose getter already exists raises `getterNameTaken` and gets no getter. A folder called `object` would otherwise have replaced `getObject`. Its classes are still reachable through `getObjectByPrefabPath`.

In both cases, rename the folder.

## The core class

`core.py` holds a class and a `getObject()` that returns it:

```python
class Coins:
    def __init__(self):
        # self is the engine's Core object
        self.coinsSpawned = 0


def getObject():
    return Coins
```

The engine appends this class to `Core.__bases__` and calls `Coins.__init__(core)`. Every method of the class becomes a method of the core, and every attribute you set on `self` lands on the core. `__init__` runs once per process, inside `Core()`, before `host()` or `join()` can be called. It runs the same way offline, on a host and on every client.

Pick attribute names the engine doesn't use. Assigning `self.mode`, `self.network`, `self.running`, `self.sprites` or `self.group`, for example, overwrites engine state without an error. `dir(core)` shows what is taken.

### Method lookup

A method that `Core` already defines, or that an earlier package defines, wins over yours without a warning. Defining `update` or `getObject` in your class has no effect, and a package can't override a method of a package it depends on by defining the same name.

To replace or wrap a method, use `core.createFunction(name, function)`. It binds the function to the core as an instance attribute, which takes precedence over every class:

```python
def everything(core, clientID, sprites):
    return sprites


core.createFunction("filterVisible", everything)
```

When a wrapper calls one of your own methods, call it through your class, as in `Coins.worldUpdate(core)`. A method with the same name in an earlier package can't take its place that way.

### Hooks

The engine looks for these methods on each package's class and calls every package's own version, in load order. All of them are optional, and `self` is the core in each.

| Method | When it runs |
| --- | --- |
| `serverUpdate(self)` | Every cycle while hosting, after the sprites update and the clients' messages are handled. Never offline and never on a client. |
| `clientUpdate(self)` | Every cycle on a client, after the host's changes are applied and the input has been sent. |
| `saveState(self)` | During `saveWorld`. Return plain data: dicts, lists, strings, numbers, booleans and None. Tuples come back as lists. |
| `loadState(self, data)` | At the end of `loadWorld`, after the sprites are back, with what `saveState` returned. Skipped when the save holds nothing for this package. |

Because each package's hook is called separately, a game and the library it depends on can both define `serverUpdate`, and both run. `filterVisible` works differently: it is a core method that you replace with `createFunction`, as described under online play.

### Running world logic

Offline, the only game step in the main loop is `core.update()`, which updates every sprite in the world. `serverUpdate` doesn't run. For game rules that should run wherever the world lives, offline and on a host, wrap `update` in `__init__`:

```python
class Coins:
    def __init__(self):
        engineUpdate = self.update

        def update(core):
            engineUpdate()
            Coins.worldUpdate(core)

        self.createFunction("update", update)

    def worldUpdate(self):
        pass  # spawn things, run timers, check for a winner
```

A client never calls `core.update()`, so neither sprite `update()` methods nor this wrapper run there. The client shows what the host streams and runs `clientUpdate`.

| Code | Where it goes |
| --- | --- |
| World rules | The wrapped `update` (offline and host) |
| Clients joining, leaving or sending messages | `serverUpdate` (host) |
| Things only a client shows or plays | `clientUpdate` (client) |
| One sprite's behavior | That sprite's `update()` (offline and host) |

## Sprites

A sprite subclasses `data.sprites.sprite.Sprite` and describes itself in `getDefaultData`:

```python
from data.sprites.sprite import Sprite, SpriteData, Animation
from data.spatial.hitbox import Hitbox
from data.emitters.image import ImageData


class Lamp(Sprite):
    def getDefaultData(self):
        self.objectData = SpriteData(
            Hitbox(8, 8),
            {"default": Animation(ImageData(path="lamp"))},
        )


def getObject():
    return Lamp
```

`Sprite.__init__` starts by calling `getDefaultData`, which has to set `self.objectData`, unless you pass an `objectData` argument yourself. The base version gives a 0x0 hitbox and the missing-texture image.

### The constructor

Saved worlds and network sync rebuild every sprite with `cls(core, pos)` and then copy the stored fields onto it. If you write an `__init__`, every parameter after `pos` needs a default, and `super().__init__(core, pos)` comes first:

```python
    def __init__(self, core, pos, value=1):
        super().__init__(core, pos)
        self.value = value
```

A sprite whose class can't be built from `(core, pos)` alone is skipped with a `spriteNotRestored` error, both when a world loads and on clients.

`pos` is a tuple `(x, y, dimension)`, where `dimension` is any string, such as `"world"` or `"cave"`. Sprites only collide with sprites in the same dimension, and the camera only shows the dimension the player is in. You can assign `pos`, `x`, `y`, `axis` (an `(x, y)` pair) and `dimension`. `rect` is the hitbox in world coordinates, with `x`, `y`, `w`, `h`, `center` and `dimension`; the pygame rect is `rect.rect`.

`collideCheck(other)` is True when two sprites' hitboxes overlap in the same dimension, and `collideCheckRect(rect)` tests against a rect. Both take an optional `additionalRange` that widens the check.

### Adding and removing

A sprite does nothing until it is in the world: it isn't updated, drawn, saved or streamed.

```python
coin = core.getCoin("coin")(core, (40, 0, "world"))
core.addObjectByID(coin, "coin1")   # or let the core pick an id: newID = core.addObject(coin)
core.getObject("coin1")             # the sprite, or None
core.removeObjectByID("coin1")      # or core.removeObject(coin)
```

Adding under an id that is already in use removes the sprite that had it. Each add and remove posts an `objectCreated` or `objectRemoved` event carrying the `id`.

### Sprite data

`SpriteData` takes these fields:

| Field | Meaning |
| --- | --- |
| `hitbox` | `Hitbox(w, h, xOffset=0, yOffset=0)`: the collision box, placed at `pos` plus the offset |
| `animations` | A dict from name to `Animation`, which must contain `"default"` |
| `clientData` | Attribute names that are sent to clients and saved |
| `saveData` | Attribute names that are saved but not sent |
| `displayByDirectionX`, `displayByDirectionY` | Move the image anchor to the side the sprite faces, for art that is mirrored as it turns |

`Animation` takes these:

| Field | Default | Meaning |
| --- | --- | --- |
| `imageData` | `ImageData()` | The picture |
| `countDown` | `-1` | Cycles before switching to `nextAnimation`; -1 never switches |
| `nextAnimation` | `"default"` | What plays after the countdown |
| `weight` | `1` | `setAnimation` only switches to an animation at least this heavy |
| `moveable` | `True` | False holds the sprite still while the animation plays |
| `displayType` | `DisplayType.topLeft` | Where the image sits on the hitbox when their sizes differ: `center`, `bottomLeft` and so on, from `data.spatial.rect` |
| `startFunc`, `endFunc` | do nothing | Called with the sprite when the animation starts and when it ends |

`sprite.setAnimation(name)` switches when the weight allows it, and asking for the animation that is already playing restarts its countdown. `sprite.loadAnimation(name)` always switches, and `sprite.addAnimationToQueue(name)` plays `name` when the current countdown ends. `sprite.currentAnimation` holds the name of the one playing, and every change posts a `switchAnimation` event.

`ImageData` is a frozen dataclass, and every field is optional:

| Field | Meaning |
| --- | --- |
| `path` | The texture name; see the assets section |
| `scaleSize` | `(w, h)` to scale to |
| `cutSize` | `(w, h)` to crop to from the top left; a larger size tiles the image |
| `flipX`, `flipY` | Mirror the image |
| `color` | RGBA multiplied into the pixels; `(255, 255, 255, 255)` leaves them alone |
| `angle` | Rotation in degrees |
| `factoredSize` | An extra scale factor |
| `renderOrder` | The draw layer, 4 by default; see drawing below |
| `text`, `fontSize` | Draw text instead of a texture; `path` then names a font |
| `resetGif` | False makes a gif, and its countdown, resume where they stopped instead of starting over |

A string field that starts with `@` reads an attribute of the sprite instead. `ImageData(path="hero", flipX="@directionX.value")` mirrors the art whenever the sprite faces right.

### update()

Override `update` for behavior. Call `super().update()`, which runs the animation countdown and applies movement, and return True to have the core remove the sprite:

```python
    def update(self):
        super().update()
        self.age += 1
        return self.age > 500  # True removes the sprite
```

Movement you add before `super().update()` applies in the same cycle. `update()` runs once per cycle, offline and on a host.

### Saved and streamed fields

Every sprite carries `rect`, `currentAnimation`, `drawIndex` and `visible`. Add your own attribute names to `clientData`, which is sent to clients when it changes and is saved, or to `saveData`, which is only saved. Names may be dotted paths into the sprite. The values have to survive JSON, so use numbers, strings, booleans, None, and lists or dicts of those; tuples come back as lists. An object with `toDict()` and `fromDict(data)` methods is stored through them, which is how `inventory` is saved.

When a sprite comes back from a save or arrives on a client, it is built with `cls(core, pos)` and then the stored values are set as attributes. Everything else has whatever value your constructor gives it.

Set `persistent = False` on a class to keep its sprites out of saved worlds. That suits menus, effects and anything else the game rebuilds by itself. Such sprites are still streamed to clients.

```python
class Sparkle(Sprite):
    persistent = False
```

`Sprite.__init__` also takes an optional `dictData`, a dict of attribute values. It doesn't apply them, because your subclass's attributes don't exist yet at that point. If you pass `dictData`, call `self.__post_init__()` at the end of your own `__init__`, which sets them:

```python
class Sign(Sprite):
    def __init__(self, core, pos, dictData={}):
        super().__init__(core, pos, dictData=dictData)
        self.label = "?"
        self.__post_init__()  # applies dictData, so it can set label


sign = Sign(core, (0, 0, "world"), dictData={"label": "Shop"})
```

Saves and network sync don't go through `dictData`.

### Drawing

The camera centers on the sprite whose id is `core.userID`: `"main"` offline and on a host, the client's id on a client. Until that sprite exists, the screen isn't redrawn. The window is 800x400 and scales when it is resized.

Each cycle the core draws the sprites in the world that are visible, in the player's dimension and near the screen. `hide()`, `show()`, `toggleVisibility()` and `isVisible()` control visibility. The order comes from `ImageData.renderOrder`:

- Below 4, sprites are drawn first, lowest value first. Use these layers for floors and shadows.
- At 4, the default, sprites are sorted by the vertical center of their hitbox, so a sprite lower on the screen covers one above it.
- Above 4, sprites are drawn last, lowest value first. Use these layers for effects and overlays.

When two sprites would otherwise tie, the one created first is drawn first.

### Alive objects, NPCs and widgets

`AliveObject`, in `data.sprites.aliveObject`, is a sprite with health, stats and an inventory. Its constructor is `(core, pos, objectData=None, tag=None, dictData={})`. Its data class `AliveObjectData` adds `health`, `damage`, `shield` (0 to 1), `speed`, `react`, `attackCountDown`, `visionRadius`, `inventorySize` and `rideData` to the `SpriteData` fields. `tag`, `health` and `inventory` are saved automatically. `attack(other)` and `applyDamage(damage, attacker=None)` deal damage. When health reaches 0, `update()` returns True and the object is removed, so a subclass that overrides `update` should end with `return super().update()`.

The stats are rebuilt from `AliveObjectData` and the inventory's items every cycle. Change them through the data or through item modifiers; a value assigned to `self.speed` is gone a cycle later.

Every alive object has an inventory, and its empty slots hold an item called `"none"`, which the inventory gets from `core.getItems("none")`. So a game with alive objects needs a prefab folder named `items`, in a domain with `create-static-getter`, holding at least `none.py`. A domain for things that never enter the world needs no other keys:

```yaml
static:
  create-static-getter: true
```

```python
# packages/coins/static/items/none.py
class NoItem:
    def getName(self):
        return "none"

    def getMax(self):
        return 0

    def applyModifiers(self, object, hand=False):
        pass


def getObject():
    return NoItem
```

Add `static` to `used-domains`. An item class needs `getName()`, `getMax()` (the stack size) and `applyModifiers(object, hand)`, which is called whenever stats are rebuilt. `Modifier.applyForList(modifiers, object, hand)` from `data.inventory.modifiers` applies a list of `Modifier(name, amount, mode=Mode.Set, handNeeded=True)` to the object, where `name` is the stat to change. `Mode` there also has `Add`, `Mul`, `MaxSet` and `MinSet`. `obj.inventory.addItemByCount(core.getItems("rock")(), 5)` hands an object items, and `obj.inventory.hasItem("rock")` checks for them.

`NpcObject`, in `data.sprites.npcObject`, is an alive object whose `NpcObjectData` adds `lootableList` and `spawners`. A `Lootable(itemID, count=1, chance=1.0)` puts items in its inventory when it is built. A `Spawner` makes it spawn other prefabs, named by `prefabPath`, around itself on a timer.

`UIObject`, in `data.sprites.uiObject`, is a widget. It is drawn at window coordinates, ignoring the camera, and only for players whose id is in its `visiblePlayers`. Its constructor is `(core, pos, objectData=None, visiblePlayers=None, interactivePlayers=None)`. `addVisiblePlayer(id)` shows it to a player, `addInteractivePlayer(id)` also lets that player use it, and `getInputList()` returns the input managers of its interactive players. A hidden widget stops updating. `addUiPart(part)` adds a child widget to the world, and the child hides and goes away with its parent. `visiblePlayers` and `interactivePlayers` are neither saved nor streamed, so a client rebuilds a streamed widget with nobody allowed to see it. Build a player's widgets on that player's machine, set `persistent = False` on them, and on a client build them in `clientUpdate`, since joining a host removes everything the client made before.

## Assets

Put files under the package's `assets/` folder:

| Folder | Files | Used by |
| --- | --- | --- |
| `assets/textures/` | .png, .gif | `ImageData(path=...)` |
| `assets/sounds/` | .ogg, .wav | `core.emittersManager.addSound(...)` |
| `assets/fonts/` | .ttf, .otf | `ImageData(text=..., path=...)` |

An asset's name is its path inside that folder without the extension: `assets/textures/coin.gif` is `"coin"`, and `assets/textures/ui/button.png` is `"ui/button"`. All packages share one set of names. When two packages ship the same name, the one that depends on the other wins; between unrelated packages, the folder that sorts last wins. Assets are read once, when `data.core` is imported, so new files need a restart.

A name that doesn't exist gives a 16x16 magenta and black checker, silence, or pygame's default font, without an error. If you see the checker, the path is wrong.

GIFs animate by themselves, at the frame durations stored in the file.

`ImageData(text="Score: 3", path="pixel", fontSize=16, color=(255, 220, 0, 255))` draws text with `assets/fonts/pixel.ttf`; leave `path` out for pygame's default font. Text is rendered white and tinted by `color`.

`core.emittersManager.addSound("coin", sprite.pos)` plays `assets/sounds/coin.ogg` (or `.wav`) at that position and returns an id. Volume and panning follow the distance to the local player, and the sound is silent beyond 300 pixels or in another dimension. `loop=True` repeats it, and `follow=spriteID` moves it along with a sprite. A sound plays only on the machine that starts it. To make a client hear one, send the client a message and play the sound in `clientUpdate`.

## Time

### Cycles

The engine runs in cycles. A cycle is meant to take 20 ms, which is 50 per second, but the real rate depends on the machine and can be lower, so measure durations in cycles rather than seconds. `core.cycles` counts the cycles since startup. Timers and animation countdowns are in cycles.

### Timers

The core has no named timers. Keep `Timer` objects as attributes instead:

```python
from data.managers.timeManager import Timer

self.spawnTimer = Timer(self, 50, repeat=True)  # in your core class's __init__

if self.spawnTimer.ended():  # True once every 50 cycles
    pass
```

`Timer(core, countDown, repeat=False)` counts `countDown` cycles. `ended()` is True once they have passed. A repeating timer then starts over, and a one-shot timer keeps returning True. A timer also has `remainingTime`, `stop()`, `start()` to resume, and `restart()`. A countdown of -1 never ends.

Sprites have named timers:

```python
self.addTimer("cooldown", 25)            # one shot, 25 cycles
if self.timerEnded("cooldown"):          # True once, then the timer is gone
    pass
self.addTimer("blink", 10, repeat=True)  # timerEnded("blink") is True every 10 cycles
```

They also have `getRemainingTime(name)`, `isTimer(name)`, `removeTimer(name)` and `getTimer(name)`. The name `"animation"` is taken by the sprite's animation countdown.

### Movement

Sprites move with vectors, which `super().update()` applies once per cycle:

```python
self.addVector((1, 0), 0.5)             # right for 25 cycles
self.addExcluciveVector((0, -1), 0.02)  # up for one cycle, unless already moving up
self.addVector((1, 1), 0.2, speed=3)    # down and right, 3 pixels per cycle on each axis
```

Each cycle a vector moves the sprite by `direction` times `speed` pixels. `time` is in seconds at the nominal rate, so every cycle uses up 0.02 of it. `speed` defaults to the sprite's `speed` attribute, which starts at 1. `addVector` adds its time to a vector that already points the same way, while `addExcluciveVector` does nothing in that case, which suits keys that are held down. Opposite vectors with the same speed cancel out. Vectors don't stop at anything, so check for collisions yourself.

## Input

Each player has an `InputManager`. `core.getInputManager(id)` returns one, and `core.inputMangers` is the dict of all of them. The local player's manager is filed under `core.userID`. On a host, each connected client has one under its client id, which is removed when the client disconnects. After that, `core.inputMangers.get(id)` returns None while `getInputManager(id)` raises `KeyError`.

```python
keys = core.inputMangers.get(player.id)
if keys != None:
    if keys.isKeyHeld("right"):
        pass
    if keys.isKeyPressed("space"):    # went down since the last cycle
        pass
    if keys.isKeyReleased("space"):
        pass
    if keys.mouseClicked():           # left button; mouseClicked(right=True) for the right one
        pass
    if keys.mouseScroll(down=True):
        pass
    mouseX, mouseY = keys.getMousePos()
```

Key names are pygame's (see `pygame.key.name`): `"a"` to `"z"`, `"0"` to `"9"`, `"up"`, `"down"`, `"left"`, `"right"`, `"space"`, `"return"`, `"escape"`, `"tab"`, `"f1"` to `"f12"`, `"left shift"`, `"right ctrl"`, `"[1]"` for keypad 1, and so on. `keys.keys` is the set of names held right now. Presses, releases, clicks and scrolls show up on the cycle after they happen.

`getMousePos()` is in window coordinates. `collideMouse(sprite)` compares the mouse with the sprite's hitbox as if the hitbox were in window coordinates too, which is right for widgets. For a point in the world, add the camera offset:

```python
me = core.getObject(core.userID)
screen = core.emittersManager.displayManager
mouseX, mouseY = keys.getMousePos()
worldPos = (mouseX + me.rect.center[0] - screen.halfW,
            mouseY + me.rect.center[1] - screen.halfH,
            me.dimension)
```

A client sends its held keys, mouse position, and key and mouse events to the host every cycle, and the host feeds them into that client's manager. Code that reacts to a player's input belongs on the host: in sprite updates, the wrapped `update` or `serverUpdate`.

## Events

Events are pygame events. The ones posted during a cycle can be read during the next one:

```python
for event in core.getEventList("clientConnected"):
    print(event.clientID)
if core.eventHappened("objectRemoved"):
    pass
```

Look lists up by name or by pygame event type, as in `core.getEventList(pygame.KEYDOWN)`. These are the engine's events and their fields:

| Name | Fields |
| --- | --- |
| `objectCreated`, `objectRemoved` | `id`, `objectType` |
| `clientConnected`, `clientDisconnected` | `clientID` |
| `networkMessage` | `clientID`, `data` |
| `error` | `name`, `message`, `fatal` |
| `cycleEnded` | `cycles` |
| `move` | `objectID` |
| `switchAnimation` | `newAnimation`, `oldAnimation`, `objectID` |
| `attack` | `attacker`, `attacked`, `remaining` |
| `healthChanged` | `healed`, `currentHealth`, `oldHealth` |
| `riderMount`, `riderDismount` | `rideID`, `riderID`, `remainingSlots` |

A sprite also keeps lists of the events it posted itself, so `sprite.eventHappened("move")` tells you whether that sprite moved during the last cycle.

Register your own events once, when your module is imported, and post them with `addEvent`:

```python
import pygame
from data.system import events


class Coins:
    coinCollected = events.EventRegister.register("coinCollected", None)

    def worldUpdate(self):
        for event in self.getEventList("coinCollected"):  # posted last cycle
            print(event.playerID)
        self.addEvent(pygame.event.Event(Coins.coinCollected, {"playerID": "main"}))
```

`EventRegister.register(name, createFunction)` returns the new event type and raises `ValueError` when the name is already registered. The second argument is only handed back by `EventRegister.create(name)`, which the engine never calls, so None works. A sprite's own `addEvent` posts to the core as well.

## Errors

The engine reports problems it has dealt with as `error` events instead of exceptions. `core.raiseError(name, message="", fatal=False)` raises one: it prints `[worldspawn error] name: message` to stderr and posts the event. `fatal=True` also prints a stack trace and stops the main loop. Like other events, errors can be read on the next cycle:

```python
for error in core.getErrors():  # or core.getErrors("worldNotFound")
    print(error.name, error.message)
if core.errorHappened("joinRejected"):
    pass
```

Errors raised while `Core()` loads the packages can be read once the first cycle is over. Functions that can fail also return False straight away, so check the return value when you need to react in the same cycle.

The engine raises these:

| Name | When |
| --- | --- |
| `packageNotLoaded` | A package folder has a bad name, a settings name that doesn't match, or a missing dependency |
| `groupNameTaken` | A domain or prefab folder's group would replace a core attribute |
| `getterNameTaken` | A prefab folder's getter would replace a core method |
| `domainNotFound` | A package lists a domain in `used-domains` that nobody declared |
| `worldNotSaved` | `saveWorld` couldn't write the world |
| `worldNotFound` | `loadWorld` found no readable save under that name |
| `worldCorrupt` | The save's sprite table isn't a mapping |
| `worldPartlyLoaded` | Some saved sprites couldn't be restored |
| `spriteNotRestored` | One sprite couldn't be rebuilt from a save or from the host |
| `hostFailed` | `host()` couldn't open the port |
| `alreadyHosting` | `host()` was called while already hosting |
| `connectionFailed` | `join()` couldn't reach the host |
| `joinRejected` | The host refused or kicked this client; the message gives the reason |
| `disconnected` | The connection to the host was lost |

## Saving worlds

```python
saved = core.saveWorld("slot1")   # False if the world couldn't be written
loaded = core.loadWorld("slot1")  # False if there was nothing readable to load
```

`saveWorld(name)` writes `save/<name>/sprites.json` and `save/<name>/settings.yaml` under the working directory, and returns True once both are written. The sprite file holds every sprite in the world except those with `persistent = False`, each with its `prefabPath`, `clientData` and `saveData`. The settings file holds the ban list and whatever each package's `saveState` returned. If a value can't be stored, such as a set in `saveData` or an object in `saveState`, `saveWorld` raises `worldNotSaved`, returns False and leaves the previous save as it was. A disk error raises `worldNotSaved` and then the `OSError`.

`loadWorld(name)` returns False with `worldNotFound` or `worldCorrupt` and leaves the world alone when it can't read the save. Otherwise it removes every sprite, rebuilds the saved ones, restores the ban list, calls each package's `loadState` and returns True. Sprites that can't be rebuilt are skipped and counted in a `worldPartlyLoaded` error, and one whose class raised also gets its own `spriteNotRestored`.

Only sprites, the ban list and `saveState` are saved. Timers, vectors and other core attributes are not. Loading removes the player too, so keep the player sprite persistent, or spawn it again after loading.

## Online play

### Hosting and joining

```python
core.host(5599, password="hunter2", sendRate=1)
core.join("192.168.1.10", 5599, identity="alice", password="hunter2")
```

`host(port, password=None, sendRate=1)` keeps the current world and starts accepting clients. It returns False with `hostFailed` or `alreadyHosting`. `sendRate=3` sends changes every third cycle instead of every cycle.

`join(ip, port, identity=None, password=None)` returns True once the connection is open, before the host has answered, and False with `connectionFailed`. When the host lets the client in, the client removes every sprite it had, `core.userID` becomes the identity, and from then on the world is whatever the host streams. When the host refuses, the client gets `joinRejected` with the reason (`"wrong password"`, `"banned"` or `"identity already belongs to the host"`) and goes back to playing offline. The same happens, with `disconnected`, when the connection drops. `core.mode` is `core.Mode.start` offline, `core.Mode.host` while hosting and `core.Mode.join` on a client.

The identity is a string that becomes the client's id on the host. Rejoining with the same identity makes you the same player. Without one, `join` makes up a random identity each time. `"main"` is refused, because that is the host's own player.

### Players

The camera follows the sprite whose id is `core.userID`, which is `"main"` offline and on the host, and the identity on a client. So a package spawns the local player in `__init__` under `core.userID`, and the host spawns one more player for each client under the client id:

```python
    def serverUpdate(self):
        for event in self.getEventList("clientConnected"):
            if self.getObject(event.clientID) == None:  # a reconnect fires this again
                player = self.getPlayer("player")(self, (0, 40, "world"))
                self.addObjectByID(player, event.clientID)
```

`clientConnected` and `clientDisconnected` show up in `serverUpdate` the cycle after they happen. A player sprite finds its input with `core.inputMangers.get(self.id)`, because a client's input manager on the host has the same id as the client's player. On a client, `__init__` runs too and spawns a `"main"` of its own, which joining removes.

### Messages

```python
core.send({"kind": "chat", "text": "hi"})                # client to host
core.send({"kind": "sound", "name": "coin"}, "alice")    # host to one client
core.send({"kind": "sound", "name": "coin"})             # host to every client
```

The data has to be JSON compatible. It arrives as a `networkMessage` event on the next cycle, where `event.data` is what was sent and `event.clientID` is the sender's id on the host and None on a client. Read them in `serverUpdate` on the host and in `clientUpdate` on a client. Offline, `send` does nothing.

On the host, `core.kick(clientID)` disconnects a client, which sees `joinRejected` with the reason `"kicked"`. `core.ban(clientID)` kicks the client and refuses that identity from then on. The ban list, `core.bannedPlayers`, is saved with the world.

Everything travels as JSON over TCP without encryption, so only play on networks you trust.

### What clients see

The host sends each client the sprites that `core.filterVisible(clientID, sprites)` returns, which by default is all of them, and after that only the `clientData` fields that changed. `saveData` never leaves the host. Replace the filter to hide things:

```python
def sameDimension(core, clientID, sprites):
    me = sprites.get(clientID)
    if me == None:
        return sprites
    return {id: sprite for id, sprite in sprites.items() if sprite.dimension == me.dimension}


core.createFunction("filterVisible", sameDimension)
```

A sprite that drops out of the filter is removed from that client and comes back once it passes again. On a client, sprite `update()` methods don't run: a streamed sprite shows the animation the host has it in, and gifs animate locally.

## Example: a coin game

The player walks around with the arrow keys, and a coin appears every 50 cycles, up to five at a time. Each coin spins for 30 cycles, flashes white for 5, and disappears when a player touches it, adding to that player's score. F5 saves the world and F9 loads it. The score shows in the window title, and the same files work as a host and as a client.

```
coinsgame/
  data/              the engine's data/ folder, copied or symlinked
  main.py            from "Running a game" above
  host.py
  join.py
  makeart.py
  packages/coins/
    settings.yaml
    domains.yaml
    core.py
    assets/textures/   made by makeart.py
    sprites/
      base.py
      player/base.py
      player/player.py
      coin/base.py
      coin/coin.py
```

```yaml
# packages/coins/settings.yaml
name: coins
used-domains: [sprites]
```

```yaml
# packages/coins/domains.yaml
sprites:
  create-static-getter: true
  create-dynamic-getter: true
  add-function: |
    super(Core,self).addObjectByID(object,id)
  remove-function: |
    super(Core,self).removeObjectByID(id)
```

The same `base.py` goes in the domain folder and in both prefab folders:

```python
# packages/coins/sprites/base.py
# Also save it as packages/coins/sprites/player/base.py and packages/coins/sprites/coin/base.py
from data.sprites.sprite import Sprite


def getObject():
    return Sprite
```

The player reads the input manager filed under its own id. Offline that is the local player's, and on a host each client's player gets that client's keys. The score is in `clientData`, so it is saved and clients can show it.

```python
# packages/coins/sprites/player/player.py
from data.sprites.sprite import Sprite, SpriteData, Animation
from data.spatial.hitbox import Hitbox
from data.emitters.image import ImageData

ARROWS = {"left": (-1, 0), "right": (1, 0), "up": (0, -1), "down": (0, 1)}


class Player(Sprite):
    def getDefaultData(self):
        self.objectData = SpriteData(
            Hitbox(16, 16),
            {"default": Animation(ImageData(path="player"))},
            clientData=["score"],
        )

    def __init__(self, core, pos):
        super().__init__(core, pos)
        self.speed = 2
        self.score = 0

    def update(self):
        keys = self.core.inputMangers.get(self.id)
        if keys != None:
            for name, direction in ARROWS.items():
                if keys.isKeyHeld(name):
                    self.addExcluciveVector(direction, 0.02)
        return super().update()


def getObject():
    return Player
```

```python
# packages/coins/sprites/coin/coin.py
from data.sprites.sprite import Sprite, SpriteData, Animation
from data.spatial.hitbox import Hitbox
from data.emitters.image import ImageData


class Coin(Sprite):
    def getDefaultData(self):
        self.objectData = SpriteData(
            Hitbox(8, 8),
            {
                # the spinning gif for 30 cycles, then a white flash for 5
                "default": Animation(ImageData(path="coin"), countDown=30, nextAnimation="flash"),
                "flash": Animation(ImageData(path="coinflash"), countDown=5),
            },
        )

    def update(self):
        super().update()
        for player in self.core.player.values():
            if self.collideCheck(player):
                player.score += 1
                return True  # collected, so the core removes the coin
        return False


def getObject():
    return Coin
```

The core class spawns the local player, runs the coin timer and the save keys in a wrapped `update`, and spawns a player for each client that joins. Coin ids come from `coinsSpawned`, which is why `saveState` keeps it: after loading, new coins carry on numbering instead of reusing the id of a coin that came back from the save.

```python
# packages/coins/core.py
import random

import pygame
from data.managers.timeManager import Timer


class Coins:
    def __init__(self):
        # self is the engine core. Every machine starts with its own player
        # under core.userID; on a client, joining a host replaces it.
        self.addObjectByID(self.getPlayer("player")(self, (0, 0, "world")), self.userID)
        self.coinTimer = Timer(self, 50, repeat=True)
        self.coinsSpawned = 0
        engineUpdate = self.update

        def update(core):
            engineUpdate()
            Coins.worldUpdate(core)

        self.createFunction("update", update)

    def worldUpdate(self):
        # runs offline and on the host
        if self.coinTimer.ended() and len(self.coin) < 5:
            self.coinsSpawned += 1
            pos = (random.randint(-150, 150), random.randint(-80, 80), "world")
            self.addObjectByID(self.getCoin("coin")(self, pos), f"coin{self.coinsSpawned}")
        keys = self.getInputManager(self.userID)
        if keys.isKeyPressed("f5"):
            self.saveWorld("coins")
        if keys.isKeyPressed("f9"):
            self.loadWorld("coins")
        Coins.showScore(self)

    def serverUpdate(self):
        for event in self.getEventList("clientConnected"):
            if self.getObject(event.clientID) == None:
                player = self.getPlayer("player")(self, (0, 40, "world"))
                self.addObjectByID(player, event.clientID)

    def clientUpdate(self):
        Coins.showScore(self)

    def showScore(self):
        me = self.getObject(self.userID)
        if me != None:
            pygame.display.set_caption(f"Coins: {me.score}")

    def saveState(self):
        return {"coinsSpawned": self.coinsSpawned}

    def loadState(self, data):
        self.coinsSpawned = data["coinsSpawned"]


def getObject():
    return Coins
```

`makeart.py` draws placeholder art with Pillow, which the engine already requires:

```python
# makeart.py
import os

from PIL import Image

folder = "packages/coins/assets/textures"
os.makedirs(folder, exist_ok=True)
Image.new("RGBA", (16, 16), (70, 140, 255, 255)).save(f"{folder}/player.png")
Image.new("RGBA", (8, 8), (255, 255, 255, 255)).save(f"{folder}/coinflash.png")
spin = [Image.new("RGBA", (8, 8), color) for color in [(255, 210, 0, 255), (200, 150, 0, 255), (255, 240, 140, 255)]]
spin[0].save(f"{folder}/coin.gif", save_all=True, append_images=spin[1:], duration=100, loop=0)
```

Run everything from the game folder:

```bash
python makeart.py
python main.py
```

For online play, one machine hosts and the others join:

```python
# host.py
import data.core

core = data.core.Core()
core.host(5599)
core.main()
```

```python
# join.py
import sys

import data.core

core = data.core.Core()
core.join(sys.argv[1], 5599, identity=sys.argv[2])
core.main()
```

```bash
python host.py
python join.py 127.0.0.1 alice   # in a second terminal, from the same folder
```

On the client, the arrow keys move alice's player on the host, and the host streams the result back. F5 and F9 only work on the host, because only the machine that owns the world runs `worldUpdate`.
