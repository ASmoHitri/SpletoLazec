db = {                      # DB connection values
    'host': '192.168.99.100',
    'port': '5432',
    'db_name': 'crawler',
    'username': 'postgres',
    'password': 'postgres'
}
# seed_urls = ["http://evem.gov.si/", "http://e-uprava.gov.si/", "http://podatki.gov.si/", "http://e-prostor.gov.si/"]
seed_urls = ["http://evem.gov.si/", "http://e-prostor.gov.si/"]    # urls to use for frontier initialization (must be canonicalized)
search_domains = ["evem.gov.si", "e-prostor.gov.si"]   # domains to search ([] for any domain)
sleep_time = 60             # time to wait in case of empty frontier (in seconds)
max_sleeps = 5              # maximum times of waiting for new URL in frontier before stopping
