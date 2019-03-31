import os
import re
import logging
import requests
import psycopg2
import duplicates
from datetime import datetime

import urltools
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from urllib.parse import quote

import config


def canonicalize_url(url, parent_scheme, parent_host, search_domain=""):
    """
    Canonicalizes given URL. If path is relative, parent_scheme and parent_host are used.
    :param url: URL to canonicalize
    :param parent_scheme: Parent page's scheme
    :param parent_host: Parent page's host (domain name)
    :param search_domain: Crawlers search domain. If specified, URL's domain is checked against it.
    :return: Canonicalized URL / None if bad domain
    """

    split_url = urltools.split(url)

    # TODO kaj ce ni v domeni

    # handle relative URLs
    scheme = split_url.scheme or parent_scheme
    netloc = split_url.netloc or parent_host
    if scheme not in ["http", "https"] or not re.match(".*" + search_domain + "/?$", netloc):
        return None
    path = split_url.path if (split_url.path and split_url.path[0] == "/") \
        else ("/" + split_url.path)                                                         # start path with /
    # remove 'index.html/htm/php'
    path = re.sub("/index\.(html|htm|php)", "/", path)

    canon_url = urltools.normalize(
        "{0}://{1}{2}".format(scheme, netloc, quote(path)))      # normalize & quote URL
    return canon_url


def get_page_urls(page_data: BeautifulSoup, parent_scheme, parent_host, search_domain=""):
    """
    Parses and normalizes all href and onClick URLs present in page_data
    :param page_data: page DOM
    :param search_domain: Crawlers search domain
    :param parent_scheme: Parent page's scheme
    :param parent_host: Parent page's host (domain name)

    :return: List of page URLs, list of binaries URLs, list of img URLs
    """

    page_urls = []
    binaries_urls = []
    binaries_regex = ".(pdf|PDF|doc|DOC|ppt|PPT)(x|X)?\/?$"
    # href URLs
    for link in page_data.find_all(href=True):
        url = link.get("href")
        canon_url = canonicalize_url(url, parent_scheme, parent_host, search_domain)
        if canon_url:
            if re.search(binaries_regex, canon_url):
                binaries_urls.append(canon_url)
            else:
                page_urls.append(canon_url)

    # onClick URLs
    for link in page_data.find_all(onclick=True):
        onclick_link = link.get("onclick")
        before_link = re.search("((document|window|parent).)?location(.href)?=", onclick_link)
        if before_link:
            before_link = before_link.group(0)
            onclick_link = onclick_link.replace(before_link, "").replace("'", "")
            canon_url = canonicalize_url(onclick_link, parent_scheme, parent_host, search_domain)
            if canon_url:
                if re.search(binaries_regex, canon_url):
                    binaries_urls.append(canon_url)
                else:
                    page_urls.append(canon_url)

    # img urls
    img_urls = []
    img_regex = ".(png|PNG|img|IMG|jp(e)?g|JP(E)?G)$"
    for link in page_data.find_all("img"):
        url = link["src"]
        canon_url = canonicalize_url(url, parent_scheme, parent_host)       # TODO Q: ali tudi slike samo tiste ki v pravi domeni?
        if canon_url and re.search(img_regex, canon_url):
            img_urls.append(canon_url)
            
    return page_urls, binaries_urls, img_urls


def fetch_data(url):
    """
    Fetches page from given url with selenium and returns HTML body as BeautifulSoup object
    :param url: URL to fetch
    :return: page body as BeautifulSoup object
    """
    # TODO error/exceptions handling (try, catch)
    options = Options()
    options.add_argument("--headless")
    options.add_argument('--ignore-certificate-errors')
    driver = webdriver.Chrome(executable_path=os.path.abspath(
        '../web_driver/chromedriver.exe'), options=options)

    driver.get(url)
    soup = BeautifulSoup(driver.page_source, features="html.parser")
    for script in soup(["head"]):
        script.extract()
    # print(soup)
    driver.close()
    return soup


def get_page_state(url):
    """
    Checks page's current state by sending HTTP HEAD request
    :param url: Request URL
    :return: ("ok", return_code: int) if request successful and not redirected,
             ("error", return_code: int) if error response code,
             ("redirected", ending_url: str) if request successful but redirected,
             (None, error_message: str) if page fetching failed (timeout, invalid URL, ...)
    """

    try:
        response = requests.head(url, verify=False, timeout=10)
    except requests.exceptions.RequestException as exception:
        logging.error(exception)
        return None, "Error fetching page"

    # print(response.history)
    # TODO check why history always empty!
    if response.history:
        return "redirected", response.url
    if response.status_code >= 400:
        return "error", response.status_code
    return "ok", response.status_code


def get_files(parentUrl: str, urls_img: list, urls_binary: list, conn):
    """
    :param soup: BeautifulSoup of the web page content you want to extract image files from.
    :param parentUrl: url of the page we are currently processing, for page_id
    :param urls: A list of binary file urls, gotten with get_page_urls
    :param conn: a psycopg2 connection with which we insert files into our database
    :return:
    """
    cur = conn.cursor()
    cur.execute("SELECT page_id FROM crawldb.page WHERE url = '%s'" % parentUrl)
    page_id = cur.fetchall()
    page_id = page_id[0]
    for url in urls_binary:
        data_type_code = (url.split('.')[-1]).upper()
        r = requests.get(url, stream=True)
        content = r.raw_read(10000000)  # tu mozno se potreben decode
        cur.execute("INSERT into crawldb.page_data (page_id, data_type_code, \"data\") VALUES (%s, %s, %s)", [
            page_id, data_type_code, psycopg2.Binary(content)])
        cur.commit()
    # for el in soup.find_all('img'):
    #     url = el['src']
    for url in urls_img:
        # TODO assuming we can canonicalize the url:
        split = url.split('.')
        filename = split[0]
        content_type = split[1]
        if content_type in {'img', 'png', 'jpg'}:
            r = requests.get(url, stream=True)
            content = r.raw_read(10000000)
            cur.execute("INSERT into crawldb.image (page_id, filename, content_type, \"data\", accessed_time) VALUES (%s, %s, %s, %s, %s)",
                        [page_id, filename, content_type, psycopg2.Binary(content), datetime.now()])
            cur.commit()
    cur.close()
    return


def process_page(url: str, conn):
    (page_state, arg) = get_page_state(url)
    page_body = fetch_data(url)
    split_url = urltools.split(url)
    url_scheme = split_url.scheme
    url_netloc = split_url.netloc
    get_page_urls(page_body, url_scheme, url_netloc)

    return
    cur = conn.cursor()

    cur.execture("SELECT id from crawldb.page WHERE url = %s", [url])
    page_id = cur.fetchall()[0]

    if page_state == "error":
        # TODO save page to database
        # ce dodamo error kot page_type lahko skoraj skopiramo iz duplicates naprej.
        # TODO ('site' saving has to be implemented/merged first (@Jan?))
        return
    elif page_state is None:
        # TODO handle pages that couldn't be fetched (se jih samo preskoci / pogleda kasneje?)
        return

    split_url = urltools.split(url)
    url_scheme = split_url.scheme
    url_netloc = split_url.netloc

    if page_state == "redirected":
        # Q: what if return value None?? (zaradi domene)
        end_page = canonicalize_url(arg, url_scheme, url_netloc, config.search_domain)
        (page_state, arg) = get_page_state(end_page)
        if duplicates.url_duplicateCheck(end_page, conn):
            cur.execute("UPDATE crawldb.page SET page_type_code = %s, http_status_code = %s, accessed_time = %s WHERE id = %s", [
                        'DUPLICATE', arg, datetime.now(), page_id])
            cur.commit()
            cur.close()
            return
        else:
            url = end_page  # QUESTION ali spremenimo tu url?
        # kaj naredimo else?

    page_body = fetch_data(url)
    # pridobimo podatke o domeni
    # tu se zaradi redirecta lahko zgodi, da še nimamo domene? pod kateri url shranjujemo redirectano stran?
    cur.execute("SELECT id from crawldb.site WHERE \"domain\" = %s", [url_netloc])
    site_id = cur.fetchall()[0]

    # sledece se verjetno ne mora zgoditi razen pri redirectih?

    # if not site_id:
    #     cur.execute(
    #         "INSERT into crawldb.site (\"domain\", robots_content, sitemap_content, next_acces, delay)", [url_netloc, ??, ??, ??, ??])
    #     cur.commit()
    # else:
    #     site_id = site_id[0]

    if duplicates.html_duplicateCheck(page_body, conn):
        cur.execute(
            "INSERT into crawldb.page (site_id, page_type_code, url, html_content, http_status_code, accessed_time)",
            [site_id, 'DUPLICATE', url, page_body, arg, datetime.now()])
        cur.commit()
        cur.close()
        return

    # naredimu update na crawldb.page, zato najprej rabimo page_id
    cur.execute("UPDATE crawldb.page SET page_type_code = %s, html_content = %s, http_status_code = %s, accessed_time = %s WHERE id = %s", [
                'HTML', page_body, arg, datetime.now(), page_id])
    cur.commit()
    new_urls, binary_urls, img_urls = get_page_urls(
        page_body, url_scheme, url_netloc, config.search_domain)

    get_files(url, img_urls, binary_urls, conn)

    for cur_url in new_urls:
        cur_split_url = urltools.split(cur_url)
        cur_url_scheme = cur_split_url.scheme
        cur_url_netloc = cur_split_url.netloc
        cur_canon_url = canonicalize_url(
            cur_url, cur_url_scheme, cur_url_netloc, config.search_domain)
        if duplicates.url_duplicateCheck(cur_canon_url, conn):
            continue
        cur.execute("SELECT id from crawldb.site WHERE \"domain\" = %s", [cur_url_netloc])
        cur_site_id = cur.fetchall()
        if not cur_site_id:  # ce domene se ni v bazi
            # cur.execute(
                # "INSERT into crawldb.site (\"domain\", robots_content, sitemap_content, next_acces, delay)", [cur_url_netloc, ??, ??, ??, ??])
                # TODO popravi zgornji insert s funkcijami iz robots.
            cur.commit()
        else:
            cur_site_id = cur_site_id[0]

        cur.execute("INSERT insert crawldb.page (site_id, page_type_code, url, accessed_time)", [
                    cur_site_id, 'FRONTIER', cur_canon_url,  datetime.now()])

        cur.execute("dodaj v frontier?")
        cur.commit()
    cur.close()
    # TODO nekam je treba vkljuciti se robots/sitemap zadeve (@Jan?)


if __name__ == '__main__':
    # # url1 = "http://dev.vitabits.org"  # should redirect!?!
    # url1 = "http://podatki.gov.si"
    # # soup = BeautifulSoup(requests.get(url1).text, features="html.parser")
    # # soup.find_all('img')[0]['src']
    #
    # # fetch_data(url1)
    # process_page(url1)
    # print("zacetek")
    # str = "doc.min.oiiof"
    # str1 = re.search("doc", str)
    # print(str1.group(0))

    page = "http://www.lpp.si/javni-prevoz/ceniki?fbclid=IwAR1rJLWxICiiIBjGvuj1PvAnenJK-tISgvv3VQ2-UcvUDSMRalciJG-N1us"
    process_page(page, None)

