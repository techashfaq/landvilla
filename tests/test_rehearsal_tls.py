"""Real native loopback TLS with the rehearsal Caddyfile; no Docker/ACME/providers."""
import http.client
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import os
from pathlib import Path
import socket
import ssl
import subprocess
import tempfile
import threading
import time
import unittest

ROOT=Path(__file__).resolve().parents[1]


class Ready(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Length","2")
        self.end_headers()
        self.wfile.write(b"ok")
    def log_message(self,*_): pass


class RehearsalTLS(unittest.TestCase):
    def test_tls_chain_sni_and_hidden_probes(self):
        with tempfile.TemporaryDirectory(dir=ROOT/".cache",prefix="rehearsal-tls-") as directory:
            work=Path(directory)
            upstream=ThreadingHTTPServer(("127.0.0.1",0),Ready)
            threading.Thread(target=upstream.serve_forever,daemon=True).start()
            def port():
                with socket.socket() as sock:
                    sock.bind(("127.0.0.1",0))
                    return sock.getsockname()[1]
            tls_port,health_port=port(),port()
            config=(ROOT/"deploy/Caddyfile.rehearsal").read_text().replace("8443",str(tls_port)).replace("8080",str(health_port))
            config=config.replace("web:3000",f"127.0.0.1:{upstream.server_port}")
            config=config.replace("tls internal","bind 127.0.0.1\n tls internal")
            (work/"Caddyfile").write_text(config)
            env={k:v for k,v in os.environ.items() if k.upper() in {"PATH","SYSTEMROOT","WINDIR","COMSPEC","PATHEXT"}}
            env.update(XDG_DATA_HOME=str(work/"data"),XDG_CONFIG_HOME=str(work/"config"),HOME=str(work),
                       TEMP=str(work),TMP=str(work),LANDVILLA_INGRESS_TOKEN="d"*64)
            with (work/"caddy.log").open("wb") as log:
                process=subprocess.Popen([os.environ["CADDY_BINARY"],"run","--config",str(work/"Caddyfile"),"--adapter","caddyfile"],
                    env=env,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW if os.name=="nt" else 0)
                try:
                    ca=work/"data/caddy/pki/authorities/local/root.crt"
                    for _ in range(100):
                        if ca.exists(): break
                        if process.poll() is not None: self.fail("Local TLS fixture exited")
                        time.sleep(.05)
                    self.assertTrue(ca.exists(),"Public rehearsal CA created")
                    context=ssl.create_default_context(cafile=str(ca))
                    for path,status in (("/",200),("/ready",404),("/health",404)):
                        connection=http.client.HTTPSConnection("localhost",tls_port,context=context,timeout=5)
                        try:
                            connection.request("GET",path)
                            response=connection.getresponse()
                            self.assertEqual(response.status,status)
                            response.read()
                        finally: connection.close()
                    connection=http.client.HTTPSConnection("localhost",tls_port,context=context,timeout=5)
                    try:
                        connection.request("GET","/",headers={"Host":"untrusted.invalid"})
                        self.assertEqual(connection.getresponse().status,421)
                    finally: connection.close()
                finally:
                    process.terminate()
                    process.wait(timeout=10)
                    upstream.shutdown()
                    upstream.server_close()
