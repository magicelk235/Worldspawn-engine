import yaml
from data.managers import fileManager
from types import MethodType
class Api:

    def __init__(self):
        self.domains:dict[str, "Api.Domain"] = {}
        self.packages:dict[str,"Api.Package"] = {}
        self.GroupsByBases:dict[any,dict[str,any]] = {}
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
                    self.api.addGroup(prefab,base)

        def createDynamicGetters(self):
            if self.settings.get("create-dynamic-getter",False):
                base = fileManager.getModule(f"{self.package.path}/{self.name}","base")
                self.api.addGroup(self.name,base)

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
                    for file in fileManager.getFiles(path,True):
                        objects[file] = fileManager.getModule(path,file)
                    objName:str = path.split("/")[-1]
                    loadedObjects = self.api.getters.get(objName,{})
                    objects = objects | loadedObjects
                    self.api.getters[objName] = objects
                    self.api.createFunction(f"get{objName.capitalize()}",self.buildStaticGetter(objName))
                

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
            for package in self.settings["dependencies"]:
                if not self.api.isPackageLoaded(package):
                    self.api.loadPackage(package)



        def load(self):
            self.loadDependencies()
            self.loadNewDomains()
            self.loadDomains()
            self.loadCoreExtension()

        def loadCoreExtension(self):
            self.core = fileManager.getModule(self.path,"core")
            self.api.addToBase(self.core)

        def getPrefabs(self,domain,fullPath=False):
            return fileManager.getFolders(self.path+f"/{domain}",fullPath)

        def getTypeSettings(self) -> dict:
            with open(self.path+"/domains.yaml") as f:
                domains = yaml.safe_load(f)
                return domains

        def loadNewDomains(self):
            domainsSettings = self.getTypeSettings()
            for domain in domainsSettings.keys():
                self.createDomain(domain,domainsSettings[domain])

        def loadDomains(self):
            usedDomains = self.settings["used-domains"]
            for domainName in usedDomains:
                domain = self.api.getDomain(domainName)
                domain.loadPackage(self)


        @ property
        def name(self) -> str:
            return self.settings["name"]


    def addGroup(self,name,cls):
        group = {}
        setattr(self,name,group)
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
            settings = yaml.safe_load(f)
            return settings

    def isPackageLoaded(self,name:str) -> bool:
        return name in self.packages

    def loadPackage(self,name:str) -> None:
        settings = self.getPackageSettings(name)
        self.packages[name] = self.Package(settings,self)

    def getDomain(self,domain):
        return self.domains[domain]

    def loadPackagesIfNeeded(self) -> None:
        packages = fileManager.getFolders("packages")
        print(packages)
        packagesSettings = [self.getPackageSettings(package) for package in packages]
        for settings in packagesSettings:
            if settings["always-enabled"]:
                self.loadPackage(settings["name"])