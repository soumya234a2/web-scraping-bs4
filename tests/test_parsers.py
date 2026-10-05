"""Offline tests: run the parsers on small HTML samples (no internet needed).

    python -m unittest discover tests
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scraper import (parse_hackernews, parse_quotes, parse_reddit,  # noqa: E402
                     parse_stackoverflow, to_int)

SO_SAMPLE = """
<div class="s-post-summary">
  <div class="s-post-summary--stats">
    <div class="s-post-summary--stats-item">
      <span class="s-post-summary--stats-item-number">5</span>
      <span class="s-post-summary--stats-item-unit">votes</span></div>
    <div class="s-post-summary--stats-item">
      <span class="s-post-summary--stats-item-number">2</span>
      <span class="s-post-summary--stats-item-unit">answers</span></div>
    <div class="s-post-summary--stats-item">
      <span class="s-post-summary--stats-item-number">1,234</span>
      <span class="s-post-summary--stats-item-unit">views</span></div>
  </div>
  <div class="s-post-summary--content">
    <h3 class="s-post-summary--content-title">
      <a href="/questions/1/how-to-read-csv">How to read a CSV file?</a></h3>
    <div class="s-post-summary--content-excerpt">I want to load data...</div>
    <a class="post-tag">python</a><a class="post-tag">csv</a>
    <div class="s-user-card--link"><a href="/users/9/amit">Amit</a></div>
  </div>
</div>
"""

REDDIT_SAMPLE = """
<div class="thing" data-fullname="t3_abc" data-subreddit="learnpython">
  <div class="score unvoted" title="1532">1.5k</div>
  <a class="title" href="/r/learnpython/comments/abc/start_here/">Start here</a>
  <a class="author">rohit</a>
  <time datetime="2026-10-01T10:00:00+00:00"></time>
  <a class="comments">48 comments</a>
</div>
<div class="thing promoted" data-fullname="t3_ad">
  <a class="title" href="https://ads.example.com">Buy now</a>
</div>
"""


HN_SAMPLE = """
<table><tr class="athing" id="1"><td class="title">
  <span class="titleline"><a href="https://example.com/post">Show HN: A tiny scraper</a></span></td></tr>
<tr><td class="subtext"><span class="score">128 points</span> by
  <a class="hnuser">pg_fan</a> <a href="item?id=1">45&nbsp;comments</a></td></tr>
<tr class="athing" id="2"><td class="title">
  <span class="titleline"><a href="item?id=2">Ask HN: Best way to learn Python?</a></span></td></tr>
<tr><td class="subtext"><a class="hnuser">learner</a> <a href="item?id=2">discuss</a></td></tr></table>
"""

QUOTES_SAMPLE = """
<div class="quote"><span class="text">\u201cThe world as we have created it.\u201d</span>
  <span>by <small class="author">Albert Einstein</small>
  <a href="/author/Albert-Einstein">(about)</a></span>
  <div class="tags"><a class="tag">change</a><a class="tag">world</a></div></div>
"""


class ParserTests(unittest.TestCase):
    def test_to_int(self):
        self.assertEqual(to_int("1,234"), 1234)
        self.assertEqual(to_int("12k"), 12000)
        self.assertEqual(to_int("48 comments"), 48)
        self.assertEqual(to_int(""), 0)

    def test_stackoverflow(self):
        rows = parse_stackoverflow(SO_SAMPLE)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["title"], "How to read a CSV file?")
        self.assertEqual(row["url"],
                         "https://stackoverflow.com/questions/1/how-to-read-csv")
        self.assertEqual((row["votes"], row["answers"], row["views"]),
                         (5, 2, 1234))
        self.assertEqual(row["tags"], "python;csv")
        self.assertEqual(row["author"], "Amit")

    def test_reddit_skips_ads(self):
        rows = parse_reddit(REDDIT_SAMPLE)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["title"], "Start here")
        self.assertEqual(row["votes"], 1532)
        self.assertEqual(row["answers"], 48)
        self.assertEqual(row["tags"], "learnpython")
        self.assertTrue(row["url"].startswith("https://old.reddit.com/r/"))

    def test_hackernews(self):
        rows = parse_hackernews(HN_SAMPLE)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["title"], "Show HN: A tiny scraper")
        self.assertEqual(rows[0]["votes"], 128)
        self.assertEqual(rows[0]["answers"], 45)
        self.assertEqual(rows[0]["author"], "pg_fan")
        self.assertEqual(rows[1]["url"], "https://news.ycombinator.com/item?id=2")
        self.assertEqual(rows[1]["votes"], 0)

    def test_quotes(self):
        rows = parse_quotes(QUOTES_SAMPLE)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["author"], "Albert Einstein")
        self.assertEqual(rows[0]["tags"], "change;world")
        self.assertEqual(rows[0]["title"], "The world as we have created it.")


if __name__ == "__main__":
    unittest.main()
