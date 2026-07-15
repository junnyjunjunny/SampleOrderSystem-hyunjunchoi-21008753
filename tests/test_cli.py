import unittest

from app.cli import paginate


class PaginateTest(unittest.TestCase):
    def test_first_page_by_default(self):
        items = list(range(1, 8))  # 7 items
        page_items, page, total_pages = paginate(items, page=0, page_size=5)
        self.assertEqual(page_items, [1, 2, 3, 4, 5])
        self.assertEqual(page, 0)
        self.assertEqual(total_pages, 2)

    def test_computes_total_pages(self):
        items = list(range(1, 11))  # 10 items, page_size 5 -> 2 pages exactly
        _, _, total_pages = paginate(items, page=0, page_size=5)
        self.assertEqual(total_pages, 2)

    def test_clamps_page_within_valid_range(self):
        items = list(range(1, 8))  # 7 items, 2 pages
        page_items, page, total_pages = paginate(items, page=5, page_size=5)
        self.assertEqual(page, 1)
        self.assertEqual(page_items, [6, 7])

        page_items, page, total_pages = paginate(items, page=-3, page_size=5)
        self.assertEqual(page, 0)
        self.assertEqual(page_items, [1, 2, 3, 4, 5])

    def test_empty_items_returns_single_page(self):
        page_items, page, total_pages = paginate([], page=0, page_size=5)
        self.assertEqual(page_items, [])
        self.assertEqual(page, 0)
        self.assertEqual(total_pages, 1)


if __name__ == "__main__":
    unittest.main()
