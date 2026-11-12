import importlib.util
from pathlib import Path
import threading
import unittest
from http.server import ThreadingHTTPServer
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("storage_fixture",ROOT/"deploy/rehearsal/storage_mock.py")
fixture=importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


class StorageFixture(unittest.TestCase):
    def setUp(self):
        fixture.OBJECTS.clear()
        self.server=ThreadingHTTPServer(("127.0.0.1",0),fixture.Storage)
        threading.Thread(target=self.server.serve_forever,daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.client=boto3.client("s3",endpoint_url=f"http://127.0.0.1:{self.server.server_port}",
                                 aws_access_key_id="rehearsal-only",aws_secret_access_key="rehearsal-only-never-production",
                                 region_name="us-east-1",config=Config(signature_version="s3v4",retries={"total_max_attempts":1},
                                 connect_timeout=1,read_timeout=2))
        self.addCleanup(self.client.close)

    def test_actual_sdk_readiness_put_get_delete_mock_only(self):
        self.client.head_bucket(Bucket=fixture.BUCKET)
        self.assertEqual(fixture.OBJECTS,{})
        body=b"synthetic-not-customer-media"
        self.client.put_object(Bucket=fixture.BUCKET,Key="files/fixture",Body=body,ContentType="image/jpeg")
        item=self.client.get_object(Bucket=fixture.BUCKET,Key="files/fixture")
        self.assertEqual(item["Body"].read(),body)
        item["Body"].close()
        self.assertEqual(item["ContentType"],"image/jpeg")
        self.client.delete_object(Bucket=fixture.BUCKET,Key="files/fixture")
        self.assertEqual(fixture.OBJECTS,{})

    def test_production_and_unknown_buckets_rejected(self):
        for bucket in ("landvilla-property-media-prod","unknown"):
            with self.assertRaises(ClientError): self.client.head_bucket(Bucket=bucket)
