"""
Web Scraping using BS4 Library
Scrapes question/post listings from Stack Overflow and Reddit using
requests + BeautifulSoup and saves them to CSV (and optionally JSON).

Usage:
    python scraper.py stackoverflow --tag python --pages 2
    python scraper.py reddit --subreddit learnpython --pages 2
    python scraper.py both --tag python --subreddit python
    python scraper.py hackernews --pages 2
    python scraper.py quotes --pages 3

Note: Stack Overflow and Reddit often block automated requests (HTTP 403 or
empty pages). Hacker News and quotes.toscrape.com allow scraping and are the
reliable sites to demo the scraper with.
"""

import argparse
import csv
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

HEADERS = {
    # Sites reject requests with no browser-like User-Agent.
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36 "
        "StudentProject-BS4Scraper/1.0"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
DELAY_SECONDS = 2          # be polite: pause between page requests
TIMEOUT_SECONDS = 15
OUTPUT_DIR = Path("output")


# ----------------------------------------------------------------- helpers
def fetch_html(url, params=None):
    """Download a page and return its HTML text, or None on failure."""
    try:
        response = requests.get(
            url, headers=HEADERS, params=params, timeout=TIMEOUT_SECONDS
        )
        response.raise_for_status()
        return response.text
    except requests.RequestException as error:
        print(f"[!] Could not fetch {url}: {error}", file=sys.stderr)
        return None


def to_int(text, default=0):
    """Turn strings like '1,234', '12k' or '3 votes' into an integer."""
    if not text:
        return default
    text = text.strip().lower().replace(",", "")
    match = re.search(r"(\d+(?:\.\d+)?)\s*([km]?)", text)
    if not match:
        return default
    number = float(match.group(1))
    number *= {"k": 1_000, "m": 1_000_000}.get(match.group(2), 1)
    return int(number)


# ----------------------------------------------------------- Stack Overflow
def parse_stackoverflow(html):
    """Extract question summaries from a Stack Overflow listing page."""
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    for item in soup.select("div.s-post-summary"):
        link = item.select_one("h3.s-post-summary--content-title a")
        if link is None:
            continue

        votes = answers = views = 0
        for stat in item.select("div.s-post-summary--stats-item"):
            number = stat.select_one(".s-post-summary--stats-item-number")
            unit = stat.select_one(".s-post-summary--stats-item-unit")
            if number is None or unit is None:
                continue
            label = unit.get_text(strip=True).lower()
            value = to_int(number.get_text())
            if label.startswith("vote"):
                votes = value
            elif label.startswith("answer"):
                answers = value
            elif label.startswith("view"):
                views = value

        excerpt = item.select_one(".s-post-summary--content-excerpt")
        author = item.select_one(".s-user-card--link a")
        tags = [t.get_text(strip=True) for t in item.select("a.post-tag")]

        rows.append({
            "source": "stackoverflow",
            "title": link.get_text(strip=True),
            "url": "https://stackoverflow.com" + link.get("href", ""),
            "author": author.get_text(strip=True) if author else "",
            "votes": votes,
            "answers": answers,
            "views": views,
            "tags": ";".join(tags),
            "excerpt": excerpt.get_text(" ", strip=True) if excerpt else "",
        })
    return rows


def scrape_stackoverflow(tag, pages):
    rows = []
    for page in range(1, pages + 1):
        url = f"https://stackoverflow.com/questions/tagged/{tag}"
        html = fetch_html(url, params={"tab": "newest", "page": page,
                                       "pagesize": 15})
        if html is None:
            break
        page_rows = parse_stackoverflow(html)
        print(f"Stack Overflow page {page}: {len(page_rows)} questions")
        if not page_rows:
            break
        rows.extend(page_rows)
        time.sleep(DELAY_SECONDS)
    return rows


# ------------------------------------------------------------------- Reddit
def parse_reddit(html):
    """Extract posts from an old.reddit.com listing page."""
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    for post in soup.select("div.thing[data-fullname]"):
        if "promoted" in post.get("class", []):
            continue                      # skip ads
        title = post.select_one("a.title")
        if title is None:
            continue

        href = title.get("href", "")
        if href.startswith("/"):
            href = "https://old.reddit.com" + href

        score = post.select_one("div.score.unvoted")
        comments = post.select_one("a.comments")
        author = post.select_one("a.author")
        time_tag = post.select_one("time")
        subreddit = post.get("data-subreddit", "")

        rows.append({
            "source": "reddit",
            "title": title.get_text(strip=True),
            "url": href,
            "author": author.get_text(strip=True) if author else "",
            "votes": to_int(score.get("title") if score and score.get("title")
                            else (score.get_text() if score else "")),
            "answers": to_int(comments.get_text()) if comments else 0,
            "views": 0,                   # Reddit does not expose view counts
            "tags": subreddit,
            "excerpt": time_tag.get("datetime", "") if time_tag else "",
        })
    return rows


def scrape_reddit(subreddit, pages):
    rows = []
    url = f"https://old.reddit.com/r/{subreddit}/"
    for page in range(1, pages + 1):
        html = fetch_html(url)
        if html is None:
            break
        page_rows = parse_reddit(html)
        print(f"Reddit page {page}: {len(page_rows)} posts")
        if not page_rows:
            break
        rows.extend(page_rows)

        # old.reddit has a "next" button that carries the pagination link
        next_link = BeautifulSoup(html, "html.parser").select_one(
            "span.next-button a")
        if next_link is None:
            break
        url = next_link.get("href")
        time.sleep(DELAY_SECONDS)
    return rows



# -------------------------------------------------------------- Hacker News
def parse_hackernews(html):
    """Extract stories from a news.ycombinator.com listing page."""
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    for story in soup.select("tr.athing"):
        link = story.select_one("span.titleline > a")
        if link is None:
            continue
        href = link.get("href", "")
        if not href.startswith("http"):
            href = "https://news.ycombinator.com/" + href

        # points / author / comments live in the row right after the title
        meta = story.find_next_sibling("tr")
        score = meta.select_one("span.score") if meta else None
        author = meta.select_one("a.hnuser") if meta else None
        comments = 0
        if meta:
            for a in meta.select("td.subtext a"):
                if "comment" in a.get_text():
                    comments = to_int(a.get_text())

        rows.append({
            "source": "hackernews",
            "title": link.get_text(strip=True),
            "url": href,
            "author": author.get_text(strip=True) if author else "",
            "votes": to_int(score.get_text()) if score else 0,
            "answers": comments,
            "views": 0,
            "tags": "",
            "excerpt": "",
        })
    return rows


def scrape_hackernews(pages):
    rows = []
    for page in range(1, pages + 1):
        html = fetch_html("https://news.ycombinator.com/news", params={"p": page})
        if html is None:
            break
        page_rows = parse_hackernews(html)
        print(f"Hacker News page {page}: {len(page_rows)} stories")
        if not page_rows:
            break
        rows.extend(page_rows)
        time.sleep(DELAY_SECONDS)
    return rows


# ------------------------------------------------------ quotes.toscrape.com
def parse_quotes(html):
    """Extract quotes from quotes.toscrape.com (a site made for practice)."""
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    for box in soup.select("div.quote"):
        text = box.select_one("span.text")
        if text is None:
            continue
        author = box.select_one("small.author")
        tags = [t.get_text(strip=True) for t in box.select("a.tag")]
        about = box.select_one("a[href^='/author/']")
        rows.append({
            "source": "quotes.toscrape",
            "title": text.get_text(strip=True).strip("\u201c\u201d\""),
            "url": ("http://quotes.toscrape.com" + about.get("href", ""))
                   if about else "",
            "author": author.get_text(strip=True) if author else "",
            "votes": 0,
            "answers": 0,
            "views": 0,
            "tags": ";".join(tags),
            "excerpt": "",
        })
    return rows


def scrape_quotes(pages):
    rows = []
    url = "http://quotes.toscrape.com/"
    for page in range(1, pages + 1):
        html = fetch_html(url)
        if html is None:
            break
        page_rows = parse_quotes(html)
        print(f"Quotes page {page}: {len(page_rows)} quotes")
        if not page_rows:
            break
        rows.extend(page_rows)
        next_link = BeautifulSoup(html, "html.parser").select_one("li.next a")
        if next_link is None:
            break
        url = "http://quotes.toscrape.com" + next_link.get("href", "")
        time.sleep(DELAY_SECONDS)
    return rows


# ------------------------------------------------------------------ output
FIELDS = ["source", "title", "url", "author", "votes", "answers",
          "views", "tags", "excerpt"]


def save_csv(rows, path):
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def save_json(rows, path):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(rows, handle, indent=2, ensure_ascii=False)


# --------------------------------------------------------------------- CLI
def build_parser():
    parser = argparse.ArgumentParser(
        description="Scrape Stack Overflow and Reddit using BeautifulSoup.")
    parser.add_argument("site", choices=["stackoverflow", "reddit", "both", "hackernews",
                                  "quotes"])
    parser.add_argument("--tag", default="python",
                        help="Stack Overflow tag (default: python)")
    parser.add_argument("--subreddit", default="learnpython",
                        help="Subreddit name (default: learnpython)")
    parser.add_argument("--pages", type=int, default=1,
                        help="Number of pages to scrape (default: 1)")
    parser.add_argument("--json", action="store_true",
                        help="Also save the results as JSON")
    return parser


def main():
    args = build_parser().parse_args()
    rows = []
    if args.site in ("stackoverflow", "both"):
        rows += scrape_stackoverflow(args.tag, args.pages)
    if args.site in ("reddit", "both"):
        rows += scrape_reddit(args.subreddit, args.pages)
    if args.site == "hackernews":
        rows += scrape_hackernews(args.pages)
    if args.site == "quotes":
        rows += scrape_quotes(args.pages)

    if not rows:
        print("No data collected. The site may be blocking requests or its "
              "page layout may have changed.")
        if args.site in ("stackoverflow", "reddit", "both"):
            print("Tip: Stack Overflow and Reddit block most scrapers. Try "
                  "'python scraper.py hackernews' or "
                  "'python scraper.py quotes' instead.")
        sys.exit(1)

    OUTPUT_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = OUTPUT_DIR / f"{args.site}_{stamp}.csv"
    save_csv(rows, csv_path)
    print(f"Saved {len(rows)} rows to {csv_path}")
    if args.json:
        json_path = csv_path.with_suffix(".json")
        save_json(rows, json_path)
        print(f"Saved JSON to {json_path}")


if __name__ == "__main__":
    main()
