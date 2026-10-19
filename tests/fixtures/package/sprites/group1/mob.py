from data.sprites.npcObject import NpcObject, NpcObjectData
from data.sprites.sprite import Animation
from data.spatial.hitbox import Hitbox


class Mob(NpcObject):
    # written the way a package would: no constructor of its own, so a saved
    # world or a host's delta rebuilds it with cls(core, pos) and nothing else.
    # Its inventory clears slots with core.getItems("none"), so a check that
    # builds one has to provide the items first.
    def getDefaultData(self):
        self.objectData = NpcObjectData(Hitbox(8, 8), {"default": Animation()}, health=10)


def getObject():
    return Mob
