"""Read-only Windows-friendly DNS/TCP/TLS checks, without exposing the configured URI."""
import json
import os
import socket
import ssl
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv
import dns.resolver


def main():
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    try:
        parsed = urlsplit(os.environ["MONGO_URL"])
        if parsed.scheme != "mongodb+srv" or not parsed.hostname:
            print(json.dumps({"dns_srv": "not_applicable", "hint": "Configured URI is not an SRV connection; no changes made"}))
            return 1
        records = list(dns.resolver.resolve("_mongodb._tcp." + parsed.hostname, "SRV", lifetime=8))
    except Exception as exc:
        category = "dns_timeout" if isinstance(exc, dns.exception.Timeout) else "dns_or_configuration_error"
        print(json.dumps({"dns_srv": category, "error_type": type(exc).__name__}))
        return 1
    print(json.dumps({"dns_srv": "resolved", "endpoint_count": len(records)}), flush=True)
    failed = False
    context = ssl.create_default_context()  # Hostname and certificate verification always enabled.
    for index, record in enumerate(records[:3], start=1):
        host = str(record.target).rstrip(".")
        report = {"endpoint_number": index}
        try:
            with socket.create_connection((host, record.port), timeout=8) as connection:
                report["tcp"] = "connected"
                try:
                    with context.wrap_socket(connection, server_hostname=host):
                        report["tls"] = "verified"
                except ssl.SSLCertVerificationError:
                    report["tls"] = "certificate_verification_failed"
                    failed = True
                except (ssl.SSLError, OSError, TimeoutError) as exc:
                    report["tls"] = "handshake_failed_or_timed_out"
                    report["tls_error_type"] = type(exc).__name__
                    # Fixed codes only: raw exception text can expose remote endpoints.
                    reason = getattr(exc, "reason", None)
                    if reason in {"TLSV1_ALERT_INTERNAL_ERROR", "UNEXPECTED_EOF_WHILE_READING",
                                  "SSLV3_ALERT_HANDSHAKE_FAILURE", "WRONG_VERSION_NUMBER"}:
                        report["tls_reason"] = reason
                    failed = True
        except (OSError, TimeoutError):
            report["tcp"] = "connection_failed_or_timed_out"
            failed = True
        print(json.dumps(report), flush=True)
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
