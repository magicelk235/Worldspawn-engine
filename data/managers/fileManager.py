import pathlib,importlib
def toModuleSyntax(path):
    return path.replace("/",".")

def getModule(path,file):
    module = importlib.import_module(toModuleSyntax(f"{path}.{file}"))
    return module.getObject()

def removeFullPath(extension,path):
    return path.replace(extension+"/","")

def getFolders(path,fullPath=False):
    pathObj = pathlib.Path(path)
    folders = [str(p).replace("\\","/") for p in pathObj.iterdir() if p.is_dir()]
    if fullPath:
        return folders
    else:
        return [removeFullPath(path,p) for p in folders]

def getFiles(path,removeEnd=False,fullPath=False):
    pathObj = pathlib.Path(path)
    files = [str(p).split(".")[0].replace("\\","/") if removeEnd else str(p).replace("\\","/") for p in pathObj.iterdir() if p.is_file()]
    if fullPath:
        return files
    else:
        return [removeFullPath(path,p) for p in files]