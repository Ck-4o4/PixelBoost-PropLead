import asyncio
import re
import urllib.parse
from typing import AsyncGenerator, Dict, Any, List, Optional
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from database import db

# Clean up text helper
def clean_text(text: Optional[str]) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()

def extract_phone_from_text(text: str) -> Optional[str]:
    if not text:
        return None
    # Match various phone number formats including international (+XX), parentheses, dashes, spaces
    match = re.search(r"(\+?\d{1,4}[-.\s]?)?(\(?\d{2,5}\)?[-.\s]?)?\d{3,5}[-.\s]?\d{3,5}", text)
    if match:
        candidate = match.group(0).strip()
        digits = re.sub(r"\D", "", candidate)
        if 7 <= len(digits) <= 15:
            return candidate
    return None

class GoogleMapsLeadScraper:
    def __init__(self):
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    async def scrape(
        self,
        query: str,
        max_results: int = 50,
        city: str = "",
        category: str = "Real Estate"
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Scrapes Google Maps for leads matching the query.
        Yields progress and lead data objects in real-time.
        """
        self._is_cancelled = False
        full_query = query.strip()
        if city and city.lower() not in full_query.lower():
            full_query = f"{full_query} in {city.strip()}"

        yield {
            "type": "log",
            "message": f"Starting scrape for query: '{full_query}' (target: {max_results} leads)..."
        }

        encoded_query = urllib.parse.quote_plus(full_query)
        maps_url = f"https://www.google.com/maps/search/{encoded_query}?hl=en"

        scraped_count = 0
        new_leads_count = 0

        async with async_playwright() as p:
            browser: Browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-accelerated-2d-canvas",
                    "--no-first-run",
                    "--no-zygote",
                    "--disable-gpu"
                ]
            )

            context: BrowserContext = await browser.new_context(
                viewport={"width": 1366, "height": 900},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                locale="en-US"
            )

            page: Page = await context.new_page()

            try:
                yield {"type": "log", "message": f"Navigating to Google Maps search..."}
                await page.goto(maps_url, timeout=45000, wait_until="domcontentloaded")

                # Handle Google consent dialog if it appears
                try:
                    consent_btn = page.locator("button[aria-label*='Accept all'], form[action*='consent'] button").first
                    if await consent_btn.is_visible(timeout=2500):
                        await consent_btn.click()
                        await page.wait_for_timeout(1000)
                except Exception:
                    pass

                # Locate the feed container containing results
                feed_selector = "div[role='feed']"
                try:
                    await page.wait_for_selector(f"{feed_selector}, div.Nv2PK, a.hfpxzc", timeout=12000)
                except Exception:
                    yield {"type": "log", "message": "Standard feed not found, checking single result or alternate layout..."}

                # Infinite scroll to load results
                yield {"type": "log", "message": "Scrolling to discover listings..."}
                
                seen_hrefs = set()
                scroll_attempts = 0
                max_scroll_attempts = max(10, (max_results // 3) + 5)

                while scroll_attempts < max_scroll_attempts and not self._is_cancelled:
                    # Find all listing elements
                    listing_anchors = await page.locator("a.hfpxzc").all()
                    
                    for anchor in listing_anchors:
                        href = await anchor.get_attribute("href")
                        if href and href not in seen_hrefs:
                            seen_hrefs.add(href)

                    if len(seen_hrefs) >= max_results:
                        break

                    # Scroll the feed
                    feed_exists = await page.locator(feed_selector).count() > 0
                    if feed_exists:
                        await page.eval_on_selector(
                            feed_selector,
                            "el => el.scrollBy(0, 1500)"
                        )
                    else:
                        await page.mouse.wheel(0, 1500)

                    await page.wait_for_timeout(1200)

                    # Check if end of list reached
                    end_text = await page.locator("span:has-text(\"You've reached the end of the list\")").is_visible()
                    if end_text:
                        yield {"type": "log", "message": "Reached end of Google Maps results."}
                        break

                    scroll_attempts += 1
                    yield {
                        "type": "progress",
                        "discovered": len(seen_hrefs),
                        "target": max_results,
                        "percent": min(95, int((len(seen_hrefs) / max_results) * 50))
                    }

                yield {"type": "log", "message": f"Found {len(seen_hrefs)} listings. Now extracting detailed contact information..."}

                # Now iterate through each listing item to extract detailed info
                cards = await page.locator("div.Nv2PK").all()
                if not cards:
                    cards = await page.locator("a.hfpxzc").all()

                items_to_process = cards[:max_results] if cards else []

                for idx, card in enumerate(items_to_process):
                    if self._is_cancelled:
                        yield {"type": "log", "message": "Scraping cancelled by user."}
                        break

                    lead_data = {
                        "name": "",
                        "phone": "",
                        "address": "",
                        "city": city or "",
                        "category": category or "Real Estate",
                        "rating": 0.0,
                        "reviews_count": 0,
                        "website": "",
                        "instagram": "",
                        "maps_url": "",
                        "query": full_query,
                        "call_status": "New",
                        "call_notes": ""
                    }

                    try:
                        # Extract basic info from card before clicking
                        name_elem = card.locator("div.qBF1Pd, div.fontHeadlineSmall").first
                        if await name_elem.count() > 0:
                            lead_data["name"] = clean_text(await name_elem.text_content())

                        anchor_elem = card.locator("a.hfpxzc").first if await card.locator("a.hfpxzc").count() > 0 else card
                        if await anchor_elem.count() > 0:
                            lead_data["maps_url"] = await anchor_elem.get_attribute("href") or ""

                        # Extract rating and review count from card text
                        card_text = await card.text_content() or ""
                        
                        rating_match = re.search(r"(\d\.\d)\s*stars?", card_text) or re.search(r"\b([1-5]\.\d)\b", card_text)
                        if rating_match:
                            try:
                                lead_data["rating"] = float(rating_match.group(1))
                            except ValueError:
                                pass

                        reviews_match = re.search(r"\((\d[\d,]*)\)", card_text)
                        if reviews_match:
                            try:
                                lead_data["reviews_count"] = int(reviews_match.group(1).replace(",", ""))
                            except ValueError:
                                pass

                        # Click on the card to open detail panel
                        await card.click()
                        await page.wait_for_timeout(1000)

                        # Extract detailed elements from the opened detail pane
                        detail_pane = page.locator("div[role='main'], div.m6QErb[aria-label]")

                        # Detail title if card name was missing
                        if not lead_data["name"]:
                            title_elem = page.locator("h1.DUwDvf, div.fontHeadlineLarge").first
                            if await title_elem.count() > 0:
                                lead_data["name"] = clean_text(await title_elem.text_content())

                        # Phone number
                        phone_btn = page.locator("button[data-item-id^='phone:'], button[aria-label*='Phone:']").first
                        if await phone_btn.count() > 0:
                            phone_text = await phone_btn.text_content()
                            lead_data["phone"] = clean_text(phone_text)
                        else:
                            # Try finding phone regex in the detail container
                            pane_text = await page.locator("div[role='main']").text_content() if await page.locator("div[role='main']").count() > 0 else card_text
                            extracted = extract_phone_from_text(pane_text)
                            if extracted:
                                lead_data["phone"] = extracted

                        # Address
                        addr_btn = page.locator("button[data-item-id='address'], button[aria-label*='Address:']").first
                        if await addr_btn.count() > 0:
                            lead_data["address"] = clean_text(await addr_btn.text_content())

                        # Website
                        web_btn = page.locator("a[data-item-id='authority'], a[aria-label*='Website:']").first
                        if await web_btn.count() > 0:
                            lead_data["website"] = await web_btn.get_attribute("href") or ""

                        # Category subtitle
                        cat_btn = page.locator("button[jsaction*='category']").first
                        if await cat_btn.count() > 0:
                            cat_text = clean_text(await cat_btn.text_content())
                            if cat_text:
                                lead_data["category"] = cat_text

                        # Instagram extraction from Google Maps page
                        ig_elem = page.locator("a[href*='instagram.com']").first
                        if await ig_elem.count() > 0:
                            lead_data["instagram"] = await ig_elem.get_attribute("href") or ""

                        # If Instagram not on maps but website exists, scan website for Instagram handle
                        if not lead_data["instagram"] and lead_data["website"]:
                            try:
                                import httpx
                                async with httpx.AsyncClient(timeout=3.5, follow_redirects=True) as client:
                                    res = await client.get(lead_data["website"], headers={"User-Agent": "Mozilla/5.0"})
                                    if res.status_code == 200:
                                        ig_match = re.search(r"https?://(?:www\.)?instagram\.com/([a-zA-Z0-9_.]{2,30})/?", res.text)
                                        if ig_match:
                                            handle = ig_match.group(1).rstrip("/?")
                                            if handle.lower() not in ["p", "explore", "reels", "stories", "tv"]:
                                                lead_data["instagram"] = f"https://www.instagram.com/{handle}/"
                            except Exception:
                                pass

                        # Fallback Instagram search URL if not directly extracted
                        if not lead_data["instagram"] and lead_data["name"]:
                            clean_ig_query = urllib.parse.quote_plus(f"{lead_data['name']} {lead_data.get('city', '')} instagram")
                            lead_data["instagram"] = f"https://www.google.com/search?q={clean_ig_query}"

                        # If city is empty, parse from address
                        if not lead_data["city"] and lead_data["address"]:
                            addr_parts = [p.strip() for p in lead_data["address"].split(",")]
                            if len(addr_parts) >= 2:
                                lead_data["city"] = addr_parts[-2]

                    except Exception as item_err:
                        yield {"type": "log", "message": f"Notice: Error extracting listing {idx + 1}: {str(item_err)}"}

                    if lead_data["name"]:
                        scraped_count += 1
                        is_new, lead_id = db.insert_or_update_lead(lead_data)
                        if is_new:
                            new_leads_count += 1
                        
                        lead_data["id"] = lead_id
                        lead_data["is_new"] = is_new

                        progress_pct = 50 + int(((idx + 1) / max(len(items_to_process), 1)) * 50)

                        yield {
                            "type": "lead",
                            "lead": lead_data,
                            "is_new": is_new,
                            "scraped_count": scraped_count,
                            "new_leads_count": new_leads_count,
                            "progress": {
                                "current": idx + 1,
                                "total": len(items_to_process),
                                "percent": min(100, progress_pct)
                            }
                        }

                yield {
                    "type": "complete",
                    "total_scraped": scraped_count,
                    "new_leads": new_leads_count,
                    "message": f"Scraping completed! Successfully processed {scraped_count} leads ({new_leads_count} newly added to database)."
                }

            except Exception as e:
                yield {
                    "type": "error",
                    "message": f"Scraper encountered an error: {str(e)}"
                }
            finally:
                await context.close()
                await browser.close()

scraper_instance = GoogleMapsLeadScraper()
