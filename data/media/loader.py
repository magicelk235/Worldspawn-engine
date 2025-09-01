import os


def load(path,validExtensions,mediaDict,mediaLoadFunction):
    for dirpath, __, filenames in os.walk(path):
        for filename in filenames:
            _, ext = os.path.splitext(filename)
            ext = ext.lower()
            
            if ext in validExtensions:
                fullPath = os.path.join(dirpath, filename)
                try:
                    mediaObject = mediaLoadFunction(fullPath)
                except Exception as e:
                    continue
                unClearedPath = fullPath.split(".")[0].replace(os.sep, "/")
                relativePath, _ = os.path.splitext(unClearedPath)
                relativePath = relativePath.replace(path+"/","")
                mediaDict[relativePath] = mediaObject

