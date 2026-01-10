import asyncio
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from random import randint, uniform

from src.timezone_utils import get_sydney_now
from src.logger import get_logger

from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeout


logger = get_logger()


PROJECT_ROOT = Path(__file__).parent.parent
SCREENSHOTS_DIR = PROJECT_ROOT / "screenshots"


@dataclass
class PriceData:
    """Scraped price data from Amazon."""
    price: Optional[float]
    currency: str
    available: bool
    screenshot_path: str
    error: Optional[str] = None


class AmazonScraper:
    """Amazon AU price scraper using Playwright."""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.playwright = None
        self.user_agents = [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        ]

    async def setup_browser(self):
        """Initialize Playwright browser with anti-detection settings."""
        self.playwright = await async_playwright().start()

        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
            ]
        )

    async def close(self):
        """Close the browser and playwright instance."""
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None

    async def _create_context(self):
        """Create a new browser context with random settings."""
        if not self.browser:
            raise RuntimeError("Browser not initialized. Call setup_browser() first.")

        user_agent = self.user_agents[randint(0, len(self.user_agents) - 1)]

        context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent=user_agent,
            locale='en-AU',
            timezone_id='Australia/Sydney',
            extra_http_headers={
                'Accept-Language': 'en-AU,en;q=0.9',
            }
        )

        return context

    def _extract_price_from_text(self, text: str) -> Optional[float]:
        """Extract numeric price from text string."""
        if not text:
            return None

        # Remove currency symbols and whitespace
        text = text.strip().replace('$', '').replace('AUD', '').replace(',', '').strip()

        # Extract numeric value
        match = re.search(r'(\d+\.?\d*)', text)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None

        return None

    async def _extract_price(self, page: Page) -> Optional[float]:
        """Try multiple selectors to extract price from Amazon page."""
        # List of selectors to try (in priority order)
        selectors = [
            '.a-price .a-offscreen',
            '#priceblock_ourprice',
            '#priceblock_dealprice',
            '.a-price-whole',
            'span.a-price > span.a-offscreen',
            '#corePrice_feature_div .a-price .a-offscreen',
        ]

        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.inner_text()
                    price = self._extract_price_from_text(text)
                    if price is not None and price > 0:
                        return price
            except Exception as e:
                logger.debug(f"Error with selector {selector}: {e}")
                continue

        return None

    async def _check_availability(self, page: Page) -> bool:
        """Check if product is available for purchase."""
        # Check for common unavailability indicators
        unavailable_selectors = [
            '#availability .a-color-state',
            '#availability .a-color-price',
            '.a-button-unavailable',
        ]

        for selector in unavailable_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = (await element.inner_text()).lower()
                    if any(keyword in text for keyword in ['unavailable', 'out of stock', 'currently unavailable']):
                        return False
            except Exception:
                continue

        # If we found a price, assume it's available
        return True

    async def capture_screenshot(self, page: Page, product_id: str) -> str:
        """Capture screenshot of product page.

        Returns:
            Relative path string (e.g., "screenshots/product-id_20260110_120000.png")
        """
        timestamp = get_sydney_now().strftime('%Y%m%d_%H%M%S')
        filename = f"{product_id}_{timestamp}.png"
        screenshot_path = SCREENSHOTS_DIR / filename

        # Ensure screenshots directory exists
        SCREENSHOTS_DIR.mkdir(exist_ok=True)

        await page.screenshot(
            path=str(screenshot_path),
            full_page=False,
            type='png',
        )

        # Return relative path as string (used in JSON storage and email paths)
        return str(screenshot_path.relative_to(PROJECT_ROOT))

    async def scrape_price(self, product_url: str, product_id: str, retry: bool = True) -> PriceData:
        """Scrape price from Amazon product page."""
        if not self.browser:
            raise RuntimeError("Browser not initialized. Call setup_browser() first.")

        context = await self._create_context()
        page = await context.new_page()

        try:
            # Navigate to product page
            logger.debug(f"Navigating to {product_url}")
            await page.goto(product_url, wait_until='networkidle', timeout=30000)

            # Random wait to appear more human-like
            await asyncio.sleep(uniform(2.0, 5.0))

            # Check for "Continue shopping" bot detection page
            continue_button = await page.query_selector('input[type="submit"][value="Continue shopping"], button:has-text("Continue shopping")')
            if continue_button:
                logger.info("Detected 'Continue shopping' button - clicking to proceed...")
                await continue_button.click()
                await page.wait_for_load_state('networkidle', timeout=15000)
                await asyncio.sleep(uniform(1.0, 2.0))

            # Always set delivery location to Sydney 2000
            try:
                # Look for the delivery location indicator
                delivery_location = await page.query_selector('#glow-ingress-line2, #nav-global-location-popover-link')
                if delivery_location:
                    location_text = await delivery_location.inner_text()
                    logger.debug(f"Current delivery location: {location_text}")
                    logger.debug("Setting delivery location to Sydney 2000...")
                    await delivery_location.click()

                    # Wait for the location modal to appear
                    await page.wait_for_selector('input[type="text"][placeholder], input[type="text"]', timeout=5000)
                    await asyncio.sleep(uniform(0.5, 1.0))

                    # Find and fill the postcode input (try multiple selectors)
                    postcode_filled = False
                    for selector in ['#GLUXPostalCodeWithCity_PostalCodeInput']:
                        postcode_input = await page.query_selector(selector)
                        if postcode_input and await postcode_input.is_visible():
                            logger.debug(f"Found postcode input with selector: {selector}")
                            # Clear any existing value first
                            await postcode_input.focus()
                            await asyncio.sleep(0.2)
                            await postcode_input.fill('')  # Clear field
                            await asyncio.sleep(0.1)

                            # Type postcode character by character like a human
                            logger.debug("Typing postcode: 2-0-0-0...")
                            for char in '2000':
                                await postcode_input.type(char, delay=uniform(1000, 2500))  # Random delay between keystrokes

                            logger.debug("✓ Postcode entered, waiting for validation...")
                            await asyncio.sleep(uniform(0.5, 1.0))
                            postcode_filled = True
                            break

                    if postcode_filled:
                        # Select city from dropdown (validation happens automatically with character-by-character typing)
                        try:
                            logger.debug("Selecting city from dropdown...")

                            # Brief wait for dropdown to be ready (typing already triggered validation)
                            await asyncio.sleep(uniform(0.8, 1.2))

                            # Click the dropdown button to open city list
                            city_dropdown = await page.query_selector('#GLUXPostalCodeWithCity_DropdownButton')
                            if city_dropdown:
                                await city_dropdown.click()
                                logger.debug("✓ Clicked dropdown to open city list")
                                await asyncio.sleep(uniform(0.5, 0.8))

                                # Wait for dropdown options to appear
                                await page.wait_for_selector('a.a-dropdown-link', timeout=3000)

                                # Find and click "SYDNEY" option (exact match, not "SYDNEY SOUTH")
                                all_options = await page.query_selector_all('a.a-dropdown-link')
                                for option in all_options:
                                    text = await option.inner_text()
                                    if text.strip() == "SYDNEY":
                                        await option.click()
                                        logger.debug("✓ Selected SYDNEY from dropdown")
                                        await asyncio.sleep(0.5)
                                        break
                            else:
                                logger.debug("Could not find city dropdown button")

                        except Exception as e:
                            logger.debug(f"Could not select city from dropdown: {e}")
                            # Continue anyway - might not always be required

                        # Click apply button using the correct ID
                        try:
                            apply_button = await page.query_selector('#GLUXPostalCodeWithCityApplyButton')
                            if apply_button and await apply_button.is_visible():
                                logger.debug("Clicking apply button...")
                                await apply_button.click()
                                logger.debug("✓ Applied Sydney 2000 delivery location")
                                await page.wait_for_load_state('networkidle', timeout=10000)
                                await asyncio.sleep(uniform(1.0, 2.0))
                            else:
                                logger.debug("Apply button not found or not visible")
                        except Exception as e:
                            logger.debug(f"Error clicking apply button: {e}")
                    else:
                        logger.debug("Could not find postcode input field")
            except Exception as e:
                logger.debug(f"Could not change delivery location: {e}")
                # Continue anyway - might already be set or not critical

            # Wait for price element (or timeout)
            try:
                await page.wait_for_selector('.a-price, #priceblock_ourprice', timeout=15000)
                logger.debug("✓ Price element found")
            except PlaywrightTimeout:
                logger.warning("⚠️  Price element not found within timeout")
                # Check if we're still on a bot detection page
                page_title = await page.title()
                page_content = await page.content()
                if 'robot' in page_title.lower() or 'continue shopping' in page_content.lower():
                    screenshot_path = await self.capture_screenshot(page, f"{product_id}_blocked")
                    return PriceData(
                        price=None,
                        currency="AUD",
                        available=False,
                        screenshot_path=screenshot_path,
                        error="Amazon bot detection - unable to bypass"
                    )

            # Extract price
            price = await self._extract_price(page)

            # Check availability
            available = await self._check_availability(page)

            # Capture screenshot
            screenshot_path = await self.capture_screenshot(page, product_id)

            return PriceData(
                price=price,
                currency="AUD",
                available=available and price is not None,
                screenshot_path=screenshot_path,
                error=None if price is not None else "Price not found"
            )

        except PlaywrightTimeout as e:
            logger.error(f"Timeout error for {product_url}: {e}")

            # Retry once
            if retry:
                logger.info("Retrying after 5 seconds...")
                await asyncio.sleep(5)
                return await self.scrape_price(product_url, product_id, retry=False)

            return PriceData(
                price=None,
                currency="AUD",
                available=False,
                screenshot_path="",
                error=f"Timeout: {str(e)}"
            )

        except Exception as e:
            logger.error(f"Error scraping {product_url}: {e}")

            return PriceData(
                price=None,
                currency="AUD",
                available=False,
                screenshot_path="",
                error=str(e)
            )

        finally:
            # Always close the context, even if there was an error
            try:
                await context.close()
            except Exception as e:
                logger.warning(f"Warning: Error closing browser context: {e}")


async def test_scraper():
    """Test function for development."""
    scraper = AmazonScraper(headless=False)
    await scraper.setup_browser()

    # Test with a sample product (replace with actual URL)
    test_url = "https://www.amazon.com.au/dp/B0CX23V2ZK"  # Example ASIN
    result = await scraper.scrape_price(test_url, "test-product")

    logger.info(f"Price: ${result.price} {result.currency}")
    logger.info(f"Available: {result.available}")
    logger.info(f"Screenshot: {result.screenshot_path}")
    logger.info(f"Error: {result.error}")

    await scraper.close()


if __name__ == "__main__":
    asyncio.run(test_scraper())
