import psycopg2
import process_page
# pools
import threading
# multithreading
import config
db = config.db
pool = psycopg2.pool.ThreadedConnectionPool(1, config.nr_of_threads, user=db['username'], password=db['password'],
                                            host=db['host'], port=db['port'], database=db['db_name'])
# conn = pool.getconn(), opcije se potem pool.putconn(conn), pool.closeall()


# sample za threading.

def crawler():
    # tu nekako definiramo crawlerja s pomocjo nasih operacij. verjetno bo en parameter connection, ki mu ga potem v sledecem forloopu dodelimo
    pass


crawlers = []

for i in range(config.nr_of_threads):
    c = threading.Thread(target=crawler)
    crawlers.append(c)
    c.start()
