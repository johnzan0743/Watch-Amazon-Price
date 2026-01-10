import argparse
import asyncio
import os
import sys
from pathlib import Path
from random import uniform
from typing import Optional
from dotenv import load_dotenv

from src.config import load_products, load_price_history, save_price_history
from src.scraper import AmazonScraper
from src.price_tracker import PriceTracker
from src.email_sender import EmailSender
from src.logger import setup_logger


# Load environment variables
load_dotenv()

# Initialize logger
logger = setup_logger()


def get_env_var(name: str, required: bool = True) -> str:
    """Get environment variable with validation."""
    value = os.getenv(name)
    if required and not value:
        logger.error(f"Environment variable {name} is not set")
        sys.exit(1)
    return value or ""


async def main(
    dry_run: bool = True,
    test_email: bool = False,
    product_filter: Optional[str] = None
):
    """Main orchestration function."""
    logger.info("=" * 60)
    logger.info("Amazon AU Price Checker")
    logger.info("=" * 60)

    # Load configuration
    logger.info("\n[1/7] Loading configuration...")
    try:
        products = load_products()
        logger.info(f"✓ Loaded {len(products)} products from products.json")

        # Filter enabled products
        enabled_products = [p for p in products if p.enabled]
        logger.info(f"✓ {len(enabled_products)} products enabled for tracking")

        # Apply product filter if specified
        if product_filter:
            enabled_products = [p for p in enabled_products if p.id == product_filter]
            if not enabled_products:
                logger.error(f"No product found with ID '{product_filter}'")
                sys.exit(1)
            logger.info(f"✓ Filtered to single product: {product_filter}")

        if not enabled_products:
            logger.info("No enabled products to check. Exiting.")
            return

    except Exception as e:
        logger.error(f"✗ Failed to load products: {e}")
        sys.exit(1)

    # Load price history
    logger.info("\n[2/7] Loading price history...")
    price_history = load_price_history()
    logger.info(f"✓ Loaded history for {len(price_history)} products")

    # Initialize price tracker
    tracker = PriceTracker(price_history)

    # Get email configuration
    gmail_address = get_env_var("GMAIL_ADDRESS", required=not dry_run)
    gmail_app_password = get_env_var("GMAIL_APP_PASSWORD", required=not dry_run)
    recipient_email = get_env_var("RECIPIENT_EMAIL", required=not dry_run)

    # Test email mode
    if test_email:
        logger.info("\n[TEST EMAIL MODE]")
        email_sender = EmailSender(gmail_address, gmail_app_password)

        # Create a dummy product and stats for testing
        from src.config import Product, PriceRecord
        from src.price_tracker import PriceStats
        from src.timezone_utils import get_sydney_timestamp

        test_product = Product(
            id="test-product",
            name="Test Product - Email Preview",
            url="https://www.amazon.com.au/dp/TEST",
            enabled=True
        )

        test_stats = PriceStats(
            current_price=99.99,
            current_timestamp=get_sydney_timestamp(),
            all_time_low=99.99,
            all_time_low_timestamp=get_sydney_timestamp(),
            previous_low=149.99,
            avg_30_day=129.99,
            price_history_7_day=[
                PriceRecord(
                    timestamp=get_sydney_timestamp(),
                    price=99.99,
                    currency="AUD",
                    available=True,
                    screenshot=""
                )
            ],
            is_new_atl=True,
            savings_percentage=33.3
        )

        html_content = email_sender.create_email_content(test_product, test_stats)
        success = email_sender.send_email(
            to=recipient_email,
            subject="🎉 Test Email: All-Time Low Price Alert",
            html_content=html_content,
            screenshot_path=None
        )

        if success:
            logger.info("✓ Test email sent successfully!")
        else:
            logger.error("✗ Failed to send test email")

        return

    # Initialize browser
    logger.info("\n[3/7] Initializing browser...")
    scraper = AmazonScraper(headless=not dry_run)

    try:
        await scraper.setup_browser()
        logger.info("✓ Playwright browser ready")
    except Exception as e:
        logger.error(f"✗ Failed to initialize Playwright browser: {e}")
        logger.error("Please ensure Playwright is installed correctly:")
        logger.error("  uv run playwright install chromium")
        logger.error("  uv run playwright install-deps chromium")
        sys.exit(1)

    # Track results
    all_time_lows_detected = []
    errors = []

    try:
        # Scrape each product
        logger.info(f"\n[4/7] Scraping {len(enabled_products)} products...")
        for i, product in enumerate(enabled_products, 1):
            logger.info(f"\n[{i}/{len(enabled_products)}] Processing: {product.name}")
            logger.info(f"  URL: {product.url}")

            try:
                # Scrape price
                price_data = await scraper.scrape_price(product.url, product.id)

                if price_data.error:
                    logger.error(f"  ✗ Error: {price_data.error}")
                    errors.append({
                        "product": product.name,
                        "error": price_data.error
                    })
                    continue

                if price_data.price is None:
                    logger.warning(f"  ⚠ Price not found")
                    continue

                logger.info(f"  ✓ Price: ${price_data.price} {price_data.currency}")
                logger.info(f"  ✓ Available: {price_data.available}")
                logger.info(f"  ✓ Screenshot: {price_data.screenshot_path}")

                # Update price history
                is_new_atl = tracker.update_price_history(product, price_data)

                if is_new_atl:
                    logger.info(f"  🎉 NEW ALL-TIME LOW!")
                    all_time_lows_detected.append(product)

                # Delay before next product (respectful scraping)
                if i < len(enabled_products):
                    delay = uniform(5.0, 10.0)
                    logger.info(f"  Waiting {delay:.1f}s before next product...")
                    await asyncio.sleep(delay)

            except Exception as e:
                logger.error(f"  ✗ Unexpected error: {e}")
                errors.append({
                    "product": product.name,
                    "error": str(e)
                })

    finally:
        # Always close browser, even if errors occurred
        logger.info("\n[5/7] Closing browser...")
        try:
            await scraper.close()
            logger.info("✓ Browser closed")
        except Exception as e:
            logger.warning(f"⚠ Error while closing browser: {e}")

    # Send email notifications
    logger.info(f"\n[6/7] Sending notifications...")
    if all_time_lows_detected and not dry_run:
        email_sender = EmailSender(gmail_address, gmail_app_password)

        for product in all_time_lows_detected:
            stats = tracker.get_price_statistics(product.id)
            if stats:
                success = email_sender.send_all_time_low_alert(
                    product=product,
                    stats=stats,
                    recipient=recipient_email
                )

                if not success:
                    errors.append({
                        "product": product.name,
                        "error": "Failed to send email"
                    })
    elif all_time_lows_detected and dry_run:
        logger.info(f"  [DRY RUN] Would send {len(all_time_lows_detected)} email(s)")
        for product in all_time_lows_detected:
            logger.info(f"    - {product.name}")
    else:
        logger.info("  ✓ No all-time lows detected, no emails sent")

    # Save price history
    logger.info(f"\n[7/7] Saving price history...")
    if not dry_run:
        save_price_history(tracker.get_history())
        logger.info("✓ Price history saved to data/price_history.json")
    else:
        logger.info("  [DRY RUN] Skipping save")

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Products checked: {len(enabled_products)}")
    logger.info(f"All-time lows detected: {len(all_time_lows_detected)}")
    logger.info(f"Errors: {len(errors)}")

    if all_time_lows_detected:
        logger.info("\nAll-Time Lows:")
        for product in all_time_lows_detected:
            stats = tracker.get_price_statistics(product.id)
            if stats:
                logger.info(f"  🎉 {product.name}: ${stats.current_price}")

    if errors:
        logger.info("\nErrors:")
        for error in errors:
            logger.error(f"  ✗ {error['product']}: {error['error']}")

    logger.info("\n✓ Done!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Amazon AU Price Checker")
    parser.add_argument("--dry-run", action="store_true", help="Don't save data or send emails")
    parser.add_argument("--test-email", action="store_true", help="Send test email only")
    parser.add_argument("--product", type=str, help="Check only a specific product by ID")

    args = parser.parse_args()

    # Run async main
    asyncio.run(main(
        dry_run=args.dry_run,
        test_email=args.test_email,
        product_filter=args.product
    ))
