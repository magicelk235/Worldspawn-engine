import enum

class DisplayType(enum.Enum):
    topLeft = "topleft"
    topRight = "topright"
    bottomLeft = "bottomleft"
    bottomRight = "bottomright"
    center = "center"

    def getStart(self):
        return self.value.replace("left","").replace("right","")

    def getEnd(self):
        return self.value.replace("bottom","").replace("top","")

    def setStart(self, value):
        if self.value != "center":
            end = self.getEnd()
            return DisplayType(value+end)
        return self
    def setEnd(self, value):
        if self.value != "center":
            start = self.getStart()
            return DisplayType(start+value)
        return self

    def calculatePosByDisplayType(self,image,hitbox, pos):
        startDict = {"top":0,"bottom":1,"center":-0.5}
        endDict = {"left":0,"right":1,"center":0.5}
        start,end = self.getParts()
        imageSize = image.getSize()
        size = hitbox.getSize()
        start,end = startDict[start],endDict[end]
        delta = ((size[0]-imageSize[0])*end,(size[1]-imageSize[1])*start)
        from data.default.rect import Rect
        return Rect.addPos(pos,delta)

    def getParts(self):
        return self.getStart(),self.getEnd()