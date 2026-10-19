
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
            if isinstance(obj,Sendable):
                # copied already, by the same rule
                data[key] = obj.toDict()
                continue
            if self.isMutable(obj):
                # any other toDict may still hand out its own live lists
                obj = obj.toDict()
            data[key] = self.snapshot(obj)
        return data

    @staticmethod
    def snapshot(obj):
        # what this hands out is kept as the host's record of what a client
        # was sent and diffed against on the next sync. A list or dict passed
        # along as itself is still the live one, so a change made to it in
        # place lands on both sides of that diff and never reaches anyone.
        # This is the one copy made of it; the record keeps it as it is.
        if isinstance(obj,list):
            return [Sendable.snapshot(value) for value in obj]
        if isinstance(obj,dict):
            return {key:Sendable.snapshot(value) for key,value in obj.items()}
        return obj
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