import pathlib,importlib
def toModuleSyntax(path):
    return path.replace("/",".")

def validPath(path):
    # Windows lists its folders with backslashes, and splitting on "/" alone
    # would hand the whole path to the name check, which no package passes
    name = str(path).replace("\\","/").split("/")[-1]
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
    if not pathObj.is_dir():
        # a fresh clone has no packages/ folder at all, and that only means
        # there is nothing to load
        return []
    # sorted, so packages that do not depend on each other load in the same
    # order on every machine and the same one wins a name they both define
    folders = sorted(str(p).replace("\\","/") for p in pathObj.iterdir() if (p.is_dir() and validPath(p)))
    if fullPath:
        return folders
    else:
        return [removeFullPath(path,p) for p in folders]

def getFiles(path,removeEnd=False,fullPath=False,extensions=None):
    """List the files in a folder.

    removeEnd drops the extension, and only the extension: cutting at the
    first dot breaks on any folder above the package that has one in its
    name. extensions filters, so a stray .DS_Store next to the sources is
    not mistaken for content. Dunder files such as __init__.py are left out
    the way __pycache__ is left out of getFolders: they make a folder a
    Python package, they are not content, and they have no getObject.
    """
    pathObj = pathlib.Path(path)
    files = []
    for p in pathObj.iterdir():
        if not p.is_file():
            continue
        if extensions != None and p.suffix.lower() not in extensions:
            continue
        if p.stem.startswith("__"):
            continue
        name = str(p).replace("\\","/")
        if removeEnd:
            name = name[:len(name)-len(p.suffix)]
        files.append(name)
    if fullPath:
        return files
    else:
        return [removeFullPath(path,p) for p in files]