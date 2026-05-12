"""Tests for eval/trec_pm2020/pubmed.py"""

import os
import sys
import tempfile
import shutil
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from eval.trec_pm2020.pubmed import fetch_abstract, PubMedError

PASS = 0
FAIL = 0


def check(name, got, expected):
    global PASS, FAIL
    if got == expected:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}: got {got!r}, expected {expected!r}")


def test_returns_cached_content_without_network():
    tmpdir = tempfile.mkdtemp()
    try:
        pmid = "12345"
        cache_path = os.path.join(tmpdir, f"{pmid}.xml")
        with open(cache_path, "w") as f:
            f.write("<PubmedArticle>cached</PubmedArticle>")

        with patch("eval.trec_pm2020.pubmed.requests.get") as mock_get:
            content = fetch_abstract(pmid, cache_dir=tmpdir)
            check("returns cached content", content, "<PubmedArticle>cached</PubmedArticle>")
            check("network not called", mock_get.called, False)
    finally:
        shutil.rmtree(tmpdir)


def test_fetches_and_caches_on_miss():
    tmpdir = tempfile.mkdtemp()
    try:
        pmid = "99999"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<PubmedArticle>fetched</PubmedArticle>"
        mock_response.raise_for_status = MagicMock()

        with patch("eval.trec_pm2020.pubmed.requests.get", return_value=mock_response) as mock_get:
            content = fetch_abstract(pmid, cache_dir=tmpdir, throttle=0.0)
            check("returns fetched content", content, "<PubmedArticle>fetched</PubmedArticle>")
            check("network called once", mock_get.call_count, 1)
            check("cached to disk", os.path.exists(os.path.join(tmpdir, f"{pmid}.xml")), True)
    finally:
        shutil.rmtree(tmpdir)


def test_retries_on_5xx_then_succeeds():
    tmpdir = tempfile.mkdtemp()
    try:
        pmid = "77777"
        fail_resp = MagicMock(status_code=503)
        import requests
        fail_resp.raise_for_status = MagicMock(side_effect=requests.HTTPError("503"))
        ok_resp = MagicMock(status_code=200)
        ok_resp.text = "<PubmedArticle>ok</PubmedArticle>"
        ok_resp.raise_for_status = MagicMock()

        with patch("eval.trec_pm2020.pubmed.requests.get",
                   side_effect=[fail_resp, fail_resp, ok_resp]):
            with patch("eval.trec_pm2020.pubmed.time.sleep"):
                content = fetch_abstract(pmid, cache_dir=tmpdir, throttle=0.0, max_retries=3)
                check("succeeds after retry", content, "<PubmedArticle>ok</PubmedArticle>")
    finally:
        shutil.rmtree(tmpdir)


def test_raises_on_4xx_invalid_pmid():
    tmpdir = tempfile.mkdtemp()
    try:
        pmid = "00000"
        resp = MagicMock(status_code=400)
        import requests
        resp.raise_for_status = MagicMock(side_effect=requests.HTTPError("400 invalid"))

        with patch("eval.trec_pm2020.pubmed.requests.get", return_value=resp):
            try:
                fetch_abstract(pmid, cache_dir=tmpdir, throttle=0.0)
                check("raises PubMedError", False, True)
            except PubMedError as e:
                check("PubMedError raised", "400" in str(e) or "invalid" in str(e).lower(), True)
    finally:
        shutil.rmtree(tmpdir)


if __name__ == "__main__":
    for fn in [test_returns_cached_content_without_network,
               test_fetches_and_caches_on_miss,
               test_retries_on_5xx_then_succeeds,
               test_raises_on_4xx_invalid_pmid]:
        print(f"\n{fn.__name__}")
        fn()
    print(f"\n{'='*50}\nPASS: {PASS}  FAIL: {FAIL}")
    sys.exit(0 if FAIL == 0 else 1)
