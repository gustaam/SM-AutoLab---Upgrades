import unittest
from unittest.mock import patch

import atualizacao


class VersionComparisonTests(unittest.TestCase):
    def test_fourth_component_is_not_truncated(self):
        self.assertLess(atualizacao._version_tuple("2.99.9"), atualizacao._version_tuple("2.99.9.1"))
        self.assertLess(atualizacao._version_tuple("2.99.9.1"), atualizacao._version_tuple("2.99.10"))

    def test_trailing_zero_component_is_equivalent(self):
        self.assertEqual(atualizacao._version_tuple("2.99.9"), atualizacao._version_tuple("v2.99.9.0"))
        self.assertEqual(atualizacao._version_tuple("2.99.9.1"), atualizacao._version_tuple("2.99.9.1.0"))

    def test_invalid_version_is_rejected(self):
        self.assertEqual(atualizacao._version_tuple("2.99.x"), ())
        self.assertEqual(atualizacao._version_tuple(""), ())
        self.assertEqual(atualizacao._version_tuple("v"), ())


class UpdateDiscoveryTests(unittest.TestCase):
    def _release(self, tag: str) -> dict:
        return {
            "tag_name": tag,
            "draft": False,
            "prerelease": False,
            "name": f"SM AutoLab {tag.lstrip('vV')}",
            "html_url": "https://example.invalid/release",
            "assets": [{
                "name": "SM.AutoLab.exe",
                "browser_download_url": "https://example.invalid/app.exe",
                "digest": "sha256:abc123",
            }],
        }

    def test_discovers_four_component_release_from_three_component_current_version(self):
        release = self._release("v2.99.9.1")
        manifest = {
            "channel": atualizacao.UPDATE_CHANNEL,
            "version": "2.99.9.1",
            "tag": "v2.99.9.1",
            "main_asset": "SM AutoLab.exe",
        }
        with patch.object(atualizacao, "current_version", return_value="2.99.9"), patch.object(
            atualizacao, "fetch_releases", return_value=[release]
        ), patch.object(atualizacao, "_load_release_manifest", return_value=manifest):
            update = atualizacao.find_update()

        self.assertIsNotNone(update)
        self.assertEqual(update["version"], "2.99.9.1")
        self.assertEqual(update["asset_name"], "SM.AutoLab.exe")
        self.assertEqual(update["sha256"], "abc123")

    def test_discovers_standard_successor_from_four_component_current_version(self):
        release = self._release("v2.99.10")
        manifest = {
            "channel": atualizacao.UPDATE_CHANNEL,
            "version": "2.99.10",
            "tag": "v2.99.10",
            "main_asset": "SM AutoLab.exe",
        }
        with patch.object(atualizacao, "current_version", return_value="2.99.9.1"), patch.object(
            atualizacao, "fetch_releases", return_value=[release]
        ), patch.object(atualizacao, "_load_release_manifest", return_value=manifest):
            update = atualizacao.find_update()

        self.assertIsNotNone(update)
        self.assertEqual(update["version"], "2.99.10")

    def test_does_not_offer_same_version_with_different_prefix(self):
        release = self._release("V2.99.9.0")
        with patch.object(atualizacao, "current_version", return_value="2.99.9"), patch.object(
            atualizacao, "fetch_releases", return_value=[release]
        ):
            self.assertIsNone(atualizacao.find_update())


if __name__ == "__main__":
    unittest.main()
