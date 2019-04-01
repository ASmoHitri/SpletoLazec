q = {
    'get_url_id_from_frontier': "SELECT page_id FROM crawldb.frontier WHERE occupied=False ORDER BY timestamp LIMIT 1",
    'get_page_by_id': "SELECT * FROM crawldb.page WHERE id=%s",
    'get_site_by_domain': "SELECT * FROM crawldb.site WHERE domain=%s",
    'add_to_frontier': "INSERT INTO crawldb.frontier (page_id) VALUES(%s)",
    'add_new_page': "INSERT INTO crawldb.page (site_id, page_type_code, url) VALUES (%s, %s, %s) RETURNING id",
    'remove_from_frontier': "DELETE FROM crawldb.frontier WHERE page_id=%s",
    'update_page_codes': "UPDATE crawldb.page \
                          SET page_type_code=%s, http_status_code=%s, accessed_time=NOW() \
                          WHERE id=%s",
    'update_frontier_page_occ': "UPDATE crawldb.frontier SET occupied=%s WHERE page_id=%s"
}
