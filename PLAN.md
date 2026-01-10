# Amazon AU Price Tracker - Implementation Plan

## Overview
Build a GitHub Actions workflow that checks Amazon AU prices daily, tracks price history in JSON, and sends Gmail notifications when all-time lows are detected. Uses Playwright for scraping with screenshots.

## Project Structure

```
Watch-Amazon-Price/
├── .github/workflows/price-check.yml    # Daily GHA workflow
├── src/
│   ├── __init__.py
│   ├── config.py                        # Load products & price history
│   ├── scraper.py                       # Playwright scraping + screenshots
│   ├── price_tracker.py                 # Price history & ATL detection
│   ├── email_sender.py                  # Gmail SMTP notifications
│   └── main.py                          # Main orchestration script
├── data/
│   ├── products.json                    # Product list (user-editable)
│   └── price_history.json               # Price tracking (auto-updated)
├── screenshots/                          # Product screenshots (committed)
├── test/
│   └── test_scraper.py                  # Testing scripts
├── pyproject.toml                       # Dependencies with uv
├── .gitignore
├── README.md
├── SETUP.md                             # GitHub Secrets setup guide
└── PLAN.md                              # Copy of this plan
```

## Configuration Formats

### products.json
```json
{
  "products": [
    {
      "id": "product-001",
      "name": "Product Name",
      "url": "https://www.amazon.com.au/dp/ASIN",
      "enabled": true,
      "notes": "Optional notes"
    }
  ]
}
```

### price_history.json
```json
{
  "product-001": {
    "name": "Product Name",
    "url": "https://www.amazon.com.au/dp/ASIN",
    "price_history": [
      {
        "timestamp": "2026-01-10T02:00:00Z",
        "price": 459.00,
        "currency": "AUD",
        "available": true,
        "screenshot": "screenshots/product-001_20260110_020000.png"
      }
    ],
    "all_time_low": {
      "price": 459.00,
      "timestamp": "2026-01-10T02:00:00Z"
    },
    "last_checked": "2026-01-10T02:00:00Z"
  }
}
```

## Implementation Steps

### 1. Project Setup
- Create directory structure and empty files
- Configure pyproject.toml with dependencies:
  - playwright >= 1.48.0
  - beautifulsoup4 >= 4.12.0 (HTML parsing backup)
  - python-dotenv >= 1.0.0 (local testing)
  - pytz >= 2024.1 (timezone handling)
- Create .gitignore (exclude .venv, .env, __pycache__)
- Initialize empty data files

### 2. Configuration Module (src/config.py)
**Functions:**
- `load_products()` → List[Product]: Load and validate products.json
- `load_price_history()` → Dict: Load existing price history
- `save_price_history(data)`: Save updated history with atomic write

**Classes:**
- `Product`: Dataclass for product info (id, name, url, enabled)
- `PriceRecord`: Dataclass for price entry (timestamp, price, currency, available, screenshot)
- `ProductHistory`: Dataclass for product tracking data

### 3. Web Scraper (src/scraper.py)
**Key Features:**
- Playwright browser setup (headless, anti-detection)
- Amazon price extraction with multiple selectors:
  - `.a-price .a-offscreen` (primary)
  - `#priceblock_ourprice` (legacy)
  - `#priceblock_dealprice` (deals)
  - Fallback to `.a-price-whole`
- Full-page screenshot capture
- Error handling with retry logic
- Random delays (5-10s between products)

**Functions:**
- `setup_browser()` → Browser: Configure Playwright with anti-bot settings
- `scrape_price(url)` → PriceData: Extract price and availability
- `capture_screenshot(page, product_id)` → str: Save PNG, return path

**Anti-bot measures:**
- Realistic user agent (macOS Chrome)
- Viewport 1920x1080
- Locale en-AU, timezone Australia/Sydney
- Random wait times (2-5s)
- Sequential processing (no parallel)

### 4. Price Tracker (src/price_tracker.py)
**Functions:**
- `update_price_history(product_id, price_data)` → bool: Add price record, update ATL, return True if new ATL
- `get_price_statistics(product_id, current_price)` → PriceStats: Calculate current, ATL, 30-day avg, trend
- `is_all_time_low(product_id, current_price)` → bool: Compare with historical low

**Logic:**
- First run: Initialize with current price as ATL (no email)
- Subsequent runs: Compare and detect new ATLs
- Keep full price history (no pruning)

### 5. Email Sender (src/email_sender.py)
**Functions:**
- `create_email_content(product, stats, screenshot_path)` → str: Generate HTML email
- `send_email(to, subject, html, screenshot)`: Send via Gmail SMTP with TLS

**Email Template:**
- Subject: "🎉 All-Time Low Price Alert: [Product Name]"
- Header with ATL badge
- Current price (large, bold)
- Previous low comparison with savings percentage
- Embedded screenshot (CID attachment)
- Last 7 days price history table
- 30-day average
- "View on Amazon" button
- Timestamp in Australian time

**SMTP Configuration:**
- Server: smtp.gmail.com:587
- Auth: App password from GitHub Secrets
- TLS encryption

### 6. Main Orchestration (src/main.py)
**Workflow:**
1. Load products configuration
2. Load existing price history
3. Initialize Playwright browser
4. For each enabled product:
   - Scrape current price (with 5-10s delay)
   - Capture screenshot
   - Update price history
   - If new ATL detected: queue email
5. Send all queued emails
6. Save updated price_history.json
7. Cleanup browser
8. Log summary (X products checked, Y ATLs found)

**Error Handling:**
- Individual product failures don't stop run
- Retry failed scrapes once (5s delay)
- Log all errors with product ID
- Continue processing remaining products

**CLI Arguments (for testing):**
- `--dry-run`: Don't commit or send emails
- `--test-email`: Send test email only
- `--product <id>`: Process single product

### 7. GitHub Actions Workflow (.github/workflows/price-check.yml)
```yaml
name: Amazon Price Checker
on:
  schedule:
    - cron: '0 2 * * *'  # 2 AM UTC = ~12 PM Australian time
  workflow_dispatch:     # Manual trigger

jobs:
  check-prices:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - Checkout code
      - Setup Python 3.12
      - Install uv package manager
      - Create .venv and install dependencies
      - Install Playwright chromium
      - Run price checker with secrets
      - Commit price_history.json and screenshots
      - Push changes (with [skip ci])
```

**Environment Variables (from Secrets):**
- `GMAIL_ADDRESS`: Sender Gmail
- `GMAIL_APP_PASSWORD`: App-specific password
- `RECIPIENT_EMAIL`: Recipient email

**Commit Strategy:**
- Commit only if price_history.json or screenshots changed
- Message: "chore: update price history [skip ci]"
- Bot user: github-actions[bot]

### 8. Documentation
**README.md:**
- Project overview
- Features list
- Quick start guide
- Local testing instructions
- GitHub Actions setup

**SETUP.md:**
- Step-by-step Gmail app password creation
- How to add GitHub Secrets
- Product configuration guide
- Troubleshooting common issues

**PLAN.md:**
- Copy of this implementation plan

## Critical Files (Implementation Order)

1. **pyproject.toml** - Dependencies configuration
2. **src/config.py** - Configuration loader (foundation)
3. **src/scraper.py** - Amazon scraping with Playwright (core logic)
4. **src/price_tracker.py** - Price history management (core logic)
5. **src/email_sender.py** - Gmail notifications (core logic)
6. **src/main.py** - Orchestration and CLI
7. **.github/workflows/price-check.yml** - Automation workflow
8. **data/products.json** - Initial product template
9. **data/price_history.json** - Empty initial state
10. **.gitignore** - Exclude .venv, .env, etc.

## GitHub Secrets Setup

Configure in: Repository Settings → Secrets and variables → Actions

1. **GMAIL_ADDRESS**: Your Gmail address (e.g., yourname@gmail.com)
2. **GMAIL_APP_PASSWORD**:
   - Go to https://myaccount.google.com/apppasswords
   - Requires 2FA enabled on Google account
   - Generate new app password for "Mail"
   - Copy 16-character password
3. **RECIPIENT_EMAIL**: Email to receive alerts (can be same as sender)

## Local Testing Process

### Initial Setup
```bash
# Configure uv for in-project venv
cd "/Users/yuanzhuang/Claude Projects/Watch-Amazon-Price"
uv venv .venv
source .venv/bin/activate

# Install dependencies
uv pip install -e .
playwright install chromium

# Create .env for local testing (don't commit)
cat > .env << EOF
GMAIL_ADDRESS=your-email@gmail.com
GMAIL_APP_PASSWORD=your-app-password
RECIPIENT_EMAIL=recipient@example.com
EOF
```

### Test Sequence
```bash
# 1. Test configuration loading
python -c "from src.config import load_products; print(load_products())"

# 2. Test single product scraping
python src/main.py --product product-001 --dry-run

# 3. Test email sending
python src/main.py --test-email

# 4. Test full run (dry run - no commit/email)
python src/main.py --dry-run

# 5. Test normal run (with commit and email)
python src/main.py
```

### Verify Local Results
- Check `data/price_history.json` created/updated
- Check `screenshots/` contains PNG files
- Check email received with correct content
- Verify git shows changes to commit

## GitHub Actions Testing

1. **Setup Secrets:**
   - Add all three secrets in repository settings
   - Verify no typos in secret names

2. **Initial Manual Run:**
   - Go to Actions tab
   - Select "Amazon Price Checker" workflow
   - Click "Run workflow" → "Run workflow"
   - Monitor execution logs

3. **Verify Results:**
   - Check workflow completed successfully (green checkmark)
   - Verify commit appeared in repository (price_history.json updated)
   - Check email received
   - Review screenshots in repository

4. **Enable Scheduled Runs:**
   - Already enabled by cron schedule
   - Will run daily at 2 AM UTC automatically

## Verification Checklist

### ✅ Core Functionality
- [ ] Project structure created correctly
- [ ] Dependencies install without errors
- [ ] Playwright chromium downloads successfully
- [ ] Products.json loads and validates
- [ ] Amazon AU pages scrape successfully
- [ ] Prices parse correctly (AUD format)
- [ ] Screenshots capture and save
- [ ] Price history updates correctly
- [ ] All-time low detection works
- [ ] Email generates with correct HTML
- [ ] Email sends via Gmail SMTP
- [ ] Screenshot embeds in email

### ✅ GitHub Actions
- [ ] Workflow file syntax valid
- [ ] Secrets configured correctly
- [ ] Manual trigger works
- [ ] Dependencies install in CI
- [ ] Playwright installs in CI
- [ ] Script runs successfully
- [ ] Commits push back to repository
- [ ] No infinite loop ([skip ci] works)
- [ ] Scheduled run executes daily

### ✅ Error Handling
- [ ] Invalid product URL handled gracefully
- [ ] Network timeout retries work
- [ ] Missing price element doesn't crash
- [ ] Email failure doesn't stop run
- [ ] Individual product errors isolated
- [ ] Logs contain useful debugging info

### ✅ Edge Cases
- [ ] First run (empty history) initializes correctly
- [ ] Same price doesn't trigger email
- [ ] Out of stock products handled
- [ ] Multiple ATLs in one run handled
- [ ] No products enabled handled
- [ ] Empty products list handled

## Key Design Decisions

1. **JSON Storage**: Simple, version-controlled, no infrastructure needed. Perfect for daily updates on 10-50 products.

2. **Playwright over Requests**: Amazon pages are JavaScript-heavy. Playwright ensures reliability and handles dynamic content.

3. **Gmail SMTP**: Simple setup for personal use. Can migrate to SendGrid/SES if scaling needed.

4. **Screenshots in Git**: Simple approach with 30-day cleanup. Can migrate to GitHub Releases if size becomes issue.

5. **Daily Runs at 2 AM UTC**: Respectful scraping, sufficient frequency, maps to ~12 PM Australian time.

6. **Sequential Processing**: Respectful rate limiting (5-10s delays), avoids hammering Amazon.

7. **All-Time Low Only**: Reduces email noise, focuses on actionable deals.

## Potential Enhancements (Future)

- Multiple email recipients
- Slack/Discord notifications
- Price drop percentage threshold (e.g., alert on 10%+ drop)
- Wishlist import from Amazon
- Price prediction using history
- Weekly summary emails
- Mobile app integration
- Multi-region support (US, UK, etc.)
- CAPTCHA solving service integration
- Screenshot cleanup automation (>30 days)

## Maintenance Notes

- **Weekly**: Review GitHub Actions runs for failures
- **Monthly**: Update dependencies for security patches
- **Quarterly**: Rotate Gmail app password
- **As needed**: Update Amazon selectors if scraping breaks
- **Monitor**: Repository size if screenshots accumulate

## Implementation Timeline

Estimated: 1-2 hours total (simple, well-defined project)

1. **Setup** (15 min): Project structure, dependencies, configs
2. **Core Logic** (30 min): Scraper, tracker, email modules
3. **Integration** (15 min): Main script and orchestration
4. **GitHub Actions** (10 min): Workflow file and secrets
5. **Testing** (20 min): Local testing and first GHA run
6. **Documentation** (10 min): README and SETUP

Ready to implement! 🚀
