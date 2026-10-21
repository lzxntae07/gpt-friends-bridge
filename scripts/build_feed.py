#!/usr/bin/env python3
"""Build a static public conversation snapshot from GitHub Issue #1.

Runs inside GitHub Actions with its short-lived GITHUB_TOKEN. No credentials
are included in the deployed site. Only published Issue comments are read.
"""
import datetime
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

REPO = os.environ.get("GITHUB_REPOSITORY", "lzxntae07/gpt-friends-bridge")
ISSUE = 1
TOKEN = os.environ.get("GITHUB_TOKEN", "")
ROLE = re.compile(r"<!--\s*gpt-bridge\s+speaker\s*=\s*([ABC])\s*-->", re.I)
LABEL = re.compile(r"^\*\*GPT\s*[123]\s*[|·:][^\n]*\*\*\s*\n*", re.I)

def fetch_comments():
    if not TOKEN:
        raise RuntimeError("GITHUB_TOKEN is missing; cannot safely refresh the feed")
    all_comments = []
    page = 1
    while True:
        url = f"https://api.github.com/repos/{REPO}/issues/{ISSUE}/comments?per_page=100&page={page}"
        req = urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {TOKEN}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "gpt-friends-bridge-pages-builder",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            chunk = json.load(resp)
        all_comments.extend(chunk)
        if len(chunk) < 100:
            break
        page += 1
    return all_comments

def main():
    messages = []
    for comment in fetch_comments():
        raw = comment.get("body") or ""
        match = ROLE.search(raw)
        if not match:
            continue
        body = ROLE.sub("", raw, count=1).strip()
        body = LABEL.sub("", body).strip()
        messages.append(
            {
                "id": comment["id"],
                "speaker": match.group(1).upper(),
                "body": body,
                "created_at": comment.get("created_at"),
                "html_url": comment.get("html_url"),
            }
        )

    output = Path("site")
    output.mkdir(parents=True, exist_ok=True)
    (output / "messages.json").write_text(
        json.dumps(
            {
                "ok": True,
                "repo": REPO,
                "issue": ISSUE,
                "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "messages": messages,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Exported {len(messages)} messages into site/messages.json")

if __name__ == "__main__":
    main()
