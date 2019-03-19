class Site:
    def __init__(self, domain, robots_content, robotParser, siteMap_content, siteMap_sites):
        self.domain = domain
        self.robots_content = robots_content
        self.robotParser = robotParser
        self.siteMap_content = siteMap_content
        self.siteMap_sites = siteMap_sites
