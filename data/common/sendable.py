
class Sendable:

    def setAttr(self, path, value):
        attributes = path.split(".")
        obj = self
        for attr in attributes[:-1]:
            obj = getattr(obj, attr)
        setattr(obj, attributes[-1], value)

    def getAttr(self, path):
        attributes = path.split(".")
        obj = self
        for attr in attributes:
            obj = getattr(obj, attr)
        return obj

    def toDict(self,keys):
        data = {}
        for key in keys:
            obj = self.getAttr(key)
            if self.isMutable(obj):
                data[key] = obj.toDict()
            else:
                data[key] = obj
        return data
    @staticmethod
    def isMutable(obj):
        return hasattr(obj,"toDict")

    def fromDict(self,data:dict[str,any]) -> None:
        for key in list(data.keys()):
            objData = data[key]
    
            if self.isMutable(self.getAttr(key)):
                self.getAttr(key).fromDict(objData)
            else:
                self.setAttr(key, objData)