from pathlib import Path
import socket
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
API_PROJECT = ROOT / "apps" / "api"
if str(API_PROJECT) not in sys.path:
    sys.path.insert(0, str(API_PROJECT))

from app.extract.security import SSRFValidationError, validate_public_url


class SecurityValidationTests(unittest.TestCase):
    def test_validate_public_url_allows_public_ipv4(self) -> None:
        with patch(
            "app.extract.security.socket.getaddrinfo",
            return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))],
        ):
            result = validate_public_url("https://Example.com:443/path?utm_source=x&a=1#frag")

        self.assertEqual(result, "https://example.com/path?a=1")

    def test_validate_public_url_blocks_private_ip(self) -> None:
        with patch(
            "app.extract.security.socket.getaddrinfo",
            return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.5", 80))],
        ):
            with self.assertRaises(SSRFValidationError):
                validate_public_url("http://example.internal/data")

    def test_validate_public_url_blocks_localhost_hostname(self) -> None:
        with self.assertRaises(SSRFValidationError):
            validate_public_url("http://localhost:8000/health")


if __name__ == "__main__":
    unittest.main()
