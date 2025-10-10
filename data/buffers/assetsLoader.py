import os
from data.managers import fileManager

class AssetsLoader:
    class Asset:
        def __init__(self,buffers:dict,additionalFunction:callable=None):
            self.buffers:dict = buffers
            self.defaultAsset = list(self.buffers.values())[0]
            
            if additionalFunction !=None:
                self.additionalFunction = additionalFunction
            else:
                self.additionalFunction = lambda x,y: None
        
        def get(self,path):
            asset = self.buffers.get(path,self.defaultAsset)
            self.additionalFunction(self,asset)
            return asset
        
    assets:dict[str,dict[str,any]] = {}
    @ classmethod
    def newAsset(cls,name:str,validExtensions:set[str],loadFunction:callable,additionalFunction:callable=None,buffers:dict={}):
        cls.load(name,validExtensions,buffers,loadFunction)
        asset = cls.Asset(buffers,additionalFunction)
        cls.assets[name] = asset
    @ staticmethod
    def load(path,validExtensions,buffers,loadFunction):
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
                        buffers[relativePath] = mediaObject
    @classmethod
    def get(cls,name,path):
        return cls.assets[name].get(path)
import data.buffers.builtInAssets