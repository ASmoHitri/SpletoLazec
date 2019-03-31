import urllib.request
import urllib.robotparser
import requests
import re
import urltools
from bs4 import BeautifulSoup
from process_page import canonicalize_url
import time
from datetime import datetime
import config

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

def get_robots_content(site_domain):
    """
    Function get_robots_content receives the site domain (without '/robots.txt')
    Fatches and parses robots.txt and sitemap files from the given site
    :param site url
    :return: robots content and sitemap content
    """
    url = 'http://' + site_domain + "/robots.txt"
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

def can_fetch_page(url, connection):
    """
    :param url: canonicalized url
    :param connection: a psycopg2 connection with which we insert files into our database
    :return: returns a tuple (site_id, boolean, delay(boolean), forbidden(boolean))
    """
    split_url = urltools.split(url)
    domain = split_url.netloc

    #odpremo povezavo do db
    with connection as conn:
        with conn.cursor() as curs:
            #preverimo, če je domena že v bazi
            curs.execute("SELECT id, robots_content, next_acces, delay FROM crawldb.site WHERE domain = '%s'" % domain)
            existing_domain = curs.fetchone()

            #če domene še ni v bazi
            if existing_domain == None:
                robots_content, sitemap_content = get_robots_content(domain)

                #če robots_content ni prazen
                if robots_content:
                    rp = urllib.robotparser.RobotFileParser()
                    rp.parse(robots_content.splitlines())
                    #  pogledamo, če lahko vhodni url-fetchamo
                    can_fetch = rp.can_fetch("*", url)
                    #crawl delay (preverimo, če je definiran drugače je privzeta vrednost 4s)
                    try:
                        delay = rp.crawl_delay("*")
                    except:
                        delay = 4
                else:
                    can_fetch = True
                    delay = 4

                #če delay ni definiran mu damo privzeto vrednost
                if not delay:
                    delay = 4

                #definiramo next_acces time
                next_acces_time = datetime.fromtimestamp(time.time() + delay)

                # v primeru, da sitemap ni prazen dodamo vse strani v frontier
                if sitemap_content:
                    sites = process_sitemap(sitemap_content)
                    for site in sites:
                        # TODO: dodaj strani na frontier
                        #TODO: kakšen ali je tu parent scheme http ali https
                        cannon_site = canonicalize_url(site, "http", domain, config.search_domain)
                        print(cannon_site)

                # dodamo domeno v bazo
                curs.execute(
                    "INSERT into crawldb.site (domain , robots_content, sitemap_content, next_acces, delay) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                    (domain, robots_content, sitemap_content, next_acces_time, delay))
                site_id = curs.fetchone()[0]

                if can_fetch:
                    return (site_id, True, False, False)
                else:
                    return (site_id, False, False, True)

            #če je domena že v bazi, izberemo robots content
            else:
                site_id = existing_domain[0]
                robots_content = existing_domain[1]
                acces_time = datetime.timestamp(existing_domain[2])
                delay = existing_domain[3]

                # informacije o robots.txt
                #če je prazen robots, preverimo samo delay
                if not robots_content:
                    visit_time = time.time()
                    if visit_time >= acces_time:
                        next_acces_update = datetime.fromtimestamp(delay + visit_time)
                        #posodobimo next_acces za domeno
                        sql = """ UPDATE crawldb.site
                                        SET next_acces = %s
                                        WHERE domain = %s"""
                        curs.execute(sql, (next_acces_update, domain))
                        return (site_id, True, False, False)
                    else:
                        return (site_id, False, True, False)
                else:
                    #robot parser
                    rp = urllib.robotparser.RobotFileParser()
                    rp.parse(robots_content.splitlines())

                    can_fetch = rp.can_fetch("*",url)
                    if can_fetch:
                        visit_time = time.time()
                        if visit_time >= acces_time:
                            next_acces_update = datetime.fromtimestamp(delay + visit_time)

                            #update next_acces
                            sql = """ UPDATE crawldb.site
                                      SET next_acces = %s
                                     WHERE domain = %s"""
                            curs.execute(sql, (next_acces_update,domain))

                            return (site_id, True, False, False)
                        else:
                            return (site_id, False, True, False)
                    else:
                        return (site_id, False, False, True)


#TEST
#definiramo seznam začetnih spletnih mest za katere bomo pobrali robots.txt in parsali sitemapa, če jih vsebujejo
ss = ["http://evem.gov.si", "http://e-uprava.gov.si","http://podatki.gov.si","http://e-prostor.gov.si"]



import  psycopg2
from config import *

conn = psycopg2.connect(user=db['username'], password=db['password'],
                            host=db['host'], port=db['port'], database=db['db_name'])

with conn:
    with conn.cursor() as curs:
        curs.execute("INSERT into crawldb.site (domain , robots_content, sitemap_content, next_acces, delay) VALUES (%s, %s, %s, %s, %s)", (
            "e-uprava.gov.si", None, None,datetime(2019, 3, 29, 20, 3, 7, 717148),150))


with conn:
    with conn.cursor() as curs:
        curs.execute("SELECT * FROM crawldb.site")
        data = curs.fetchall()
data
with conn:
    with conn.cursor() as curs:
        curs.execute("TRUNCATE crawldb.site CASCADE")











