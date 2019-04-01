q = {
    'add_to_frontier': "INSERT INTO crawldb.frontier (page_id) VALUES(%s)",
    'add_new_page': "INSERT INTO crawldb.page (site_id, page_type_code, url) VALUES (%s, %s, %s) RETURNING id",
    'remove_from_frontier': "DELETE FROM crawldb.frontier WHERE page_id=%s",
    'update_page_codes': "UPDATE crawldb.page SET page_type_code=%s, http_status_code=%s, accessed_time=NOW()"
}
