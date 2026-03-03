from pathlib import Path
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]


class M1ComposeTests(unittest.TestCase):
    @unittest.skipIf(shutil.which("docker") is None, "docker is not installed")
    def test_compose_config_is_valid(self) -> None:
        command = ["docker", "compose", "-f", "docker-compose.yml", "config"]
        result = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            self.fail(
                "docker compose config failed\n"
                f"stdout:\n{result.stdout}\n"
                f"stderr:\n{result.stderr}"
            )

        self.assertIn("services:", result.stdout)
        self.assertIn("searxng:", result.stdout)
        self.assertIn("redis:", result.stdout)
        self.assertIn("api:", result.stdout)


if __name__ == "__main__":
    unittest.main()

