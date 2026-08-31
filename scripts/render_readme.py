#!/usr/bin/env python3
"""Render profile/README.md from README.tpl.md + the live blog.

{{LATEST_POSTS}} — the three newest editorial posts, in the order the live
/blog listing shows them (it is date-sorted); titles and excerpts come from
the public search index. {{UPDATED}} — today's date. Any fetch failure keeps
the previous rendered section so a flaky network can never blank the page.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from datetime import date, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TPL = ROOT / "profile" / "README.tpl.md"
OUT = ROOT / "profile" / "README.md"
BLOG = "https://hyperdrift.io/blog"
INDEX = "https://hyperdrift.io/api/search-index"
UA = {"User-Agent": "hyperdrift-profile-renderer"}


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", "replace")


def latest_posts(n: int = 3) -> list[dict]:
    listing = fetch(BLOG)
    slugs: list[str] = []
    for slug in re.findall(r'href="/blog/([a-z0-9-]+)"', listing):
        if slug.startswith(("tag", "page", "daily-intel")) or slug in slugs:
            continue
        slugs.append(slug)
        if len(slugs) == n:
            break
    index = {p["slug"]: p for p in json.loads(fetch(INDEX))}
    posts = []
    for slug in slugs:
        p = index.get(slug)
        if p:
            posts.append({"slug": slug, "title": p["title"], "excerpt": p["excerpt"]})
    return posts


def render_posts(posts: list[dict]) -> str:
    lines = []
    for p in posts:
        lines.append(f"**[{p['title']}](https://hyperdrift.io/blog/{p['slug']})**  ")
        lines.append(f"{p['excerpt']}")
        lines.append("")
    return "\n".join(lines).strip()


def main() -> int:
    tpl = TPL.read_text(encoding="utf-8")
    try:
        posts_md = render_posts(latest_posts())
        if not posts_md:
            raise RuntimeError("no posts extracted")
    except Exception as exc:  # noqa: BLE001 — keep the previous section on any failure
        prev = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        m = re.search(r"## Fresh from the blog\n\n(.*?)\n\nMore:", prev, re.S)
        if not m:
            print(f"fetch failed and no previous section to keep: {exc}", file=sys.stderr)
            return 1
        posts_md = m.group(1).strip()
        print(f"fetch failed, kept previous blog section: {exc}", file=sys.stderr)
    out = tpl.replace("{{LATEST_POSTS}}", posts_md)
    out = out.replace("{{UPDATED}}", date.today().strftime("%-d %b %Y"))
    OUT.write_text(out, encoding="utf-8")
    print(f"rendered {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
