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


# conn = pool.getconn(), opcije se potem pool.putconn(conn), pool.closeall()

def crawler(conn, crawler_id):
    # PREDLAGANA STRUKTURA ZA FRONTIER columns = site_id (zvezano z crawldb.page), time_added_to_frontier(po tem bomo sortiral) , occupied (booean)

    # if frontier is empty, stop or wait? kako bomo? nek while frontier != empty?
    # get correct website from frontier (and mark),
    # check sites if it can be acessed
    # -> if yes:
    # consult with robots to add a timestamp to the site database when the domain can be acessed next.
    # -> if no:
    # if cant be accessed due to delay: return to frontier (unmark) last
    # if cannot be accessed due to it being forbidden, add to crawldb.page with pade type code fobidden (add this to the database under page type codes.)
    #  and get the next page in line and repeat the process, untill you find a valid page..
    # when we have a page we can process_page()
    # cur = conn.cursor()

    # # DB TEST
    # with conn.cursor() as cursor:
    #     cursor.execute("insert into crawldb.site (\"domain\") VALUES ('moja domena')")
    #     cursor.execute("SELECT * from crawldb.site where domain=%s", ['moja domena'])
    #     res = cursor.fetchall()
    # print(res)
    # return
    consecutive_sleeps = 0
    max_sleeps = 5
    sleep_time = 60     # sleep in seconds
    while True: # TODO kaksen bo pogoj?
        # get next URL from frontier
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(queries.q['get_url_id_from_frontier'])
        urls = cur.fetchall()
        if not urls:
            if consecutive_sleeps >= max_sleeps:
                logging.log("************************************************************************")
                logging.log("          NO MORE URLS TO PARSE, CRAWLER {0} STOPPING.                   ".format(crawler_id))
                logging.log("************************************************************************")
                return
            logging.log("NO URLS IN FRONTIER, GOING TO SLEEP FOR {0} SECONDS".format(sleep_time))
            consecutive_sleeps += 1
            time.sleep(sleep_time)
            continue

        # mark page as occupied in frontier
        cur.execute(queries.q['update_frontier_page_occ'])
        cur.commit()

        consecutive_sleeps = 0      # reset consecutive sleeps counter
        cur.exec(queries.q['get_page_by_id'], [urls[0]['id']])
        current_page = cur.fetchone()
        current_url = current_page['url']
        # check with robots if URL can be fetched

        cur.close()


if __name__ == '__main__':
    nr_of_threads = int(sys.argv[1])
    pool = psycopg2.pool.ThreadedConnectionPool(1, nr_of_threads, user=config.db['username'], password=config.db['password'],
                                                host=config.db['host'], port=config.db['port'], database=config.db['db_name'])

    crawlers = []
    for i in range(nr_of_threads):
        c = threading.Thread(target=crawler, args=(pool.getconn(), i))
        crawlers.append(c)
        c.start()
    # QUESTION, moramo tu kaj ustaviti? ali je to to? ce tu damo pool.closeall() se mi zdi da vsi crawlerji crknejo.
