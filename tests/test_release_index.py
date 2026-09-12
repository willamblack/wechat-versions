import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from build_release_index import render_index, version_sort_key  # noqa: E402


class ReleaseIndexTests(unittest.TestCase):
    def test_fourth_version_component_is_numeric(self):
        tags = ["4.1.13.8_269576", "4.1.13.60_269628",
                "4.1.13.63_269631", "4.1.13.61_269629"]
        self.assertEqual(sorted(tags, key=version_sort_key, reverse=True),
                         ["4.1.13.63_269631", "4.1.13.61_269629",
                          "4.1.13.60_269628", "4.1.13.8_269576"])

    def test_index_links_assets_in_sorted_order(self):
        items = []
        for tag in ("4.1.13.8_269576", "4.1.13.63_269631"):
            items.append({"tag_name": tag, "html_url": f"https://example.test/{tag}",
                          "assets": [
                              {"name": f"WeChatMac-{tag}.dmg", "browser_download_url": f"https://example.test/{tag}.dmg"},
                              {"name": f"WeChatMac-{tag}.dmg.sha256", "browser_download_url": f"https://example.test/{tag}.sha256"},
                          ]})
        text = render_index(items)
        self.assertLess(text.index("| 4.1.13.63 |"), text.index("| 4.1.13.8 |"))
        self.assertIn("[下载 DMG](https://example.test/4.1.13.63_269631.dmg)", text)


if __name__ == "__main__":
    unittest.main()
