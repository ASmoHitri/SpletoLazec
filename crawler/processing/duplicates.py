from bs4 import BeautifulSoup
# QUESTION drugace, kot da dodam sledeci dve vrstici ne znam importat configa.
# import sys
# sys.path.insert(0, "/Users/Gal/Desktop/ISRM/FRI/IEPS/SpletoLazec/crawler/")
import config
import psycopg2
import hashlib
# import urltools
# import urllib


def url_duplicateCheck(url, connection):
    """
    :param url: URL to check (string, canonicalized)
    :param connection: psycopg2 connection
    :return: isDuplicate(boolean) or None if check unsucessful
    """
    cur = connection.cursor()
    try:
        cur.execute("SELECT id FROM crawldb.page WHERE url = %s", [url])
        # QUESTION pravo poimentovanje tabele?
        # Assumes urls in database are canonicalized.
    except:
        print('could not execute check')
        return None

    if not cur.fetchall():
        return False
    else:
        return True


def html_duplicateCheck(html: BeautifulSoup, connection):
    """
    :param html: html content in the form of a BeautifulSoup
    :param connection: psycopg2 connection
    :return: isDuplicate(boolean) or None if check unsucessful
    """
    content = str(html)
    # QUESTION ali content = html.prettify()? kako bomo dajali v bazo
    content_hash = hashlib.md5(content)
    cur = connection.cursor()
    try:
        cur.execute("SELECT id FROM crawldb.page WHERE content_hash = %s", [content_hash])
        # QUESTION pravo poimentovanje tabele?
    except:
        print('could not execute check')
        return None

    if not cur.fetchall():
        # TODO ali je treba cursorje zapirati, isto v url_duplicatecheck?
        return False
    else:
        return True
    pass


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

    test_url = 'www.test.com'
    # urllib.parse.urlsplit(sample_url)
    sample_url = "http://podatki.gov.si/nekejsmrdi"
    # moramo testirati z napolnjeno bazo
