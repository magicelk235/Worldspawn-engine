import os
from data.managers import fileManager


class AssetsLoader:
    class Asset:
        def __init__(self,mediaDict:dict,additionalFunction:callable|None=None):
            self.mediaDict = mediaDict
            if additionalFunction !=None:
                self.additionalFunction = additionalFunction
            else:
                self.additionalFunction = lambda x,y: None
        
        def get(self,path):
            asset = self.mediaDict.get(path,self.mediaDict.values[-1])
            self.additionalFunction(self,asset)
            return asset
        
    assets:dict[str,dict[str,any]] = {}
    @ classmethod
    def newAsset(cls,name:str,validExtensions:set[str],loadFunction:callable,additionalFunction:callable|None=None,mediaDict:dict={}):
        cls.load(name,validExtensions,mediaDict,loadFunction)
        asset = cls.Asset(mediaDict,additionalFunction)
        cls.assets[name] = asset
    @ staticmethod
    def load(path,validExtensions,mediaDict,loadFunction):
        for package in fileManager.getFolders("packages",True):
            currentPath = f"{package}/assets/{path}"
            for dirpath, __, filenames in os.walk(currentPath):
                for filename in filenames:
                    _, ext = os.path.splitext(filename)
                    ext = ext.lower()
                    if ext in validExtensions:
                        fullPath = os.path.join(dirpath, filename)
                        try:
                            mediaObject = loadFunction(fullPath)
                        except Exception as e:
                            continue
                        unClearedPath = fullPath.split(".")[0].replace(os.sep, "/")
                        relativePath, _ = os.path.splitext(unClearedPath)
                        relativePath = relativePath.replace(currentPath+"/","")
                        mediaDict[relativePath] = mediaObject
    @classmethod
    def get(cls,name,path):
        cls.assets[name].get(path, cls.assets[name].keys()[0])