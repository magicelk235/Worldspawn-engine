import pathlib,importlib
def toModuleSyntax(path):
    return path.replace("/",".")

def validPath(path):
    name = str(path)
    name = name.split("/")[-1]
    return validName(name)
    
def validName(name):
    return str(name).isalnum()

def getModule(path,file):
    module = importlib.import_module(toModuleSyntax(f"{path}.{file}"))
    return module.getObject()

def removeFullPath(extension,path):
    return path.replace(extension+"/","")

def getFolders(path,fullPath=False):
    pathObj = pathlib.Path(path)
    folders = [str(p).replace("\\","/") for p in pathObj.iterdir() if (p.is_dir() and validPath(p))]
    if fullPath:
        return folders
    else:
        return [removeFullPath(path,p) for p in folders]

def getFiles(path,removeEnd=False,fullPath=False,extensions=None):
    """List the files in a folder.

    removeEnd drops the extension, and only the extension: cutting at the
    first dot breaks on any folder above the package that has one in its
    name. extensions filters, so a stray .DS_Store next to the sources is
    not mistaken for content.
    """
    pathObj = pathlib.Path(path)
    files = []
    for p in pathObj.iterdir():
        if not p.is_file():
            continue
        if extensions != None and p.suffix.lower() not in extensions:
            continue
        name = str(p).replace("\\","/")
        if removeEnd:
            name = name[:len(name)-len(p.suffix)]
        files.append(name)
    if fullPath:
        return files
    else:
        return [removeFullPath(path,p) for p in files]