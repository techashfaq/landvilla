import copy
import importlib.util
import ipaddress
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("rehearsal_checker",ROOT/"scripts/check-rehearsal.py")
checker=importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class HostInventory(unittest.TestCase):
    def test_null_builtin_network_ipam_and_real_collision(self):
        networks=[{"IPAM":{"Config":None}},{"IPAM":{"Config":[{"Subnet":"172.17.0.0/16"}]}}]
        results=["host bridge",json.dumps(networks),'[{"dst":"default"},{"dst":"10.1.0.0/16"}]',""]
        with patch.object(checker.subprocess,"run",side_effect=[subprocess.CompletedProcess([],0,s,"") for s in results]):
            checker.host_collisions(ipaddress.IPv4Network("172.20.240.0/24"))
        with patch.object(checker.subprocess,"run",side_effect=[subprocess.CompletedProcess([],0,s,"") for s in results[:2]]):
            with self.assertRaisesRegex(ValueError,"collision"):
                checker.host_collisions(ipaddress.IPv4Network("172.17.240.0/24"))


class RehearsalConfiguration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work=tempfile.TemporaryDirectory(dir=ROOT/".cache",prefix="rehearsal-check-")
        cls.addClassCleanup(cls.work.cleanup)
        env=Path(cls.work.name)/"synthetic.env"
        # Test-only addresses/digests; never approved deployment allocations/artifacts.
        values={"REHEARSAL_SUBNET":"172.30.249.0/24","REHEARSAL_DYNAMIC_RANGE":"172.30.249.128/25","REHEARSAL_WEB_IP":"172.30.249.10"}
        for name,image in (("API","fixture-api"),("WEB","fixture-web"),("MONGO","mongo:8"),("MAIL","axllent/mailpit:v1.29"),("CADDY","caddy:2.11.9-alpine")):
            values["REHEARSAL_"+name+"_IMAGE"]=image+"@sha256:"+"a"*64
        env.write_text("\n".join(k+"="+v for k,v in values.items()),encoding="utf-8")
        cls.model=checker.resolve(env,os.getenv("LANDVILLA_TEST_COMPOSE_BINARY"))

    def reject(self,mutation):
        model=copy.deepcopy(self.model)
        mutation(model)
        with self.assertRaises((ValueError,RuntimeError)): checker.validate(model)

    def test_rehearsal_model(self): checker.validate(self.model)

    def test_no_publication_except_loopback_tls(self):
        for name in ("api","web","mongo","mail","storage"):
            self.reject(lambda m:m["services"][name].update(ports=[{"target":8000,"published":"8000"}]))
        self.reject(lambda m:m["services"]["caddy"]["ports"][0].update(host_ip="0.0.0.0"))

    def test_no_production_targets_or_real_credentials(self):
        for change in ({"DB_NAME":"landvilla_prod"},{"S3_BUCKET":"landvilla-property-media-prod"},
                       {"MONGO_URL":"mongodb+srv://external.invalid/test"},{"S3_ENDPOINT":"https://external.invalid"},
                       {"SMTP_HOST":"smtp.external.invalid"},{"S3_SECRET_ACCESS_KEY":"operator-input"}):
            self.reject(lambda m:m["services"]["api"]["environment"].update(change))

    def test_no_external_network_volume_mount_or_env(self):
        self.reject(lambda m:m["networks"]["rehearsal"].update(internal=False))
        self.reject(lambda m:m["volumes"]["mongo_data"].update(name="landvilla_mongo_data"))
        self.reject(lambda m:m["services"]["api"].update(env_file=["/etc/landvilla/production.env"]))
        self.reject(lambda m:m["services"]["api"].update(volumes=[{"type":"bind","source":"/etc/landvilla/production.env","target":"/app/.env","read_only":True}]))

    def test_no_seed_payment_or_mutable_image(self):
        for key in ("SEED_ON_STARTUP","SEED_DEMO_LISTINGS","ALLOW_LIVE_PAYMENTS","REFUNDS_ENABLED"):
            self.reject(lambda m:m["services"]["api"]["environment"].update({key:"true"}))
        self.reject(lambda m:m["services"]["mongo"].update(image="mongo:latest"))

    def test_invalid_network_identity(self):
        self.reject(lambda m:m["services"]["web"]["networks"]["rehearsal"].update(ipv4_address="172.30.249.140"))
        self.reject(lambda m:m["services"]["api"]["environment"].update(FORWARDED_ALLOW_IPS="*"))

    def test_runtime_command_and_mail_relay_cannot_override_fixture(self):
        self.reject(lambda m:m["services"]["api"].update(command=["unreviewed"]))
        self.reject(lambda m:m["services"]["web"].update(entrypoint=["unreviewed"]))
        self.reject(lambda m:m["services"]["mail"]["environment"].update(MP_SMTP_RELAY_ALL="true"))

    def test_caddy_internal_tls_no_acme(self):
        env={k:v for k,v in os.environ.items() if k.upper() in {"PATH","SYSTEMROOT","WINDIR","COMSPEC","PATHEXT"}}
        result=subprocess.run([os.environ["CADDY_BINARY"],"adapt","--config",str(ROOT/"deploy/Caddyfile.rehearsal"),"--adapter","caddyfile"],env=env,capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)
        model=json.loads(result.stdout)
        self.assertNotIn('"acme"',json.dumps(model))
        self.assertIn('"internal"',json.dumps(model))
        self.assertNotIn("landvilla.in",json.dumps(model))
