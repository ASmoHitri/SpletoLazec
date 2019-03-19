import urllib.request
import urllib.robotparser
import requests
import re
from bs4 import BeautifulSoup
from Site import Site

#Additional functions
def contains_sitemap(txt):
    """
    :param txt:
    :return: url of the sitemap otherwise returns False
    """
    if re.search("Sitemap",txt):
        findUrl = re.search("Sitemap: (.*)", txt)
        return findUrl.group(1)
    else:
        return False

def get_sitemap(url):
    """
    :param Site map url:
    :return: Site map content
    """
    get_url = requests.get(url)

    if get_url.status_code == 200:
        return get_url.text
    else:
        print ('Unable to fetch sitemap: %s.' % url)


def process_sitemap(s):
    """
    :param s: Sitemap content in xml format
    :return: A list of URLs of all the web sites listed in site map
    """
    soup = BeautifulSoup(s)
    result = []

    for loc in soup.findAll('loc'):
        result.append(loc.text)

    return result




def process_robots(startingSites):
    """
    Function processRobots recives a list of all the seed/starting websites
    Fatches and parses robots.txt and sitemap files from the given sites
    :param startingSites:
    :return: a list of Site objects
    """
    sites = []

    for site in startingSites:
        url = site + "/robots.txt"
        try:
            data = urllib.request.urlopen(url)
            #definiramo domeno
            domain = site

            #vsebina robots.txt
            robots_content = data.read().decode()
            #parser za robots.txt
            robotParser = urllib.robotparser.RobotFileParser()
            robotParser.set_url(url)
            robotParser.read()

            #SiteMap
            siteMapUrl = contains_sitemap(robots_content)
            #preverimo, če vsebuje sitemap
            if siteMapUrl:
                siteMap_content = get_sitemap(siteMapUrl)
                #poiščemo vse spletne strani na sitemapu
                siteMap_sites = process_sitemap(siteMap_content)
            else:
                siteMap_content = None
                siteMap_sites = None

            newSite = Site(domain, robots_content, robotParser, siteMap_content, siteMap_sites)
            sites.append(newSite)

        except urllib.error.HTTPError as err:
            domain = site
            robots_content = None
            robotParser = None
            siteMap_content = None
            siteMap_sites = None
            newSite = Site(domain, robots_content, robotParser, siteMap_content, siteMap_sites)
            sites.append(newSite)

    return sites

#TEST
#definiramo seznam začetnih spletnih mest za katere bomo pobrali robots.txt in parsali sitemapa, če jih vsebujejo
startingSites = ["http://evem.gov.si", "http://e-uprava.gov.si","http://podatki.gov.si","http://e-prostor.gov.si"]
sites = process_robots(startingSites)









