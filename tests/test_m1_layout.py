from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class M1LayoutTests(unittest.TestCase):
    def test_expected_directories_exist(self) -> None:
        expected = [
            ROOT / "apps" / "api",
            ROOT / "apps" / "mcp",
            ROOT / "infra" / "searxng",
            ROOT / "tests",
        ]
        for path in expected:
            self.assertTrue(path.is_dir(), f"missing directory: {path}")

    def test_expected_files_exist(self) -> None:
        expected = [
            ROOT / "docker-compose.yml",
            ROOT / "infra" / "searxng" / "settings.yml",
            ROOT / "apps" / "api" / "app" / "main.py",
            ROOT / "apps" / "mcp" / "app" / "main.py",
        ]
        for path in expected:
            self.assertTrue(path.is_file(), f"missing file: {path}")

    def test_browser_profile_is_marked_optional(self) -> None:
        compose_text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn("browser:", compose_text)
        self.assertIn('profiles: ["browser"]', compose_text)


if __name__ == "__main__":
    unittest.main()

