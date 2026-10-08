#!/usr/bin/env python3
"""Read-only GitHub/HF tree and live deployment check (standard library only).

Fetch the remotes first. Compare committed blobs, never working-directory files.
LFS pointer identities normalize to SHA-256 and size; modes remain significant.
This verifies repository identity, not availability of every remote LFS object.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import urllib.request


LFS_POINTER = re.compile(
    rb"version https://git-lfs.github.com/spec/v1\n"
    rb"oid sha256:([0-9a-f]{64})\nsize (0|[1-9][0-9]*)\n?"
)


def git(repo, *args):
    return subprocess.check_output(
        ["git", "-C", str(repo), *args], stderr=subprocess.PIPE, timeout=60,
    )


def manifest(repo, sha):
    """Map exact paths to mode, content SHA-256 and byte size."""
    entries = {}
    for record in git(repo, "ls-tree", "-rz", "--full-tree", sha).split(b"\0"):
        if not record:
            continue
        metadata, raw_path = record.split(b"\t", 1)
        mode, kind, oid = metadata.split()
        path = raw_path.decode("utf-8", "surrogateescape")
        if path == ".gitattributes":
            continue
        if kind != b"blob":
            raise ValueError(f"Entrée Git non prise en charge : {path}")
        content = git(repo, "cat-file", "blob", oid.decode())
        pointer = LFS_POINTER.fullmatch(content) if mode != b"120000" else None
        if pointer:
            digest, size = pointer.group(1).decode(), int(pointer.group(2))
        else:
            if content.startswith(b"version https://git-lfs.github.com/spec/"):
                raise ValueError(f"Pointeur LFS non pris en charge : {path}")
            digest, size = hashlib.sha256(content).hexdigest(), len(content)
        entries[path] = (mode.decode(), digest, size)
    return entries


def fetch_json(url, timeout):
    request = urllib.request.Request(url, headers={"User-Agent": "DakiKobo-deployment-check/1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.load(response)
    if not isinstance(payload, dict):
        raise ValueError("Réponse JSON attendue : objet")
    return payload


def verify(args):
    report = {"github_sha": None, "hf_sha": None, "live_sha": None,
              "differing_paths": [], "manifest_match": False,
              "live_verified": False, "result": "FAIL"}
    try:
        github = git(args.repo, "rev-parse", "--verify", "--end-of-options",
                     args.github_ref + "^{commit}").decode().strip()
        hf = git(args.repo, "rev-parse", "--verify", "--end-of-options",
                 args.hf_ref + "^{commit}").decode().strip()
        report.update(github_sha=github, hf_sha=hf)
        left, right = manifest(args.repo, github), manifest(args.repo, hf)
        report["differing_paths"] = sorted(
            path for path in left.keys() | right.keys() if left.get(path) != right.get(path)
        )
        report["manifest_match"] = not report["differing_paths"]
        report["deployment_message_match"] = (
            git(args.repo, "log", "-1", "--format=%s", hf).decode().strip()
            == f"Deploy GitHub main {github} to Space"
        )
        if not args.dry_run:
            version = fetch_json(args.base_url.rstrip("/") + "/version", args.timeout)
            report["live_sha"] = version.get("commit")
            health = fetch_json(args.base_url.rstrip("/") + "/healthz", args.timeout)
            report["live_verified"] = (
                report["live_sha"] == hf and version.get("rag_status") == "ready"
                and health.get("ok") is True and health.get("rag_ready") is True
                and health.get("rag_status") == "ready"
            )
        if (report["manifest_match"] and report["deployment_message_match"]
                and (args.dry_run or report["live_verified"])):
            report["result"] = "PASS (dry run only)" if args.dry_run else "PASS"
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        report["error"] = str(exc)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--github-ref", default="origin/main")
    parser.add_argument("--hf-ref", default="hf/main")
    parser.add_argument("--base-url", default="https://kimcomehome-dakikobo.hf.space")
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument("--dry-run", action="store_true", help="Comparer les arbres sans accès HTTP.")
    args = parser.parse_args()
    report = verify(args)
    print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0 if report["result"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
