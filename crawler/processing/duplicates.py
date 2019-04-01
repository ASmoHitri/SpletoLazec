import psycopg2
import hashlib
import logging
from bs4 import BeautifulSoup
from crawler import config


def url_duplicateCheck(url, connection):
    """
    :param url: URL to check (string, canonicalized)
    :param connection: psycopg2 connection
    :return: isDuplicate(boolean) or None if check unsuccessful
    """
    with connection.cursor() as cur:
        try:
            cur.execute("SELECT id FROM crawldb.page WHERE url = %s", [url])
        except Exception:
            logging.error('Error checking for URL duplicates. Could not execute DB check.')
            return None

        if cur.fetchall():
            return True
        return False


def html_duplicateCheck(html: BeautifulSoup, connection):
    """
    :param html: html content in the form of a BeautifulSoup
    :param connection: psycopg2 connection
    :return: isDuplicate(boolean) or None if check unsuccessful
    """
    content = str(html)
    content_hash = hashlib.md5(content.encode()).hexdigest()
    with connection.cursor() as cur:
        try:
            cur.execute("SELECT id FROM crawldb.page WHERE content_hash = %s", [content_hash])
        except Exception:
            logging.error('Error checking for content duplicates. Could not execute DB check.')
            return None

        if cur.fetchall():
            return True
        return False


# def init_html_hashtable():
#     """
#     """
#     pass
#
#
# def html_duplicateCheckLSH(html, hash, hashtable):
#     def shingle(html):
#         pass
#
#     """
#     :param url:
#     :param hash:
#     :param hashtable:
#     :return: isNearDuplicate(boolean), new_hashtable
#     """
#     pass
if __name__ == '__main__':
    db = config.db
    conn = psycopg2.connect(user=db['username'], password=db['password'],
                            host=db['host'], port=db['port'], database=db['db_name'])
    # cur = conn.cursor()
    # cur.execute("SELECT id FROM crawldb.page WHERE url = %s", ['mojprimer'])
    # cur.fetchall()
    # cur.close()

    test_url = 'www.test.com'
    # urllib.parse.urlsplit(sample_url)
    sample_url = "http://podatki.gov.si/nekejsmrdi"
    # moramo testirati z napolnjeno bazo
