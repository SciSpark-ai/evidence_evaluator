"""PubMed E-utilities efetch with retry + on-disk cache.

Fetches a single PMID's XML record (db=pubmed, retmode=xml). Caches to disk;
returns cached content on hit. Retries 5xx with exponential backoff (1s, 4s, 16s).
4xx responses raise PubMedError immediately.

Set NCBI_API_KEY env var to raise rate limit from 3 to 10 req/s (default throttle
is 0.34s between calls).
"""

import os
import time
from typing import Optional

import requests


EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
DEFAULT_THROTTLE_S = 0.34  # ~3 req/s without API key
WITH_KEY_THROTTLE_S = 0.10  # ~10 req/s with API key
DEFAULT_MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 4  # 1s, 4s, 16s


class PubMedError(Exception):
    """Raised on unrecoverable PubMed efetch errors (4xx or final 5xx retry)."""


def fetch_abstract(
    pmid: str,
    cache_dir: str,
    throttle: Optional[float] = None,
    max_retries: int = DEFAULT_MAX_RETRIES,
    api_key: Optional[str] = None,
) -> str:
    """Fetch a PubMed record's XML for the given pmid, with caching.

    Args:
        pmid: PubMed ID as string
        cache_dir: directory to cache responses (created if missing)
        throttle: seconds to sleep before request; default 0.34s (or 0.10s if API key)
        max_retries: number of retry attempts on 5xx errors (default 3)
        api_key: NCBI_API_KEY override; falls back to env var

    Returns:
        The XML string content (cached or freshly fetched).

    Raises:
        PubMedError on 4xx or after exhausting retries on 5xx.
    """
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, f"{pmid}.xml")
    if os.path.exists(cache_path):
        with open(cache_path) as f:
            return f.read()

    key = api_key or os.environ.get("NCBI_API_KEY")
    if throttle is None:
        throttle = WITH_KEY_THROTTLE_S if key else DEFAULT_THROTTLE_S

    params = {"db": "pubmed", "id": pmid, "retmode": "xml"}
    if key:
        params["api_key"] = key

    last_err: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        if throttle > 0:
            time.sleep(throttle)
        try:
            resp = requests.get(EFETCH_URL, params=params, timeout=30)
            if 400 <= resp.status_code < 500:
                raise PubMedError(
                    f"PubMed efetch returned {resp.status_code} for pmid={pmid}: invalid pmid?"
                )
            resp.raise_for_status()
            content = resp.text
            with open(cache_path, "w") as f:
                f.write(content)
            return content
        except PubMedError:
            raise
        except (requests.HTTPError, requests.RequestException) as e:
            last_err = e
            if attempt < max_retries:
                backoff = RETRY_BACKOFF_BASE ** attempt  # 1, 4, 16
                time.sleep(backoff)
            else:
                raise PubMedError(
                    f"PubMed efetch failed for pmid={pmid} after {max_retries} retries: {e}"
                ) from e
    # Defensive: unreachable
    raise PubMedError(f"Unexpected end of retry loop for pmid={pmid}: {last_err}")
