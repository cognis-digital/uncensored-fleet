"""Tests for livesearch — keyless feed/search ingestion (standard library only)."""
from __future__ import annotations

import livesearch


RSS_SAMPLE = """<?xml version="1.0"?>
<rss version="2.0"><channel>
  <title>Example Feed</title>
  <item>
    <title>First &amp; foremost</title>
    <link>https://example.com/a</link>
    <pubDate>Wed, 08 Jul 2026 12:00:00 GMT</pubDate>
  </item>
  <item>
    <title>Second</title>
    <link>https://example.com/b</link>
    <pubDate>Tue, 07 Jul 2026 09:30:00 GMT</pubDate>
  </item>
</channel></rss>"""

ATOM_SAMPLE = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Atom Example</title>
  <entry>
    <title>Atom Item</title>
    <link href="https://atom.example/x"/>
    <updated>2026-07-06T10:00:00Z</updated>
  </entry>
</feed>"""


def test_google_news_rss_url_encodes_query_and_recency():
    url = livesearch.google_news_rss("iran oil", when="7d")
    assert url.startswith("https://news.google.com/rss/search?")
    assert "iran+oil" in url and "when%3A7d" in url


def test_parse_dt_rfc822():
    dt = livesearch._parse_dt("Wed, 08 Jul 2026 12:00:00 GMT")
    assert dt.year == 2026 and dt.month == 7 and dt.day == 8


def test_parse_dt_iso8601_and_z():
    dt = livesearch._parse_dt("2026-07-06T10:00:00Z")
    assert dt.tzinfo is not None and dt.year == 2026


def test_parse_dt_invalid_returns_none():
    assert livesearch._parse_dt("not a date") is None
    assert livesearch._parse_dt(None) is None


def test_tag_strips_namespace():
    class E:
        tag = "{http://www.w3.org/2005/Atom}entry"
    assert livesearch._tag(E()) == "entry"


def test_fetch_feed_parses_rss(monkeypatch):
    monkeypatch.setattr(livesearch, "_get", lambda url: RSS_SAMPLE.encode())
    items = livesearch.fetch_feed("http://x")
    assert len(items) == 2
    assert items[0]["title"] == "First & foremost"  # html-unescaped
    assert items[0]["link"] == "https://example.com/a"
    assert items[0]["published"].startswith("2026-07-08")
    assert items[0]["source"] == "Example Feed"


def test_fetch_feed_parses_atom_link_href(monkeypatch):
    monkeypatch.setattr(livesearch, "_get", lambda url: ATOM_SAMPLE.encode())
    items = livesearch.fetch_feed("http://x")
    assert items[0]["link"] == "https://atom.example/x"
    assert items[0]["title"] == "Atom Item"


def test_fetch_feed_bad_xml_returns_empty(monkeypatch):
    monkeypatch.setattr(livesearch, "_get", lambda url: b"<not xml")
    assert livesearch.fetch_feed("http://x") == []


def test_fetch_feed_respects_limit(monkeypatch):
    monkeypatch.setattr(livesearch, "_get", lambda url: RSS_SAMPLE.encode())
    assert len(livesearch.fetch_feed("http://x", limit=1)) == 1


def test_web_search_tags_query(monkeypatch):
    monkeypatch.setattr(livesearch, "_get", lambda url: RSS_SAMPLE.encode())
    items = livesearch.web_search("nuclear", when="1d")
    assert items and all(it["query"] == "nuclear" for it in items)
    assert all(it["source"] == "google-news" for it in items)


def test_ddg_search_extracts_redirect_targets(monkeypatch):
    html = ('<a rel="nofollow" class="result__a" '
            'href="/l/?uddg=https%3A%2F%2Freal.example%2Fpage">Real <b>Result</b></a>')
    monkeypatch.setattr(livesearch, "_get", lambda url: html.encode())
    out = livesearch.ddg_search("q")
    assert out[0]["link"] == "https://real.example/page"
    assert out[0]["title"] == "Real Result"
    assert out[0]["source"] == "duckduckgo"


def test_harvest_dedupes_and_sorts(monkeypatch):
    monkeypatch.setattr(livesearch, "_get", lambda url: RSS_SAMPLE.encode())
    # same feed twice -> links de-duplicated
    out = livesearch.harvest(["http://a", "http://b"], since_days=0)
    links = [it["link"] for it in out]
    assert len(links) == len(set(links)) == 2
    # newest first
    assert out[0]["published"] >= out[1]["published"]


def test_harvest_filters_by_min_year(monkeypatch):
    old = RSS_SAMPLE.replace("2026", "2019")
    monkeypatch.setattr(livesearch, "_get", lambda url: old.encode())
    out = livesearch.harvest(["http://a"], since_days=0, min_year=2026)
    assert out == []


def test_harvest_handles_query_dicts(monkeypatch):
    monkeypatch.setattr(livesearch, "_get", lambda url: RSS_SAMPLE.encode())
    out = livesearch.harvest([{"query": "sanctions", "when": "7d"}], since_days=0)
    assert out and all(it["query"] == "sanctions" for it in out)


def test_cli_json_output(monkeypatch, capsys):
    monkeypatch.setattr(livesearch, "_get", lambda url: RSS_SAMPLE.encode())
    rc = livesearch._cli(["nuclear", "--json"])
    assert rc == 0
    import json
    data = json.loads(capsys.readouterr().out)
    assert isinstance(data, list) and data[0]["title"]


def test_cli_feed_mode(monkeypatch, capsys):
    monkeypatch.setattr(livesearch, "_get", lambda url: RSS_SAMPLE.encode())
    rc = livesearch._cli(["--feed", "http://x"])
    assert rc == 0
    assert "example.com" in capsys.readouterr().out
