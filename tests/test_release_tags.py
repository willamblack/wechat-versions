import plistlib
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from destVersionForMac import get_tag_from_plist  # noqa: E402
from sync_upstream_releases import update_dest_version  # noqa: E402


class ReleaseTagTests(unittest.TestCase):
    def test_exact_version_and_build_from_real_release_metadata(self):
        with tempfile.TemporaryDirectory() as temp:
            plist = Path(temp) / "WeChat.app" / "Contents" / "Info.plist"
            plist.parent.mkdir(parents=True)
            with plist.open("wb") as handle:
                plistlib.dump({"WeChatBundleVersion": "4.1.13.63",
                               "CFBundleShortVersionString": "4.1.13",
                               "CFBundleVersion": "269631"}, handle)
            self.assertEqual(get_tag_from_plist(temp), "4.1.13.63_269631")

    def test_fallback_version_keeps_build(self):
        with tempfile.TemporaryDirectory() as temp:
            plist = Path(temp) / "WeChat.app" / "Contents" / "Info.plist"
            plist.parent.mkdir(parents=True)
            with plist.open("wb") as handle:
                plistlib.dump({"CFBundleShortVersionString": "3.5.5",
                               "CFBundleVersion": "12345"}, handle)
            self.assertEqual(get_tag_from_plist(temp), "3.5.5_12345")

    def test_sync_changes_only_dest_version(self):
        old = "WeChat for Mac automatic release\n- DestVersion: 4.1.13.63\n- Sha256: abc\n"
        self.assertEqual(update_dest_version(old, "4.1.13.63_269631"),
                         "WeChat for Mac automatic release\n- DestVersion: 4.1.13.63_269631\n- Sha256: abc\n")


if __name__ == "__main__":
    unittest.main()
