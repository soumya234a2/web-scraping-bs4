# Web Scraping using BS4 Library

B.Tech final-year project (Computer Science and Engineering).
A Python scraper built with **requests** and **BeautifulSoup (bs4)** that collects
question and post listings from **Stack Overflow**, **Reddit**, **Hacker News** and
**quotes.toscrape.com** and saves them as structured **CSV / JSON** files for analysis.

## What it does

- Scrapes Stack Overflow questions by tag: title, link, author, votes, answers, views, tags, excerpt
- Scrapes Reddit posts from a subreddit: title, link, author, score, comment count, subreddit, timestamp
- Scrapes Hacker News front-page stories: title, link, author, points, comment count
- Scrapes quotes.toscrape.com (a site built for scraping practice): quote, author, tags
- Follows pagination across multiple pages
- Skips Reddit ads, handles failed requests, and waits between requests to stay polite
- Exports results to CSV (and JSON with `--json`)
- Includes offline unit tests for the HTML parsers

## Tech stack

Python, requests, BeautifulSoup4 (html.parser), csv, json, argparse, unittest

## Run it locally

```
git clone https://github.com/soumya234a2/web-scraping-bs4.git
cd web-scraping-bs4
python -m venv venv
venv\Scripts\activate          # Windows   (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
```

Examples:

```
python scraper.py stackoverflow --tag python --pages 2
python scraper.py reddit --subreddit learnpython --pages 2
python scraper.py hackernews --pages 2
python scraper.py quotes --pages 3
python scraper.py both --tag flask --subreddit flask --json
```

Hacker News and quotes.toscrape.com allow scraping and work reliably. Stack Overflow
and Reddit block many automated requests (HTTP 403 or empty pages), so they may
return no data depending on your network.

Results are saved in the `output/` folder with a timestamp in the file name.

## Run the tests

```
python -m unittest discover tests
```

The tests use small HTML samples, so they work without internet.

## Project structure

```
scraper.py              fetching, parsing (4 sites), CSV/JSON export, CLI
tests/test_parsers.py   offline tests for the parsers
requirements.txt        dependencies
output/                 scraped files are written here
```

## How it works

1. `requests` downloads the page with a browser-like User-Agent.
2. `BeautifulSoup` parses the HTML and CSS selectors pick out each question or post.
3. Numbers like `1,234` or `1.5k` are converted to integers.
4. Rows are written to CSV/JSON.

## Notes and limitations

- Websites change their HTML. If a site updates its layout, the CSS selectors in
  `scraper.py` may need updating.
- Stack Overflow and Reddit may block automated traffic or require their official
  APIs for heavy use. Keep `--pages` small, respect each site's Terms of Service
  and robots.txt, and use this project for learning only.
- Reddit is scraped from `old.reddit.com`, whose layout is simpler to parse.

## Author

**Soumyaranjan Naik** - B.Tech Computer Science Engineering, Synergy Institute of Engineering Technology, Dhenkanal
Guide: Prof. Ipsita Panda
