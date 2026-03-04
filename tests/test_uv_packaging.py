from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]


class UvPackagingTests(unittest.TestCase):
    def _read_toml(self, path: Path) -> dict:
        return tomllib.loads(path.read_text(encoding="utf-8"))

    def test_api_uses_pyproject_and_uv_lock(self) -> None:
        pyproject_path = ROOT / "apps" / "api" / "pyproject.toml"
        lock_path = ROOT / "apps" / "api" / "uv.lock"
        self.assertTrue(pyproject_path.is_file())
        self.assertTrue(lock_path.is_file())
        self.assertFalse((ROOT / "apps" / "api" / "requirements.txt").exists())

        data = self._read_toml(pyproject_path)
        dependencies = set(data["project"]["dependencies"])
        self.assertIn("fastapi==0.116.1", dependencies)
        self.assertIn("uvicorn[standard]==0.35.0", dependencies)

    def test_mcp_has_uv_project_files(self) -> None:
        pyproject_path = ROOT / "apps" / "mcp" / "pyproject.toml"
        lock_path = ROOT / "apps" / "mcp" / "uv.lock"
        self.assertTrue(pyproject_path.is_file())
        self.assertTrue(lock_path.is_file())

        data = self._read_toml(pyproject_path)
        self.assertEqual(data["project"]["name"], "openagentsearch-mcp")
        dependencies = set(data["project"]["dependencies"])
        self.assertIn("fastmcp==3.1.0", dependencies)
        self.assertIn("httpx==0.28.1", dependencies)


if __name__ == "__main__":
    unittest.main()

