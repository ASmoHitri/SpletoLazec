import urllib.request
import urllib.robotparser
import requests
import re
from bs4 import BeautifulSoup

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

def get_robots_content(siteUrl):
    """
    Function get_robots_content receives the url of the root site (without '/robots.txt')
    Fatches and parses robots.txt and sitemap files from the given site
    :param site url
    :return: robots content and sitemap content
    """
    url = siteUrl + "/robots.txt"
    try:
        data = urllib.request.urlopen(url)
        #vsebina robots.txt
        robots_content = data.read().decode()
        #SiteMap
        site_map_url = contains_sitemap(robots_content)
        #preverimo, če vsebuje sitemap
        if site_map_url:
            site_map_content = get_sitemap(site_map_url)
        else:
            site_map_content = None
        return robots_content, site_map_content
    except urllib.error.HTTPError as err:
        robots_content = None
        site_map_content = None
    return robots_content, site_map_content

#TEST
#definiramo seznam začetnih spletnih mest za katere bomo pobrali robots.txt in parsali sitemapa, če jih vsebujejo
startingSites = ["http://evem.gov.si", "http://e-uprava.gov.si","http://podatki.gov.si","http://e-prostor.gov.si"]











