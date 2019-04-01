q = {
    'add_to_frontier': "INSERT INTO crawldb.frontier (page_id) VALUES(%s)",
    'remove_from_frontier': "DELETE FROM crawldb.frontier WHERE page_id=%s"
}
