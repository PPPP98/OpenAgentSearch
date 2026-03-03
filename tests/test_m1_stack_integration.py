import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import unittest
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
RUN_INTEGRATION = os.environ.get("OAS_RUN_DOCKER_TESTS") == "1"
DEFAULT_SERVICES = ("redis", "searxng", "api")


def _run_compose(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", "compose", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def _service_container_id(service: str) -> str:
    result = _run_compose("ps", "-q", service)
    if result.returncode != 0:
        raise RuntimeError(f"failed to inspect compose service {service}: {result.stderr}")
    return result.stdout.strip()


def _is_service_healthy(service: str) -> bool:
    container_id = _service_container_id(service)
    if not container_id:
        return False
    inspect = subprocess.run(
        ["docker", "inspect", "--format", "{{.State.Health.Status}}", container_id],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return inspect.returncode == 0 and inspect.stdout.strip() == "healthy"


def _wait_for_services_healthy(services: tuple[str, ...], timeout_seconds: int = 180) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if all(_is_service_healthy(svc) for svc in services):
            return True
        time.sleep(3)
    return False


@unittest.skipIf(shutil.which("docker") is None, "docker is not installed")
@unittest.skipUnless(RUN_INTEGRATION, "set OAS_RUN_DOCKER_TESTS=1 to run integration tests")
class M1StackIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        up = _run_compose("up", "-d", "--build")
        if up.returncode != 0:
            raise RuntimeError(f"docker compose up failed: {up.stderr}")

    @classmethod
    def tearDownClass(cls) -> None:
        _run_compose("down", "-v", "--remove-orphans")

    def test_default_services_become_healthy(self) -> None:
        self.assertTrue(
            _wait_for_services_healthy(DEFAULT_SERVICES),
            "services did not become healthy within timeout",
        )

    def test_api_health_endpoint(self) -> None:
        self.assertTrue(
            _wait_for_services_healthy(DEFAULT_SERVICES),
            "services did not become healthy before API health check",
        )
        with urlopen("http://127.0.0.1:8000/health", timeout=10) as response:
            self.assertEqual(response.status, 200)
            payload = json.loads(response.read().decode("utf-8"))
        self.assertEqual(payload.get("status"), "ok")

    def test_searxng_returns_json(self) -> None:
        self.assertTrue(
            _wait_for_services_healthy(DEFAULT_SERVICES),
            "services did not become healthy before SearXNG query",
        )
        with urlopen("http://127.0.0.1:8080/search?format=json&q=agent", timeout=20) as response:
            self.assertEqual(response.status, 200)
            payload = json.loads(response.read().decode("utf-8"))
        self.assertIsInstance(payload, dict)
        self.assertIn("results", payload)


if __name__ == "__main__":
    unittest.main()
