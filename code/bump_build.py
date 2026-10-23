#!/usr/bin/env python3
"""Stamp a fresh build marker into index.html.

Run this before every push. It rewrites the BUILD_INFO literal so the deployed
page always carries an identifier that changes per deploy, and mirrors the value
into the visible header chip and the page <title>.

    python3 code/bump_build.py            # stamp with current time
    python3 code/bump_build.py --dry-run  # show what would change
    python3 code/bump_build.py --bump patch   # also bump the semver
"""
import argparse
import datetime
import io
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, "index.html")
VERSION_FILE = os.path.join(ROOT, "code", "VERSION")

MARKER_RE = re.compile(
    r"const BUILD_INFO = \{ version: '[^']*', build: '[^']*', "
    r"commit: '[^']*', deployed: '[^']*' \};"
)


def git(*args):
    try:
        return subprocess.check_output(["git", "-c", "safe.directory=*"] + list(args),
                                       cwd=ROOT, text=True,
                                       stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def read_version():
    try:
        with io.open(VERSION_FILE, encoding="utf-8") as f:
            v = f.read().strip()
        if re.fullmatch(r"\d+\.\d+\.\d+", v):
            return v
    except OSError:
        pass
    return "5.0.0"


def bump_version(part):
    major, minor, patch = (int(x) for x in read_version().split("."))
    if part == "major":
        major, minor, patch = major + 1, 0, 0
    elif part == "minor":
        minor, patch = minor + 1, 0
    else:
        patch += 1
    v = "%d.%d.%d" % (major, minor, patch)
    os.makedirs(os.path.dirname(VERSION_FILE), exist_ok=True)
    with io.open(VERSION_FILE, "w", encoding="utf-8") as f:
        f.write(v + "\n")
    return v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--bump", choices=["major", "minor", "patch"],
                    help="also increment the semantic version")
    args = ap.parse_args()

    version = bump_version(args.bump) if args.bump else read_version()
    now = datetime.datetime.now()
    build = now.strftime("%Y%m%d-%H%M%S")
    commit = git("rev-parse", "--short", "HEAD") or "local"
    deployed = now.strftime("%Y-%m-%d %H:%M")

    with io.open(INDEX, encoding="utf-8") as f:
        html = f.read()

    if not MARKER_RE.search(html):
        print("ERROR: BUILD_INFO marker not found in index.html", file=sys.stderr)
        return 1

    new_marker = ("const BUILD_INFO = { version: 'v%s', build: '%s', "
                  "commit: '%s', deployed: '%s' };"
                  % (version, build, commit, deployed))
    html = MARKER_RE.sub(lambda _m: new_marker, html, count=1)

    html = re.sub(r"<title>Multi-API Chat Interface \(v[\d.]+\)</title>",
                  "<title>Multi-API Chat Interface (v%s)</title>" % version, html)
    html = re.sub(r'(<small id="appVersionLabel"[^>]*>)v[\d.]+(</small>)',
                  lambda m: m.group(1) + "v" + version + m.group(2), html)

    info = {"version": "v" + version, "build": build,
            "commit": commit, "deployed": deployed}
    if args.dry_run:
        print(json.dumps(info, indent=1))
        return 0

    if not os.path.exists(VERSION_FILE):
        os.makedirs(os.path.dirname(VERSION_FILE), exist_ok=True)
        with io.open(VERSION_FILE, "w", encoding="utf-8") as f:
            f.write(version + "\n")

    with io.open(INDEX, "w", encoding="utf-8") as f:
        f.write(html)
    print("stamped v%s build %s commit %s" % (version, build, commit))
    return 0


if __name__ == "__main__":
    sys.exit(main())
