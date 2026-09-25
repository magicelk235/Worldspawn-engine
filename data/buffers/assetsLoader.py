import os
import yaml
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
    def newAsset(cls,name:str,validExtensions:set[str],loadFunction:callable,additionalFunction:callable=None,buffers:dict=None):
        buffers = {} if buffers == None else buffers
        cls.load(name,validExtensions,buffers,loadFunction)
        asset = cls.Asset(buffers,additionalFunction)
        cls.assets[name] = asset
    @ staticmethod
    def packagesByDependency():
        """Package folders with a package listed after everything it needs.

        Two packages can ship an asset under the same name - a game that
        replaces a base package's item keeps the item's art next to it - and
        the buffer holds one entry per name. Walking the folders in whatever
        order the filesystem hands back would decide the winner arbitrarily
        and differently on another machine, so a package is loaded after its
        dependencies and overrides them, which is the same direction the
        content getters resolve in.
        """
        folders = sorted(fileManager.getFolders("packages",True))
        needs = {}
        for folder in folders:
            try:
                with open(f"{folder}/settings.yaml") as f:
                    settings = yaml.safe_load(f) or {}
            except OSError:
                settings = {}
            needs[folder] = set(settings.get("dependencies") or ())
        byName = {folder.split("/")[-1]:folder for folder in folders}
        ordered = []
        placed = set()
        # dependencies first; a cycle or a missing one just falls through in
        # sorted order rather than dropping the package
        while len(ordered) < len(folders):
            progressed = False
            for folder in folders:
                if folder in placed:
                    continue
                pending = {byName[name] for name in needs[folder] if name in byName}
                if pending <= placed:
                    ordered.append(folder)
                    placed.add(folder)
                    progressed = True
            if not progressed:
                for folder in folders:
                    if folder not in placed:
                        ordered.append(folder)
                        placed.add(folder)
                break
        return ordered

    @ staticmethod
    def load(path,validExtensions,buffers,loadFunction):
        for package in AssetsLoader.packagesByDependency():
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
                        # only the extension comes off: a dot anywhere in the
                        # path above the package would cut the key short and
                        # the asset would never be found by its own name
                        relativePath,_ = os.path.splitext(fullPath.replace(os.sep,"/"))
                        relativePath = relativePath.replace(currentPath+"/","")
                        buffers[relativePath] = mediaObject
    @classmethod
    def get(cls,name,path):
        return cls.assets[name].get(path)
import data.buffers.builtInAssets