"""Retain complete SBOMs and unsuppressed image scans on disposable CI only."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / ".cache/linux-rehearsal"
VERSION = "0.121.3"
ARCHIVE_SHA256 = "e9da18cc1429e786722e32161288103600efffd8e483c90761f90485bd1bec85"
SYFT_VERSION = "1.57.1"
# Official GitHub release asset digest rechecked on 2026-11-13.
SYFT_SHA256 = "bf52519eb57f675d47c07d43213cb6dff6449f3d6d1147ff6701ed91f44eef0c"
NAMES = ("API", "WEB", "CADDY", "MONGO", "MAIL")


def require(value, label):
    if not value:
        raise RuntimeError(label)


def json_command(command, env):
    process = subprocess.run(command, cwd=WORK, env=env, capture_output=True,
                             text=True, timeout=600, check=False)
    require(process.returncode == 0, "Evidence command failed")
    return json.loads(process.stdout)


def install_tool(name, version, expected_hash):
    url = f"https://github.com/anchore/{name}/releases/download/v{version}/{name}_{version}_linux_amd64.tar.gz"
    with urllib.request.urlopen(url, timeout=60) as response:
        data = response.read(100 * 1024 * 1024)
    require(hashlib.sha256(data).hexdigest() == expected_hash, "Tool checksum mismatch")
    archive = WORK / (name + ".tar.gz")
    archive.write_bytes(data)
    binary = WORK / name
    with tarfile.open(archive, "r:gz") as bundle:
        member = bundle.getmember(name)
        require(member.isfile() and member.size < 200 * 1024 * 1024, "Invalid tool archive")
        binary.write_bytes(bundle.extractfile(member).read())
    binary.chmod(0o700)
    return binary


def image_identity(metadata, reference, artifact, commit):
    image_id = metadata.get("Id", "")
    require(bool(re.fullmatch(r"sha256:[a-f0-9]{64}", image_id)), "Invalid image identity")
    require(metadata.get("Os") == "linux" and metadata.get("Architecture") == "amd64", "Linux amd64 required")
    require(bool(re.fullmatch(r"(?:[^\s]+@)?sha256:[a-f0-9]{64}", reference)), "Immutable image reference required")
    if reference.startswith("sha256:"):
        require(reference == image_id, "Runtime image mismatch")
    if artifact:
        require(artifact.get("Id") == image_id and artifact.get("revision") == commit,
                "Runtime artifact mismatch")
        labels = metadata.get("Config", {}).get("Labels") or {}
        require(labels.get("org.opencontainers.image.revision") == commit, "Image revision mismatch")
    else:
        require(reference in metadata.get("RepoDigests", []) or
                any(value.rsplit("@", 1)[-1] == reference.rsplit("@", 1)[-1]
                    for value in metadata.get("RepoDigests", [])), "Vendor manifest mismatch")
    layers = metadata.get("RootFS", {}).get("Layers", [])
    require(bool(layers), "Image layer metadata required")
    # Never persist unrestricted Docker Config/Env or runtime inspection.
    return {key: metadata.get(key) for key in
            ("Id", "RepoDigests", "Size", "Os", "Architecture", "Created", "RootFS")}


def validate_sbom(sbom, image):
    source = sbom.get("source", {})
    metadata = source.get("metadata", {})
    require(source.get("type") == "image" and metadata.get("imageID") == image["Id"],
            "SBOM image mismatch")
    require(metadata.get("os") == "linux" and metadata.get("architecture") == "amd64",
            "SBOM platform mismatch")
    require(bool(metadata.get("layers")) and bool(sbom.get("artifacts")), "Complete image SBOM required")
    require(sbom.get("descriptor", {}).get("name") == "syft", "Syft SBOM required")


def summarize_matches(report, sbom, image, sbom_path):
    require(not report.get("ignoredMatches"), "Ignored vulnerability matches are forbidden")
    source = report.get("source", {})
    # Grype preserves Syft's image source; older serializers may use the SBOM
    # filename instead. In either case it must identify this exact input.
    valid_source = (source.get("type") == "image" and
                    isinstance(source.get("target"), dict) and
                    source["target"].get("imageID") == image["Id"])
    valid_source |= source.get("type") == "sbom-file" and source.get("target") == str(sbom_path)
    require(valid_source, "Grype source mismatch")
    packages = {item["id"]: item for item in sbom["artifacts"]}
    records = []
    for match in report.get("matches", []):
        vulnerability = match["vulnerability"]
        package = match["artifact"]
        cataloged = packages.get(package.get("id"))
        require(cataloged is not None and cataloged["name"] == package["name"] and
                cataloged["version"] == package["version"], "Matched package absent from SBOM")
        records.append({"id": vulnerability["id"], "severity": vulnerability["severity"],
                        "package": package["name"], "installed": package["version"],
                        "package_type": package.get("type"), "package_id": package["id"],
                        "purl": cataloged.get("purl"),
                        "locations": [item["path"] for item in cataloged.get("locations", [])],
                        "location_provenance": cataloged.get("locations", []),
                        "package_metadata": cataloged.get("metadata"),
                        "fix": vulnerability.get("fix"), "source": vulnerability.get("dataSource"),
                        "namespace": vulnerability.get("namespace"),
                        "match_details": match.get("matchDetails", []),
                        "related_vulnerabilities": match.get("relatedVulnerabilities", [])})
    return records


def write_evidence(path, value):
    payload = (json.dumps(value, indent=2) + "\n").encode()
    path.write_bytes(payload)
    return {"path": path.relative_to(WORK).as_posix(), "sha256": hashlib.sha256(payload).hexdigest(),
            "bytes": len(payload)}


def gate(records):
    return "FAIL" if any(item["severity"] in ("High", "Critical") for item in records) else "PASS"


def main():
    require(os.getenv("GITHUB_ACTIONS") == "true" and os.getenv("RUNNER_ENVIRONMENT") == "github-hosted"
            and sys.platform == "linux", "Disposable hosted Linux runner required")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", required=True, type=Path)
    args = parser.parse_args()
    result = json.loads(args.result.read_text())
    commit = result.get("commit", "")
    require(result.get("production") is False and result.get("status") == "PASS" and
            bool(re.fullmatch(r"[a-f0-9]{40}", commit)) and commit == os.getenv("GITHUB_SHA"),
            "Matching successful disposable runtime evidence required")
    evidence_dir = WORK / "security"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    isolated_home = WORK / "scanner-home"
    isolated_home.mkdir(exist_ok=True)
    # Explicit empty config and clean HOME prevent local ignore files or implicit
    # scanner configuration from altering the result. No caller scanner variables.
    config = WORK / "scanner-empty.yaml"
    config.write_text("{}\n")
    env = {key: value for key, value in os.environ.items() if key in ("PATH", "LANG")}
    env.update(HOME=str(isolated_home), GRYPE_CHECK_FOR_APP_UPDATE="false",
               SYFT_CHECK_FOR_APP_UPDATE="false", GRYPE_DB_CACHE_DIR=str(WORK / "grype-db"))
    syft = install_tool("syft", SYFT_VERSION, SYFT_SHA256)
    grype = install_tool("grype", VERSION, ARCHIVE_SHA256)
    findings = []
    for name in NAMES:
        reference = result["images"]["REHEARSAL_" + name + "_IMAGE"]
        metadata = json_command(["docker", "image", "inspect", "--format", "{{json .}}", reference], env)
        image = image_identity(metadata, reference, result.get("artifacts", {}).get(name.lower()), commit)
        sbom = json_command([str(syft), "scan", "docker:" + image["Id"], "--config", str(config),
                             "--scope", "squashed", "-o", "syft-json"], env)
        sbom_path = evidence_dir / (name.lower() + ".syft.json")
        files = {"sbom": write_evidence(sbom_path, sbom)}
        # Retain diagnostic evidence if schema/identity validation fails; no
        # successful summary is emitted until every identity check passes.
        validate_sbom(sbom, image)
        report = json_command([str(grype), "sbom:" + str(sbom_path), "--config", str(config), "-o", "json"], env)
        files["grype"] = write_evidence(evidence_dir / (name.lower() + ".grype.json"), report)
        records = summarize_matches(report, sbom, image, sbom_path)
        files["provenance"] = write_evidence(evidence_dir / (name.lower() + ".provenance.json"),
            {"commit": commit, "image": image, "reference": reference,
             "distribution": sbom.get("distro"), "source": sbom["source"],
             "package_count": len(sbom["artifacts"]), "matches": records})
        counts = dict(Counter(item["severity"] for item in records))
        findings.append({"image": name, "reference": reference, "identity": image,
                         "distribution": sbom.get("distro"), "package_count": len(sbom["artifacts"]),
                         "counts": counts, "matches": records, "files": files,
                         "database": report.get("descriptor", {}).get("db", {})})
        print(name + ": " + str(len(records)) + " unsuppressed vulnerability matches; " +
              str(counts.get("High", 0)) + " High, " + str(counts.get("Critical", 0)) + " Critical", flush=True)
        # Keep one database snapshot throughout the five-image campaign.
        env["GRYPE_DB_AUTO_UPDATE"] = "false"
    status = gate([record for item in findings for record in item["matches"]])
    write_evidence(WORK / "image-security.json", {"commit": commit, "scanner": "grype " + VERSION,
        "scanner_archive_sha256": ARCHIVE_SHA256, "cataloger": "syft " + SYFT_VERSION,
        "cataloger_archive_sha256": SYFT_SHA256, "status": status, "scope": "squashed",
        "production": False, "images": findings})
    return int(status != "PASS")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        # RuntimeError labels are fixed strings produced by require(), never
        # subprocess stderr, configuration values or remote response bodies.
        detail = str(error) if type(error) is RuntimeError else type(error).__name__
        print("BLOCKED image security scan: " + detail + "; no configuration/output bodies emitted")
        raise SystemExit(1)
