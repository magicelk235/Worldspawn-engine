import os
import yaml
from data.managers import fileManager
from types import MethodType
class Api:

    def __init__(self):
        self.domains:dict[str, "Api.Domain"] = {}
        self.packages:dict[str,"Api.Package"] = {}
        self.GroupsByBases:dict[any,dict[str,any]] = {}
        # every dynamic group by name. The world dict the core keeps all of
        # its objects in is one of them from the start: a domain called
        # sprites means that same dict, where handing the core a fresh one
        # would leave the main loop, the saves and the sync walking only the
        # objects of that one domain
        self.GroupsByNames:dict[str,dict[str,any]] = {"sprites":self.sprites}
        self.getters:dict[str,dict[str,any]] = {}
        self.loadPackagesIfNeeded()

    class Domain:
        def __init__(self,name,package,settings,api):
            self.package = package
            self.name = name
            self.api = api
            self.settings = settings
            self.createDynamicGetters()


        def loadPackage(self,package:"Api.Package"):
            self.createStaticGetter(package)
            self.loadDynamicGetters(package)

        def loadDynamicGetters(self,package:"Api.Package"):
            if self.settings.get("create-dynamic-getter",False):
                for prefab in package.getPrefabs(self.name):
                    base = fileManager.getModule(f"{package.path}/{self.name}/{prefab}","base")
                    self.api.addGroup(prefab,base,f"{package.path}/{self.name}/{prefab}")

        def createDynamicGetters(self):
            if self.settings.get("create-dynamic-getter",False):
                base = fileManager.getModule(f"{self.package.path}/{self.name}","base")
                self.api.addGroup(self.name,base,f"{self.package.path}/{self.name}")

        @ staticmethod
        def buildStaticGetter(objName:str):
            # bound through a factory: a closure over the loop variable would
            # leave every getter pointing at the last prefab that was loaded
            def f(self,name):
                return self.getters[objName].get(name)
            return f

        def createStaticGetter(self,package:"Api.Package"):
            if self.settings.get("create-static-getter",False):
                for path in package.getPrefabs(self.name,True):
                    objects = {}
                    for file in fileManager.getFiles(path,True,extensions={".py"}):
                        objects[file] = fileManager.getModule(path,file)
                    objName:str = path.split("/")[-1]
                    loadedObjects = self.api.getters.get(objName,{})
                    # dependencies load first, so anything already registered
                    # belongs to a package this one builds on: the later
                    # package wins and may specialise inherited content
                    objects = loadedObjects | objects
                    self.api.getters[objName] = objects
                    getterName = f"get{objName.capitalize()}"
                    if hasattr(type(self.api),getterName):
                        # a method the core already has - a folder called
                        # object would replace getObject and every lookup by
                        # id with it. The prefabs still load by prefabPath.
                        self.api.raiseError("getterNameTaken",
                            f"{path}: core.{getterName} already exists, so this folder gets no getter; rename it")
                        continue
                    self.api.createFunction(getterName,self.buildStaticGetter(objName))
                

        def load(self):
            pass
            


    class Package:
        def __init__(self,settings,api:"Api"):
            self.api = api
            self.settings = settings
            self.path = f"packages/{self.name}"
            self.load()

        def createDomain(self,name,settings):
            domain = self.api.Domain(name,self,settings,self.api)
            self.api.addDomain(domain)

        def loadDependencies(self):
            for package in self.settings.get("dependencies") or []:
                if not self.api.isPackageLoaded(package):
                    self.api.loadPackage(package)



        def load(self):
            self.loadDependencies()
            self.loadNewDomains()
            self.loadDomains()
            self.loadCoreExtension()

        def loadCoreExtension(self):
            # a package of content alone has nothing to graft onto the core,
            # and the hooks the core looks up on it are all optional
            self.core = None
            if not os.path.isfile(self.path+"/core.py"):
                return
            self.core = fileManager.getModule(self.path,"core")
            self.api.addToBase(self.core)

        def getPrefabs(self,domain,fullPath=False):
            return fileManager.getFolders(self.path+f"/{domain}",fullPath)

        def getTypeSettings(self) -> dict:
            if not os.path.isfile(self.path+"/domains.yaml"):
                return {}
            with open(self.path+"/domains.yaml") as f:
                # a package that adds no domains may leave the file empty
                domains = yaml.safe_load(f) or {}
                return domains

        def loadNewDomains(self):
            domainsSettings = self.getTypeSettings()
            for domain in domainsSettings.keys():
                self.createDomain(domain,domainsSettings[domain])

        def loadDomains(self):
            usedDomains = self.settings.get("used-domains") or []
            for domainName in usedDomains:
                if domainName not in self.api.domains:
                    self.api.raiseError("domainNotFound",
                        f"{self.path}: uses the domain {domainName}, which neither it nor its dependencies declare")
                    continue
                domain = self.api.getDomain(domainName)
                domain.loadPackage(self)


        @ property
        def name(self) -> str:
            return self.settings["name"]


    def addGroup(self,name,cls,source=None):
        group = self.GroupsByNames.get(name)
        if group == None:
            group = {}
            self.GroupsByNames[name] = group
            if hasattr(self,name):
                # core.host, core.packages, core.network: a group set over one
                # of those breaks the engine far from the folder that did it
                self.raiseError("groupNameTaken",
                    f"{source or name}: core.{name} already exists, so this group is not reachable as core.{name}; rename the folder")
            else:
                setattr(self,name,group)
        # a package that fills a domain or a prefab folder another one
        # already declared adds to the group that is there. A fresh dict would
        # drop everything put in it so far out of core.<name>.
        self.GroupsByBases[cls] = group

    def addDomain(self,domain):
        self.domains[domain.name] = domain


    @ staticmethod
    def getPackagePathByName(name):
        return f"packages/{name}"

    def createFunction(self,name,func):
        setattr(self,name,MethodType(func,self))

    def addToBase(self,newClass):
        if newClass not in self.__class__.__bases__:
            self.__class__.__bases__ = self.__class__.__bases__+(newClass,)
        newClass.__init__(self)
    @ staticmethod
    def getPackageSettings(name:str) -> dict:
        with open(f"{Api.getPackagePathByName(name)}/settings.yaml") as f:
            settings = yaml.safe_load(f) or {}
            return settings

    def isPackageLoaded(self,name:str) -> bool:
        return name in self.packages

    def loadPackage(self,name:str) -> None:
        settings = self.getPackageSettings(name)
        if settings.get("name") != name:
            # the folder is what the engine imports from and the name is what
            # everything else calls it by, so the two have to agree
            self.raiseError("packageNotLoaded",
                f"packages/{name}: settings.yaml names it {settings.get('name')!r}; a package has to be named after its folder")
            return
        missing = [dependency for dependency in settings.get("dependencies") or []
                   if not self.isPackageLoaded(dependency)
                   and not os.path.isfile(f"{self.getPackagePathByName(dependency)}/settings.yaml")]
        if missing:
            # without what it builds on the package would fail halfway through
            # loading, after grafting part of itself onto the core
            self.raiseError("packageNotLoaded",
                f"packages/{name}: needs {', '.join(missing)}, which is not in packages/")
            return
        self.packages[name] = self.Package(settings,self)

    def getDomain(self,domain):
        return self.domains[domain]

    def loadPackagesIfNeeded(self) -> None:
        if os.path.isdir("packages"):
            for folder in sorted(os.listdir("packages")):
                # only letters and digits make a package folder; anything else
                # that carries a settings.yaml is a package left out, and the
                # author ought to hear about it rather than see nothing
                if not fileManager.validName(folder) and os.path.isfile(f"packages/{folder}/settings.yaml"):
                    self.raiseError("packageNotLoaded",
                        f"packages/{folder}: a package folder name may only hold letters and digits")
        for folder in fileManager.getFolders("packages"):
            # a folder without settings is not a package, just something
            # sitting next to them
            if not os.path.isfile(f"packages/{folder}/settings.yaml"):
                continue
            settings = self.getPackageSettings(folder)
            # a package pulled in as somebody else's dependency is already
            # loaded; loading it again would re-run its core extension and
            # let it overwrite content the package that depends on it added.
            # One that does not say otherwise loads, as everything sitting in
            # packages/ is meant to.
            if settings.get("always-enabled",True) and not self.isPackageLoaded(folder):
                self.loadPackage(folder)