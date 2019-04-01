db = {
    'host': '192.168.99.100',
    'port': '5432',
    'db_name': 'crawler',
    'username': 'postgres',
    'password': 'postgres'
}
seed_urls = ["http://evem.gov.si/", "http://e-uprava.gov.si", "http://podatki.gov.si", "http://e-prostor.gov.si"]       # must be canonicalized
search_domain = "gov.si"
sleep_time = 60        # in seconds
max_sleeps = 5
