import os
import re
import logging
import requests

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

    scheme = split_url.scheme or parent_scheme                                              # handle relative URLs
    netloc = split_url.netloc or parent_host
    if scheme not in ["http", "https"] or not re.match(".*" + search_domain + "/?$", netloc):
        return None
    path = split_url.path if (split_url.path and split_url.path[0] == "/") \
        else ("/" + split_url.path)                                                         # start path with /
    path = re.sub("/index\.(html|htm|php)", "/", path)                                      # remove 'index.html/htm/php'

    canon_url = urltools.normalize("{0}://{1}{2}".format(scheme, netloc, quote(path)))      # normalize & quote URL
    return canon_url


def get_page_urls(page_data: BeautifulSoup, parent_scheme, parent_host, search_domain=""):
    """
    Parses and normalizes all href and onClick URLs present in page_data
    :param page_data: page DOM
    :param search_domain: Crawlers search domain
    :param parent_scheme: Parent page's scheme
    :param parent_host: Parent page's host (domain name)

    :return: List of page URLs
    """

    page_urls = []
    # href URLs
    for link in page_data.find_all(href=True):
        url = link.get("href")
        canon_url = canonicalize_url(url, parent_scheme, parent_host, search_domain)
        if canon_url:
            page_urls.append(canon_url)

    # onClick URLs
    print("**********onclick:")
    for link in page_data.find_all(onclick=True):
        url = re.search("https?://.*", link.get("onclick"))
        print(url)
    print("******** end")

    return page_urls


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
    driver = webdriver.Chrome(executable_path=os.path.abspath('../web_driver/chromedriver.exe'), options=options)

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


def process_page(url: str):
    (page_state, arg) = get_page_state(url)
    if page_state == "error":
        # TODO save page to database
        # TODO ('site' saving has to be implemented/merged first (@Jan?))
        return
    elif page_state is None:
        # TODO handle pages that couldn't be fetched (se jih samo preskoci / pogleda kasneje?)
        return

    split_url = urltools.split(url)
    url_scheme = split_url.scheme
    url_netloc = split_url.netloc
    if page_state == "redirected":
        end_page = canonicalize_url(arg, url_scheme, url_netloc, config.search_domain)    # Q: what if return value None?? (zaradi domene)
        # TODO check if end_page a duplicate (duplicates check part 1 (URL) (@Gal?))
    print("fetching")
    page_body = fetch_data(url)
    # TODO check for duplicates (duplicates check part 2 (content) (@Gal?))

    new_urls = get_page_urls(page_body, url_scheme, url_netloc, config.search_domain)
    # TODO save new URLs to DB & frontier (@Gal?) kako bomo sedaj naredili s frontierjem?
    # TODO parse & save binaries/files

    # TODO nekam je treba vkljuciti se robots/sitemap zadeve (@Jan?)


if __name__ == '__main__':
    # url1 = "http://dev.vitabits.org"  # should redirect!?!
    # url1 = "http://podatki.gov.si"
    url1 = "https://www.plus2net.com/html_tutorial/button-linking.php"
    process_page(url1)


