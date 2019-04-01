import sys
import time
import threading
import logging
import psycopg2
from psycopg2 import pool
from psycopg2 import extras

import config
from processing import process_page, robots
from db import queries


def get_page_to_process(connection, sleep_time, max_sleeps):
    """
    :param connection: Database connection
    :param sleep_time: Time to sleep between new check for url in frontier
    :param max_sleeps: Maximum number of sleeps before stopping crawler
    :return: New page to process(dict), None if no more pages in frontier
    """
    consecutive_sleeps = 0
    new_page = {}
    while not new_page:
        with connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(queries.q['get_url_id_from_frontier'])
            urls = cur.fetchall()
            if not urls:
                if consecutive_sleeps >= max_sleeps:
                    return None
                logging.info("NO URLS IN FRONTIER, GOING TO SLEEP FOR {0} SECONDS".format(sleep_time))
                consecutive_sleeps += 1
                time.sleep(sleep_time)
            else:
                # get page
                page_id = urls[0]['id']
                cur.execute(queries.q['get_page_by_id'], [page_id])
                new_page = cur.fetchone()
                # mark page as occupied in frontier
                cur.execute(queries.q['update_frontier_page_occ'], [True, page_id])

    return new_page


def crawler(conn, crawler_id):
    # check sites if it can be acessed
    # -> if yes:
    # consult with robots to add a timestamp to the site database when the domain can be acessed next.

    while True:
        can_fetch = False
        current_url = ""
        page_to_free = -1       # id of page to free after getting new page from frontier
        while not can_fetch:
            # get next URL from frontier
            current_page = get_page_to_process(conn, config.sleep_time, config.max_sleeps)
            if not current_page:
                logging.info("**********************************************************************")
                logging.info("          NO MORE URLS TO PARSE, CRAWLER {0} STOPPING.                ".format(crawler_id))
                logging.info("**********************************************************************")
                conn.close()
                return

            if page_to_free >= 0:
                with conn.cursor() as cur:
                    cur.execute(queries.q['update_frontier_page_occ'], [False, page_to_free])
                page_to_free = -1

            current_url = current_page['url']
            current_page_id = current_page['id']
            # check with robots if URL can be fetched
            (can_fetch, delayed) = robots.can_fetch_page(current_url, conn)
            if can_fetch is False:
                if delayed:                                     # can't fetch -> delay
                    page_to_free = current_page_id
                    continue
                else:                                           # can't fetch -> forbidden
                    with conn.cursor() as cur:
                        cur.execute(queries.q['update_page_codes'], ['FORBIDDEN', None, current_page_id])  # mark as forbidden
                        cur.execute(queries.q['remove_from_frontier'], [current_page_id])                  # remove from frontier
                    continue
        process_page.process_page(current_url, conn)


if __name__ == '__main__':
    nr_of_threads = int(sys.argv[1])

    # INIT
    with psycopg2.connect(user=config.db['username'], password=config.db['password'],
                          host=config.db['host'], port=config.db['port'], database=config.db['db_name']) as connection:
        # if frontier empty -> initialize it with seed urls
        with connection.cursor as cur:
            cur.execute("SELECT * FROM crawldb.frontier LIMIT 1")
            frontier_url = cur.fetchone
            if not frontier_url:
                process_page.add_urls_to_frontier(config.seed_urls, connection)
        # make sure all pages in frontier are marked as unoccupied
        with connection.cursor as cur:
            cur.execute("UPDATE crawldb.frontier SET occupied=False")

    # CRAWL
    pool = psycopg2.pool.ThreadedConnectionPool(1, nr_of_threads, user=config.db['username'], password=config.db['password'],
                                                host=config.db['host'], port=config.db['port'], database=config.db['db_name'])
    crawlers = []
    for i in range(nr_of_threads):
        c = threading.Thread(target=crawler, args=(pool.getconn(), i))
        crawlers.append(c)
        c.start()
