import hashlib
import logging
from bs4 import BeautifulSoup


def url_duplicateCheck(url, connection):
    """
    :param url: URL to check (string, canonicalized)
    :param connection: psycopg2 connection
    :return: isDuplicate(boolean) or None if check unsuccessful
    """
    with connection, connection.cursor() as cur:
        try:
            cur.execute("SELECT id FROM crawldb.page WHERE url = %s", [url])
        except Exception:
            logging.error('Error checking for URL duplicates. Could not execute DB check.')
            return None

        if cur.fetchall():
            return True
        return False


def html_duplicateCheck(html: BeautifulSoup, page_id, connection):
    """
    :param html: html content in the form of a BeautifulSoup
    :param connection: psycopg2 connection
    :return: isDuplicate(boolean) or None if check unsuccessful
    """
    try:
        content = html.prettify()
        content_hash = hashlib.md5(content.encode()).hexdigest()
        with connection, connection.cursor() as cur:
            try:
                cur.execute("SELECT id FROM crawldb.page WHERE content_hash = %s AND id != %s", [content_hash, page_id])
            except Exception:
                logging.error('Error checking for content duplicates. Could not execute DB check.')
                return None

            if cur.fetchall():
                return True
    except Exception:
        logging.error("Could not stringify soup")
    return False
