import hashlib
import hmac
import os
import time
import unittest
from unittest.mock import patch
from starlette.requests import Request
from fastapi import HTTPException
from client_identity import rate_identity


class ClientIdentity(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, APP_ENV="production", CLIENT_IP_MODE="signed-v1",
                              FORWARDED_ALLOW_IPS="172.30.250.10", WEB_API_IP_KEY="e" * 64)
        self.env.start()
        self.addCleanup(self.env.stop)

    def request(self, ip="203.0.113.10", peer="172.30.250.10", age=0, path="/api/auth/otp/request", extra=()):
        stamp = str(int(time.time()) - age)
        message = "\n".join(("v1", stamp, "POST", "/api/auth/otp/request", ip))
        signature = hmac.new(bytes.fromhex("e" * 64), message.encode(), hashlib.sha256).hexdigest()
        return Request({"type": "http", "method": "POST", "scheme": "https", "path": path,
                        "query_string": b"", "server": ("api",8000), "client": (peer,1234),
                        "headers": [(b"host",b"api"), (b"x-lv-client-ip",ip.encode()),
                                    (b"x-lv-ip-time",stamp.encode()), (b"x-lv-ip-signature",signature.encode()), *extra]})

    def test_distinct_visitors_have_distinct_buckets(self):
        self.assertNotEqual(rate_identity(self.request()), rate_identity(self.request(ip="203.0.113.11")))

    def test_peer_signature_path_age_and_duplicate_boundaries(self):
        invalid = [self.request(peer="172.30.250.11"), self.request(age=120), self.request(age=-120),
                   self.request(path="/api/auth/logout"), self.request(ip="bad"),
                   self.request(extra=[(b"x-lv-client-ip",b"203.0.113.12")]),
                   self.request(extra=[(b"x-forwarded-for",b"203.0.113.10")])]
        for request in invalid:
            with self.subTest(scope=request.scope["path"]), self.assertRaises(HTTPException):
                rate_identity(request)
        with patch.dict(os.environ, WEB_API_IP_KEY="f"*64), self.assertRaises(HTTPException):
            rate_identity(self.request())

    def test_mapped_ipv6_has_same_rate_identity(self):
        self.assertEqual(rate_identity(self.request(ip="::ffff:203.0.113.10")), "203.0.113.10")

    def test_missing_attestation_is_rejected(self):
        request=self.request()
        request.scope["headers"]=[(b"host",b"api")]
        with self.assertRaises(HTTPException): rate_identity(request)
