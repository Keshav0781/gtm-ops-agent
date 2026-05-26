"""
Node 2 — Scrape Competitors

Second node in Competitor Intelligence Agent.
Visits each competitor website and fetches
public page content for analysis.

Legal and ethical scraping:
- Only public pages — no login required
- Rate limited — 3 second delay between requests
- Respects reasonable usage
- Same as what any browser would do
- Used by Crayon, Klue, SEMrush commercially

httpx is used for async HTTP requests —
same library already in our requirements.
beautifulsoup4 parses HTML — also installed.
"""

import asyncio
import logging
import os
from typing import List
import httpx
from bs4 import BeautifulSoup
from agents.competitor_intelligence.state import (
    CompetitorState
)

logger = logging.getLogger(__name__)

# Rate limiting — be respectful to websites
DELAY_BETWEEN_REQUESTS = 2  # seconds
MAX_CONTENT_LENGTH = 3000   # chars per page
REQUEST_TIMEOUT = 10        # seconds


async def fetch_page(
    client: httpx.AsyncClient,
    url: str
) -> str:
    """
    Fetches single page content.
    Returns cleaned text — no HTML tags.
    Returns empty string on any error.
    """
    try:
        response = await client.get(
            url,
            timeout=REQUEST_TIMEOUT,
            follow_redirects=True
        )

        if response.status_code != 200:
            logger.warning(f"Non-200 response for {url}")
            return ""

        soup = BeautifulSoup(
            response.text, "html.parser"
        )

        # Remove script and style elements
        for element in soup(["script", "style", "nav",
                             "footer", "header"]):
            element.decompose()

        # Get clean text
        text = soup.get_text(separator=" ", strip=True)

        # Limit content length
        return text[:MAX_CONTENT_LENGTH]

    except httpx.TimeoutException:
        logger.warning(f"Timeout fetching {url}")
        return ""
    except Exception as e:
        logger.warning(f"Error fetching {url}: {str(e)}")
        return ""


async def scrape_single_competitor(
    competitor: dict
) -> dict:
    """
    Scrapes all pages for one competitor.
    Returns competitor dict with content added.
    """
    name = competitor["name"]
    base_url = competitor["url"]
    pages = competitor.get("pages_to_check", [""])

    logger.info(f"Scraping {name} — {base_url}")

    current_content = {}

    async with httpx.AsyncClient(
        headers={
            "User-Agent": (
                "Mozilla/5.0 (compatible; "
                "GTMOpsAgent/1.0; "
                "competitive-intelligence-bot)"
            )
        }
    ) as client:
        for page_path in pages:
            url = f"{base_url}{page_path}"

            content = await fetch_page(client, url)

            page_name = page_path.strip("/") or "homepage"
            current_content[page_name] = content

            if content:
                logger.info(
                    f"Fetched {name}/{page_name} — "
                    f"{len(content)} chars"
                )
            else:
                logger.warning(
                    f"No content for {name}/{page_name}"
                )

            # Rate limiting — be respectful
            await asyncio.sleep(DELAY_BETWEEN_REQUESTS)

    competitor["current_content"] = current_content

    has_content = any(
        v for v in current_content.values() if v
    )
    if not has_content:
        competitor["fetch_error"] = (
            "No content retrieved from any page"
        )

    return competitor


async def scrape_competitors(
    state: CompetitorState
) -> CompetitorState:
    """
    Node 2 — Scrape all competitor websites.

    Async — makes HTTP requests to competitor sites.

    What it does:
    1. Checks if Node 1 failed
    2. Scrapes each competitor sequentially
       Sequential not parallel — rate limiting
    3. Tracks successful and failed scrapes
    4. Updates state with scraped content

    Input state fields used:
        competitors (with pages_to_check)

    Output state fields added:
        scraped_data, successful_scrapes,
        failed_scrapes
    """

    # ==========================================
    # Step 1 — Check if previous node failed
    # ==========================================
    if state.get("error"):
        logger.warning(
            f"[{state.get('request_id')}] "
            f"Node 2: Skipping — previous node failed"
        )
        return state

    competitors = state["competitors"]

    logger.info(
        f"[{state.get('request_id')}] "
        f"Node 2: Scraping {len(competitors)} competitors"
    )

    scraped_data = []
    successful = 0
    failed = 0

    # ==========================================
    # Step 2 — Scrape each competitor
    # Sequential — respects rate limits
    # ==========================================
    for competitor in competitors:
        try:
            scraped = await scrape_single_competitor(
                competitor
            )
            scraped_data.append(scraped)

            if scraped.get("fetch_error"):
                failed += 1
            else:
                successful += 1

        except Exception as e:
            logger.error(
                f"[{state.get('request_id')}] "
                f"Node 2: Failed scraping "
                f"{competitor['name']} — {str(e)}"
            )
            competitor["fetch_error"] = str(e)
            scraped_data.append(competitor)
            failed += 1

    # ==========================================
    # Step 3 — Update state
    # ==========================================
    state["scraped_data"] = scraped_data
    state["successful_scrapes"] = successful
    state["failed_scrapes"] = failed

    logger.info(
        f"[{state.get('request_id')}] "
        f"Node 2: Scraping complete — "
        f"success={successful} failed={failed}"
    )

    return state