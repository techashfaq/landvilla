"""Bounded in-memory S3-shaped fixture. NOT evidence of R2 signing/permissions/privacy."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
import threading
from urllib.parse import urlsplit, unquote

BUCKET="landvilla-property-media-rehearsal"
OBJECTS={}
LOCK=threading.Lock()
LIMIT=10*1024*1024


class Storage(BaseHTTPRequestHandler):
    def log_message(self,*_args): pass
    def respond(self,status,body=b"",content_type="application/octet-stream"):
        self.send_response(status)
        self.send_header("Content-Type",content_type)
        self.send_header("Content-Length",str(len(body)))
        self.end_headers()
        if self.command != "HEAD": self.wfile.write(body)
    def handle_request(self):
        path=unquote(urlsplit(self.path).path)
        if path=="/health" and self.command=="GET": return self.respond(200,b"ok")
        if not path.startswith("/"+BUCKET): return self.respond(403)
        if path in ("/"+BUCKET,"/"+BUCKET+"/"):
            return self.respond(200 if self.command=="HEAD" else 405)
        if not path.startswith("/"+BUCKET+"/") or ".." in path.split("/"): return self.respond(403)
        if self.command=="PUT":
            try: size=int(self.headers.get("Content-Length","-1"))
            except ValueError: return self.respond(400)
            if not 0<=size<=LIMIT: return self.respond(413)
            body=self.rfile.read(size)
            if len(body)!=size: return self.respond(400)
            with LOCK:
                if len(OBJECTS)>=20 and path not in OBJECTS: return self.respond(507)
                OBJECTS[path]=(body,self.headers.get("Content-Type","application/octet-stream"))
            return self.respond(200)
        with LOCK:
            if self.command=="DELETE":
                OBJECTS.pop(path,None)
                return self.respond(204)
            item=OBJECTS.get(path)
        if self.command not in ("GET","HEAD"): return self.respond(405)
        return self.respond(200,*item) if item else self.respond(404)
    do_GET=do_HEAD=do_PUT=do_DELETE=handle_request


if __name__=="__main__":
    if os.getenv("DEPLOYMENT_TIER")!="rehearsal": raise SystemExit("Disposable tier required")
    ThreadingHTTPServer(("0.0.0.0",9000),Storage).serve_forever()
