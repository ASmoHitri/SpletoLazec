import urllib.request
import urllib.robotparser
import requests
import re
import urltools
from bs4 import BeautifulSoup
import time
from datetime import datetime
import config

from duplicates import url_duplicateCheck
from process_helpers import canonicalize_url

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
    soup = BeautifulSoup(s,features='html.parser')
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
        # print("robots",url)
        # print("robots", url.encode("utf-8"))
        # data = urllib.request.urlopen(url)
        # #vsebina robots.txt
        # robots_content = data.read().decode()
        data = requests.get(url,verify = False)
        robots_content = data.text
        #SiteMap
        site_map_url = contains_sitemap(robots_content)
        #preverimo, če vsebuje sitemap
        if site_map_url:
            site_map_content = get_sitemap(site_map_url)
        else:
            site_map_content = None
        return robots_content, site_map_content
    #except (urllib.error.HTTPError, urllib.error.URLError) as err:
    except Exception as err:
        robots_content = None
        site_map_content = None
    return robots_content, site_map_content

def can_fetch_page(url, conn):
    """
    :param url: canonicalized url
    :param connection: a psycopg2 connection with which we insert files into our database
    :return: returns a tuple (boolean, boolean (true - delay, false - forbiden))
    """
    split_url = urltools.split(url)
    parent_scheme = split_url.scheme
    domain = split_url.netloc

    with conn, conn.cursor() as curs:
        #vzamemo robots content
        curs.execute("SELECT id, robots_content, next_acces, delay FROM crawldb.site WHERE domain = '%s'" % domain)
        site_id, robots_content, acces_time, delay = curs.fetchone()

    #če domene v bazi še nima robots_content
    if  robots_content == None:
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
         #v primeru, da je robots_prazen ga nastavimo na prazen niz ""
        else:
            robots_content = ""
            can_fetch = True
            delay = 4

        #če delay ni definiran mu damo privzeto vrednost
        if not delay:
            delay = 4

        #definiramo next_acces time
        next_acces_time = datetime.fromtimestamp(time.time() + delay)
        with conn, conn.cursor() as curs:
            # domeno v bazi posodobimo
            sql = """ UPDATE crawldb.site
                      SET robots_content = %s,
                          sitemap_content = %s,
                          next_acces = %s,
                          delay = %s
                      WHERE domain = %s"""
            curs.execute(sql,
                (robots_content, sitemap_content, next_acces_time, delay, domain))

        # v primeru, da sitemap ni prazen dodamo vse strani v frontier
        if sitemap_content:
            sites = process_sitemap(sitemap_content)
            for site in sites:
                cannon_site = canonicalize_url(site, parent_scheme, domain, config.search_domains)
                if cannon_site == None:
                    continue
                # če se stran še ni pojavila jo dodamo v bazo
                if not url_duplicateCheck(cannon_site, conn):
                    with conn, conn.cursor() as curs:
                        curs.execute(
                            "INSERT INTO crawldb.page (site_id, page_type_code,url, accessed_time) VALUES (%s, %s, %s, %s) RETURNING id",
                            [site_id, 'FRONTIER', cannon_site, datetime.now()])
                        cur_id = curs.fetchone()[0]
                        curs.execute("INSERT INTO crawldb.frontier (page_id) VALUES (%s)", [cur_id])
                else:
                    continue

        if can_fetch:
            return (True, False)
        else:
            return (False, False)

    #če robots.txt ni None (!= None)
    else:
        # informacije o robots.txt
        #če je prazen robots, preverimo samo delay
        if robots_content == "":
            visit_time = time.time()
            if visit_time >= acces_time.timestamp():
                next_acces_update = datetime.fromtimestamp(delay + visit_time)
                #posodobimo next_acces za domeno
                with conn, conn.cursor() as curs:
                    sql = """ UPDATE crawldb.site
                                        SET next_acces = %s
                                        WHERE domain = %s"""
                    curs.execute(sql, (next_acces_update, domain))
                return (True, False)
            else:
                return (False, True)
        else:
            #robot parser
            rp = urllib.robotparser.RobotFileParser()
            rp.parse(robots_content.splitlines())

            can_fetch = rp.can_fetch("*",url)
            if can_fetch:
                visit_time = time.time()
                if visit_time >= acces_time.timestamp():
                    next_acces_update = datetime.fromtimestamp(delay + visit_time)

                    with conn, conn.cursor() as curs:
                        #update next_acces
                        sql = """ UPDATE crawldb.site
                                      SET next_acces = %s
                                     WHERE domain = %s"""
                        curs.execute(sql, (next_acces_update,domain))

                    return (True, False)
                else:
                    return (False, True)
            else:
                return (False, False)

#funkcija add domain prejme domeno, ki ni v bazi
#doda domeno v bazo in vrne site_id
def add_domain(domain, conn):
    """
    :param domain that has to be added to the DB
    :param connection to the DB
    :return: site_id of the newly added site
    """
    with conn, conn.cursor() as curs:
        # dodamo domeno v bazo
        curs.execute(
            "INSERT into crawldb.site (domain) VALUES (%s) RETURNING id",
            (domain,))
        site_id = curs.fetchone()[0]
    return site_id


# TEST
# definiramo seznam začetnih spletnih mest za katere bomo pobrali robots.txt in parsali sitemapa, če jih vsebujejo
ss = ["http://evem.gov.si", "http://e-uprava.gov.si","http://podatki.gov.si","http://e-prostor.gov.si"]


#
# import  psycopg2
# from config import *
#
# conn = psycopg2.connect(user=db['username'], password=db['password'],
#                             host=db['host'], port=db['port'], database=db['db_name'])
#
# def test(connection):
#     with connection.cursor() as curs:
#         #curs.execute("INSERT into crawldb.site (domain , robots_content, sitemap_content, next_acces, delay) VALUES (%s, %s, %s, %s, %s)", (
#          #    "e-uprava.gov.si", None, None,datetime(2019, 3, 29, 20, 3, 7, 717148),150))
#         curs.execute("SELECT * FROM crawldb.site")
#         list = curs.fetchall()
#     return list
#
#
# with conn:
#     with conn.cursor() as curs:
#         curs.execute("SELECT * FROM crawldb.site")
#         data = curs.fetchall()
# data
#
# with conn:
#     with conn.cursor() as curs:
#         curs.execute("TRUNCATE crawldb.site CASCADE")
#
#
# for site in ss:
#     split_url = urltools.split(site)
#     domain = split_url.netloc
#     add_domain(domain,conn)
#
# for site in ss:
#     print(can_fetch_page(site, conn))









