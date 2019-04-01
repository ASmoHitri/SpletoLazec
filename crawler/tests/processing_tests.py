import unittest

from process_page import canonicalize_url
from process_page import get_page_state


class TestProcessingMethods(unittest.TestCase):
    def test_canonicalize_url(self):
        self.assertEqual(canonicalize_url("http://some.domain.com", "", ""), "http://some.domain.com/")                 # add trailing / for root
        self.assertEqual(canonicalize_url("http://domain.com:80/path#there", "", ""), "http://domain.com/path")         # remove port & fragment     ?what if not 'standard' port?
        self.assertEqual(canonicalize_url("http://domain.com/test/./../end", "", ""), "http://domain.com/end")          # remove unnecessary path parts
        self.assertEqual(canonicalize_url("/relative/path", "http", "domain.com"), "http://domain.com/relative/path")   # relative to absolute path
        self.assertEqual(canonicalize_url("http://domain.com/s pace.php", "", ""), "http://domain.com/s%20pace.php")    # test quoting
        self.assertEqual(canonicalize_url("http://bad.domain/", "", "", "domain.com"), None)                            # filter domain
        self.assertEqual(canonicalize_url("http://domain.com/index.html", "", ""), "http://domain.com/")                # remove index.html

    def test_get_page_state(self):
        self.assertEqual(get_page_state("http://httpstat.us/200"), ("ok", 200))
        self.assertEqual(get_page_state("http://httpstat.us/500"), ("error", 500))
        # self.assertEqual(get_page_state("http://ne-obstajam.comm/"), (None, "Error fetching page"))


if __name__ == '__main__':
    unittest.main()
