from data.default import default
class Sendable:

    def toDict(self,keys):
        data = {}
        for key in keys:
            obj = default.getAttr(self,key)
            if self.isMutable(obj):
                data[key] = obj.toDict()
            else:
                data[key] = obj
    @staticmethod
    def isMutable(obj):
        return hasattr(obj,"__dict__") and hash(obj) == None 

    def fromDict(self,data:dict[str,any]) -> None:
        for key in list(data.keys()):
            objData = data[key]
    
            if self.isMutable(default.getAttr(self,key)):
                default.getAttr(self,key).fromDict(objData)
            else:
                default.setAttr(self, key, objData)