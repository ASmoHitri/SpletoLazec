import psycopg2
import process_page
import robots
# pools
import threading
# multithreading
import config
import sys
db = config.db

# conn = pool.getconn(), opcije se potem pool.putconn(conn), pool.closeall()


# sample za threading.

def crawler(conn):
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
    #

    pass


if __name__ == '__main__':
    nr_of_threads = sys.argv[1]
    pool = psycopg2.pool.ThreadedConnectionPool(1, nr_of_threads, user=db['username'], password=db['password'],
                                                host=db['host'], port=db['port'], database=db['db_name'])

    crawlers = []
    for i in range(nr_of_threads):
        c = threading.Thread(target=crawler, args=(pool.getconn(),))
        crawlers.append(c)
        c.start()
    # QUESTION, moramo tu kaj ustaviti? ali je to to? ce tu damo pool.closeall() se mi zdi da vsi crawlerji crknejo.
