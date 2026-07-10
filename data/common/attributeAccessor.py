class AttributeAccessor:
    def setAttr(self, path:str, value:any):
        attributes = path.split(".")
        obj = self
        for attr in attributes[:-1]:
            obj = getattr(obj, attr)
        setattr(obj, attributes[-1], value)

    def getAttr(self, path:str) -> any:
        attributes = path.split(".")
        obj = self
        for attr in attributes:
            obj = getattr(obj, attr)
        return obj