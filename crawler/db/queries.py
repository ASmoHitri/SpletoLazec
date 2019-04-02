q = {
    'get_page_id_from_frontier': "UPDATE crawldb.frontier \
                                 SET occupied=True \
                                 WHERE page_id=( \
                                    SELECT page_id \
                                    FROM crawldb.frontier as f \
                                    LEFT JOIN crawldb.page as p \
                                        ON f.page_id=p.id \
                                    WHERE f.occupied=False AND p.site_id IN (\
                                        SELECT id FROM crawldb.site WHERE next_acces<=NOW() OR next_acces IS NULL) \
                                    ORDER BY time_added \
                                    LIMIT 1) \
                                 RETURNING page_id",
    'get_link': "SELECT * FROM crawldb.link WHERE from_page=%s AND to_page=%s",
    'get_page_by_id': "SELECT * FROM crawldb.page WHERE id=%s",
    'get_site_by_domain': "SELECT * FROM crawldb.site WHERE domain=%s",
    'add_to_frontier': "INSERT INTO crawldb.frontier (page_id) VALUES(%s)",
    'add_new_page': "INSERT INTO crawldb.page (site_id, page_type_code, url) VALUES (%s, %s, %s) RETURNING id",
    'add_pages_to_link': "INSERT INTO crawldb.link (from_page, to_page) VALUES (%s, %s)",
    'remove_from_frontier': "DELETE FROM crawldb.frontier WHERE page_id=%s",
    'update_page_codes': "UPDATE crawldb.page \
                          SET page_type_code=%s, http_status_code=%s, accessed_time=NOW() \
                          WHERE id=%s",
    'update_frontier_page_occ&time': "UPDATE crawldb.frontier SET occupied=%s WHERE page_id=%s"
}
