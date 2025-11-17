#!/usr/bin/env python3
"""
Create ONE installer markdown card from a GitHub release.

Env:
  ORG            default: ManiVaultStudio
  REPO           default: Releases
  GITHUB_TOKEN   token for REST (PAT, GITHUB_TOKEN, or App token)
  RELEASE_TAG    exact tag to fetch; if unset -> latest release
  DEST_DIR       where to write the md file in the checked-out website repo (default: _installers)

Filename rule (from tag only):
  <version>_<os_slug>.md
Examples:
  ManiVault-1.3.0-Ubuntu-24      -> 1.3.0_ubuntu_24.md
  ManiVault-1.1.0-Ubuntu-22      -> 1.1.0_ubuntu_22.md
  ManiVault_1.3_online_Windows   -> 1.3.0_windows.md
"""

import os
import re
from datetime import datetime, timezone

import requests

ORG = os.getenv("ORG", "ManiVaultStudio")
REPO = os.getenv("REPO", "Releases")
DEST_DIR = os.getenv("DEST_DIR", "_installers")

_tok = os.getenv("GITHUB_TOKEN")
HDR = {
    "Accept": "application/vnd.github+json",
    **({"Authorization": f"Bearer {_tok}"} if _tok else {}),
}


def get_release(tag: str | None) -> dict:
    base = f"https://api.github.com/repos/{ORG}/{REPO}/releases"
    url = f"{base}/tags/{tag}" if tag else f"{base}/latest"
    r = requests.get(url, headers=HDR, timeout=30)
    r.raise_for_status()
    return r.json()


# -------- version + os slug (for filename) from Release Tag --------
def version_from_tag(tag: str) -> str:
    # accept 1.3 or 1.3.0; normalize to x.y.z
    m = re.search(r"(\d+\.\d+(?:\.\d+)?)", tag)
    if not m:
        return "0.0.0"
    v = m.group(1)
    return v if v.count(".") == 2 else v + ".0"


def os_slug_from_tag(tag: str) -> str:
    t = tag.lower()
    if re.search(r"ubuntu[-_\s]?24", t):
        return "ubuntu_24"
    if re.search(r"ubuntu[-_\s]?22", t):
        return "ubuntu_22"
    if "windows" in t:
        return "windows"
    if "macos" in t or "mac" in t:
        return "macos"
    if "linux" in t:
        return "linux"
    return "windows"
# -------------------------------------------------------------


def infer_os_for_frontmatter(tag: str, asset_name: str) -> str:
    hay = f"{tag.lower()} {asset_name.lower()}"
    if "windows" in hay or asset_name.lower().endswith((".exe", ".msi")):
        return "windows"
    if "macos" in hay or "mac" in hay or asset_name.lower().endswith((".dmg", ".pkg")):
        return "mac"
    if "linux" in hay or "ubuntu" in hay or asset_name.lower().endswith(
        (".appimage", ".deb", ".tar.gz", ".tgz")
    ):
        return "linux"
    return "windows"


def os_meta(os_key: str):
    table = {
        "windows": ("Windows", "Windows", "Windows 10, 11", "windows", 1, "windows"),
        "mac": ("macOS", "macOS", "macOS 12+ (Apple & Intel)", "mac", 2, "apple"),
        "linux": ("Linux", "Linux", "Ubuntu 22.04+", "linux", 3, "linux"),
    }
    return table[os_key]


def fmt_date(iso: str) -> str:
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def size_mb(nbytes: int) -> str:
    return f"{round((nbytes or 0) / 1024 / 1024)} MB"


def render_md(
    name, short, compat, key, order, icon, version, date_str, size_str, url
) -> str:
    return f"""---
layout: plugin
name: "{name}"
shortname: "{short}"
compatibility: "{compat}"
key: {key}
type: installer
image: 
version: {version}
date:   {date_str}
order: {order}
icon: {icon}
size: {size_str}

organization: ManiVault
organization-link: https://www.manivault.studio
download-link: {url}
---
{version} release of ManiVault Studio.
"""


def main() -> None:
    rel = get_release(os.getenv("RELEASE_TAG"))
    assets = rel.get("assets") or []
    if not assets:
        raise SystemExit("Release has no assets; cannot create installer card.")

    a0 = assets[0]
    aname = a0.get("name", "")
    tag = rel.get("tag_name", "")

    # filename parts from tag
    version_for_filename = version_from_tag(tag)
    os_slug = os_slug_from_tag(tag)

    # front-matter OS (robust via tag+asset)
    os_key = infer_os_for_frontmatter(tag, aname)
    name, short, compat, key, order, icon = os_meta(os_key)

    date_str = fmt_date(rel.get("published_at") or rel.get("created_at"))
    size_str = size_mb(a0.get("size", 0))
    url = a0.get("browser_download_url")

    md = render_md(
        name, short, compat, key, order, icon, version_for_filename, date_str, size_str, url
    )

    os.makedirs(DEST_DIR, exist_ok=True)
    fname = f"{version_for_filename}_{os_slug}.md"
    path = os.path.join(DEST_DIR, fname)
    with open(path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"Generated: {path}")


if __name__ == "__main__":
    main()
