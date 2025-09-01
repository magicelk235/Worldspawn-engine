import pathlib
def setAttr(obj, path, value):
    attributes = path.split(".")
    for attr in attributes[:-1]:
        obj = getattr(obj, attr)
    setattr(obj, attributes[-1], value)

def getAttr(obj, path):
    attributes = path.split(".")
    for attr in attributes:
        obj = getattr(obj, attr)
    return obj

def deltaDict(dict1,dict2):
    dict3 = {}
    for key in dict1.keys():
        if dict2.get(key,None) != None:
            if dict1[key] != dict2[key]:
                dict3[key] = dict2[key]
            dict2.pop(key)
    for key in dict2.keys():
        dict3[key] = dict2[key]
    return dict3

