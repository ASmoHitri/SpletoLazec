import os
import logging
import requests
import psycopg2
import psycopg2.extras
from datetime import datetime

import urltools
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException
from bs4 import BeautifulSoup

from crawler import config
from db import queries
from processing import duplicates
from processing import process_helpers
from processing.robots import add_domain


def fetch_data(url):
    """
    Fetches page from given url with selenium and returns HTML body as BeautifulSoup object
    :param url: URL to fetch
    :return: page body as BeautifulSoup object
    """
    options = Options()
    options.add_argument("--headless")
    options.add_argument('--ignore-certificate-errors')
    try:
        driver = webdriver.Chrome(executable_path=os.path.abspath(
            '../web_driver/chromedriver.exe'), options=options)
        driver.get(url)
    except WebDriverException as e:
        logging.error(e.msg)
        return None

    soup = BeautifulSoup(driver.page_source, features="html.parser")
    for script in soup(["head"]):
        script.extract()
    driver.close()
    return soup


def get_page_state(url):
    """
    Checks page's current state by sending HTTP HEAD request
    :param url: Request URL
    :return: ("ok", return_code: int) if request successful,
             ("error", return_code: int) if error response code,
             (None, error_message: str) if page fetching failed (timeout, invalid URL, ...)
    """

    try:
        response = requests.head(url, verify=False, timeout=10)
    except requests.exceptions.RequestException as exception:
        logging.error(exception)
        return None, "Error fetching page"

    if response.status_code >= 400:
        return "error", response.status_code
    return "ok", response.status_code


def get_files(parent_url: str, urls_img: list, urls_binary: list, conn):
    """
    :param parent_url: url of the page we are currently processing, for page_id
    :param urls_img: A list of img files to load (to DB)
    :param urls_binary: A list of binary files to load (to DB)
    :param conn: a psycopg2 connection with which we insert files into our database
    :return:
    """

    # get parent page id from database
    with conn.cursor() as cur:
        cur.execute("SELECT page_id FROM crawldb.page WHERE url = '%s'" % parent_url)
        page_id = cur.fetchall()
    if page_id:
        page_id = page_id[0]
    else:
        logging.error("Error fetching files. Couldn't get parent URL's id form DB.")

    for url in urls_binary:
        data_type_code = (url.split('.')[-1]).upper()
        r = requests.get(url, stream=True)
        content = r.raw_read(10000000)  # TODO tu mozno se potreben decode
        with conn.cursor() as cur:
            cur.execute("INSERT into crawldb.page_data (page_id, data_type_code, \"data\") VALUES (%s, %s, %s)",
                        [page_id, data_type_code, psycopg2.Binary(content)])

    for url in urls_img:
        split = url.split('.')
        filename = "".join(split[:-1])
        content_type = split[-1].lower()
        if content_type in {'img', 'png', 'jpg'}:
            r = requests.get(url, stream=True)
            content = r.raw_read(10000000)
            with conn.cursor() as cur:
                cur.execute("INSERT into crawldb.image (page_id, filename, content_type, data, accessed_time) \
                             VALUES (%s, %s, %s, %s, %s)",
                            [page_id, filename, content_type, psycopg2.Binary(content), datetime.now()])
    return


def process_page(url: str, conn):
    (page_state, state_arg) = get_page_state(url)

    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SELECT * from crawldb.page WHERE url = %s", [url])
        page = cur.fetchall()[0]
        page_id = page['id']
        site_id = page['site_id']

        if page_state == "error":
            # if page returned error before just remove from frontier, otherwise re-add to frontier & update code
            cur.execute(queries.q['remove_from_frontier'], [page_id])
            if page['http_status_code']:
                page_type = 'HTML'
            else:
                page_type = 'FRONTIER'
                cur.execute(queries.q['add_to_frontier'], [page_id])
            cur.execute(queries.q['update_page_codes'], [page_type, state_arg, page_id])
            return
        elif page_state is None:
            # failed to fetch page -> re-add page to frontier
            cur.execute(queries.q['remove_from_frontier'], [page_id])
            cur.execute(queries.q['add_to_frontier'], [page_id])
            return

    page_body = fetch_data(url)
    # handle content duplicates
    if duplicates.html_duplicateCheck(page_body, conn):
        with conn.cursor() as cur:
            cur.execute(queries.q['update_page_codes'], ['DUPLICATE', state_arg, page_id])
        return

    # parse/process page
    split_url = urltools.split(url)
    url_scheme = split_url.scheme
    url_netloc = split_url.netloc
    new_urls, binary_urls, img_urls = process_helpers.get_page_urls(page_body, url_scheme, url_netloc, config.search_domain)

    get_files(url, img_urls, binary_urls, conn)

    for cur_url in new_urls:
        if duplicates.url_duplicateCheck(cur_url, conn):
            continue
        cur_split_url = urltools.split(cur_url)
        with conn.cursor() as cur:
            cur.execute("SELECT id from crawldb.site WHERE \"domain\" = %s", [cur_split_url.netloc])
            cur_site_id = cur.fetchall()
            if not cur_site_id:
                cur_site_id = add_domain(cur_split_url.netloc, conn)    # add domain if doesn't exists yet
            else:
                cur_site_id = cur_site_id[0]

            cur.execute(queries.q['add_new_page'], [cur_site_id, 'FRONTIER', cur_url])
            cur_id = cur.fetchall()[0]
            cur.execute(queries.q['add_to_frontier'], [cur_id])

    # mark page as crawled
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE crawldb.page \
            SET page_type_code=%s, html_content=%s, http_status_code=%s, accessed_time=NOW() \
            WHERE id=%s",
            ['HTML', page_body, state_arg, page_id])
