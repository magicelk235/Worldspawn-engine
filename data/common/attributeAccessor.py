class AttributeAccessor:
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