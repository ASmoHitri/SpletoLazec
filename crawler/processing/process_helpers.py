import re
import urltools

from bs4 import BeautifulSoup
from urllib.parse import quote


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
    binaries_regex = "\.(pdf|PDF|doc|DOC|ppt|PPT)(x|X)?\/?$"
    ignore_regex = "\.(mp4|MP4|avi|AVI)$"
    # href URLs
    for link in page_data.find_all(href=True):
        url = link.get("href")
        canon_url = canonicalize_url(url, parent_scheme, parent_host, search_domain)
        if canon_url:
            if re.search(ignore_regex, canon_url):
                continue
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
    img_regex = "\.(png|PNG|img|IMG|jp(e)?g|JP(E)?G)$"
    for link in page_data.find_all("img"):
        if link.has_attr("src"):
            canon_url = canonicalize_url(link["src"], parent_scheme, parent_host)
            if canon_url and re.search(img_regex, canon_url):
                img_urls.append(canon_url)

    return page_urls, binaries_urls, img_urls
