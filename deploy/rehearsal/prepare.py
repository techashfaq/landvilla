"""Explicit disposable replica/index setup. Cannot select a production endpoint."""
import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import OperationFailure


def prepare_tls(directory):
    # A disposable CA authenticates only the local SMTP fixture; TLS is never disabled.
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
    directory.mkdir(mode=0o700,exist_ok=True)
    files=[directory/name for name in ("ca.crt","mail.crt","mail.key")]
    if any(path.exists() for path in files):
        # Re-running one-shot setup must not rotate trust beneath running Mailpit.
        if not all(path.is_file() for path in files): raise RuntimeError("Incomplete fixture TLS")
        existing=x509.load_pem_x509_certificate(files[0].read_bytes())
        if existing.not_valid_after_utc <= datetime.now(timezone.utc)+timedelta(hours=1):
            raise RuntimeError("Expired fixture TLS requires explicit disposable cleanup")
        return
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,"LANDVILLA disposable SMTP fixture")])
    now=datetime.now(timezone.utc)
    certificate=(x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
                 .serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(minutes=1))
                 .not_valid_after(now+timedelta(days=2)).add_extension(x509.BasicConstraints(ca=True,path_length=0),critical=True)
                 .add_extension(x509.KeyUsage(True,False,False,False,False,True,True,False,False),critical=True)
                 .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()),critical=False)
                 .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(key.public_key()),critical=False).sign(key,hashes.SHA256()))
    leaf=(x509.CertificateBuilder().subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,"mail")]))
          .issuer_name(name).public_key(key.public_key()).serial_number(x509.random_serial_number())
          .not_valid_before(now-timedelta(minutes=1)).not_valid_after(now+timedelta(days=2))
          .add_extension(x509.BasicConstraints(ca=False,path_length=None),critical=True)
          .add_extension(x509.KeyUsage(True,False,True,False,False,False,False,False,False),critical=True)
          .add_extension(x509.SubjectAlternativeName([x509.DNSName("mail")]),critical=False)
          .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(key.public_key()),critical=False).sign(key,hashes.SHA256()))
    public=certificate.public_bytes(serialization.Encoding.PEM)
    (directory/"ca.crt").write_bytes(public)
    (directory/"mail.crt").write_bytes(leaf.public_bytes(serialization.Encoding.PEM))
    (directory/"mail.key").write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
    (directory/"mail.key").chmod(0o600)


async def main():
    if (os.getenv("DEPLOYMENT_TIER") != "rehearsal" or os.getenv("DB_NAME") != "landvilla_rehearsal" or
        os.getenv("MONGO_URL") != "mongodb://mongo:27017/landvilla_rehearsal?replicaSet=lv_rehearsal"):
        raise RuntimeError("Disposable rehearsal target required")
    prepare_tls(Path("/home/app/tls"))
    now=datetime.now(timezone.utc)
    direct=AsyncIOMotorClient("mongodb://mongo:27017/?directConnection=true", serverSelectionTimeoutMS=3000)
    try:
        try:
            await direct.admin.command("replSetInitiate", {"_id":"lv_rehearsal","members":[{"_id":0,"host":"mongo:27017"}]})
        except OperationFailure as error:
            if error.code != 23: raise  # AlreadyInitialized only.
    finally: direct.close()
    client=AsyncIOMotorClient(os.environ["MONGO_URL"], serverSelectionTimeoutMS=3000)
    try:
        for _ in range(20):
            try:
                if (await client.admin.command("hello")).get("isWritablePrimary"): break
            except Exception: pass
            await asyncio.sleep(1)
        else: raise RuntimeError("Disposable replica did not elect a primary")
        sys.path.insert(0,"/app")
        from seed import m001_indexes, m002_identity_indexes
        await m001_indexes(client.landvilla_rehearsal)
        await m002_identity_indexes(client.landvilla_rehearsal)
        await client.landvilla_rehearsal.schema_migrations.update_one(
            {"version":"002_identity_indexes"}, {"$setOnInsert":{"version":"002_identity_indexes","applied_at":now}}, upsert=True)
        # Minimal synthetic reference fixture, only on the exact guarded disposable DB.
        # No customer listings, accounts, production seed runner or production data.
        await client.landvilla_rehearsal.cities.update_one({"slug":"ujjain"}, {"$setOnInsert":{
            "id":"city_rehearsal","slug":"ujjain","name_en":"Rehearsal fixture",
            "name_hi":"Rehearsal fixture","is_active":True,"created_at":now}}, upsert=True)
        print("PASS disposable replica, identity indexes and synthetic city fixture")
    finally: client.close()


if __name__ == "__main__":
    try: asyncio.run(main())
    except Exception as error:
        print("FAIL disposable preparation: "+type(error).__name__+"; details withheld",file=sys.stderr)
        raise SystemExit(1)
