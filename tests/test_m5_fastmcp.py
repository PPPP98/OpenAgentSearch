import importlib
import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
MCP_APP_DIR = ROOT / "apps" / "mcp" / "app"


def _load_mcp_package() -> None:
    if "mcp_app" in sys.modules:
        return
    spec = importlib.util.spec_from_file_location(
        "mcp_app",
        MCP_APP_DIR / "__init__.py",
        submodule_search_locations=[str(MCP_APP_DIR)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load mcp_app package")
    module = importlib.util.module_from_spec(spec)
    sys.modules["mcp_app"] = module
    spec.loader.exec_module(module)


_load_mcp_package()
client_module = importlib.import_module("mcp_app.client")
server_module = importlib.import_module("mcp_app.server")
OpenAgentSearchApiClient = client_module.OpenAgentSearchApiClient
build_search_payload = server_module.build_search_payload
build_extract_payload = server_module.build_extract_payload


class FastMCPPayloadTests(unittest.TestCase):
    def test_build_search_payload_validates_and_normalizes(self) -> None:
        payload = build_search_payload(
            query="  agent search ",
            mode="Balanced",
            limit=5,
            page=2,
            extract_top_n=2,
            max_extract_chars=5000,
        )
        self.assertEqual(payload["query"], "agent search")
        self.assertEqual(payload["mode"], "balanced")
        self.assertEqual(payload["limit"], 5)
        self.assertEqual(payload["page"], 2)

    def test_build_search_payload_rejects_invalid_mode(self) -> None:
        with self.assertRaises(ValueError):
            build_search_payload(query="agent", mode="fast")

    def test_build_extract_payload_validates(self) -> None:
        payload = build_extract_payload(url=" https://example.com ", max_chars=1200)
        self.assertEqual(payload, {"url": "https://example.com", "max_chars": 1200})

        with self.assertRaises(ValueError):
            build_extract_payload(url="", max_chars=1200)


class ClientHeaderTests(unittest.TestCase):
    def test_client_build_headers_default_and_override(self) -> None:
        client = OpenAgentSearchApiClient(
            base_url="http://api:8000",
            auth_header_name="Authorization",
            auth_header_value="Bearer base-token",
        )

        base_headers = client._build_headers(auth_header_name=None, auth_header_value=None)
        self.assertEqual(base_headers, {"Authorization": "Bearer base-token"})

        override_headers = client._build_headers(
            auth_header_name="X-API-Key",
            auth_header_value="abc",
        )
        self.assertEqual(override_headers, {"X-API-Key": "abc"})

        no_default_client = OpenAgentSearchApiClient(base_url="http://api:8000")
        with self.assertRaises(ValueError):
            no_default_client._build_headers(auth_header_name="Authorization", auth_header_value=None)


if __name__ == "__main__":
    unittest.main()
