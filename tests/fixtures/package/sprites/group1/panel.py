from data.sprites.uiObject import UIObject


class Panel(UIObject):
    # a widget with no constructor of its own, rebuilt with cls(core, pos)
    pass


def getObject():
    return Panel
