# Amazon AU Price Tracker

Automated price monitoring for Amazon Australia products with email alerts for all-time low prices.

> **Latest Update (2026-01-13):** Added test email workflow for easy verification of email delivery without running price checks. See [Testing Email Functionality](#testing-email-functionality) below.

## Features

- **Daily Price Checks**: Automated GitHub Actions workflow runs once per day
- **All-Time Low Alerts**: Email notifications only when prices hit new all-time lows
- **Rich Notifications**: HTML emails with price history, screenshots, and direct Amazon links
- **Price History Tracking**: JSON-based storage committed to repository for full history
- **Playwright Scraping**: Reliable scraping with anti-detection measures
- **Multi-Product Support**: Track unlimited products from a single configuration file

## How It Works

1. **GitHub Actions** runs daily at 2:00 AM UTC (~12:00 PM Australian time)
2. **Playwright** scrapes current prices from Amazon AU product pages
3. **Price Tracker** compares with historical data to detect all-time lows
4. **Email Alerts** sent via Gmail when new all-time lows are detected
5. **Price History** automatically committed back to the repository

## Quick Start

### 1. Setup Gmail App Password

Follow the instructions in [SETUP.md](SETUP.md) to create a Gmail app password.

### 2. Configure GitHub Secrets

Add these secrets in your repository settings (Settings → Secrets and variables → Actions):

- `GMAIL_ADDRESS`: Your Gmail address (e.g., `yourname@gmail.com`)
- `GMAIL_APP_PASSWORD`: Your Gmail app-specific password (16 characters)
- `RECIPIENT_EMAIL`: Email address to receive alerts

### 3. Add Products to Track

Edit `data/products.json`:

```json
{
  "products": [
    {
      "id": "sony-headphones",
      "name": "Sony WH-1000XM5 Headphones",
      "url": "https://www.amazon.com.au/dp/B09XS7JWHH",
      "enabled": true,
      "notes": "Noise-canceling headphones"
    }
  ]
}
```

### 4. Enable GitHub Actions

- Push your changes to GitHub
- The workflow will run automatically daily
- You can also trigger manually: Actions → Amazon Price Checker → Run workflow

## Local Testing

### Setup Development Environment

```bash
# Create virtual environment
uv venv .venv
source .venv/bin/activate  # On Unix/macOS
# .venv\Scripts\activate   # On Windows

# Install dependencies
uv pip install -e .
playwright install chromium

# Create .env file for local testing
cat > .env << EOF
GMAIL_ADDRESS=your-email@gmail.com
GMAIL_APP_PASSWORD=your-app-password
RECIPIENT_EMAIL=recipient@example.com
EOF
```

### Test Commands

```bash
# Test configuration loading
python -c "from src.config import load_products; print(load_products())"

# Test single product (dry run - no emails/commits)
python -m src.main --product sony-headphones --dry-run

# Send test email (verify email delivery)
python -m src.main --test-email

# Full run (dry run)
python -m src.main --dry-run

# Full run (with emails and save)
python -m src.main
```

## Testing Email Functionality

### GitHub Actions (Recommended)

Test email functionality directly from GitHub without local setup:

1. Go to **Actions** tab in your repository
2. Select **Test Email Sending** workflow
3. Click **Run workflow** → **Run workflow**
4. Check your email inbox for test email
5. Review workflow logs if needed

The test email will have subject "🎉 Test Email: All-Time Low Price Alert" and shows a preview of the actual alert format.

### Local Testing

```bash
# Send test email from local environment
python -m src.main --test-email
```

This creates a dummy product with test data and sends a formatted HTML email to verify:
- Gmail credentials are correct
- Email delivery works
- HTML formatting renders properly

## Project Structure

```
Watch-Amazon-Price/
├── .github/workflows/
│   ├── price-check.yml          # Daily price checking workflow
│   └── test-email.yml           # Email testing workflow
├── src/
│   ├── config.py                # Configuration loader
│   ├── scraper.py               # Playwright scraping
│   ├── price_tracker.py         # Price history management
│   ├── email_sender.py          # Gmail notifications
│   ├── timezone_utils.py        # Sydney timezone handling
│   ├── logger.py                # Logging configuration
│   └── main.py                  # Main orchestration
├── data/
│   ├── products.json            # Product list (edit this!)
│   └── price_history.json       # Price tracking (auto-updated)
├── screenshots/                 # Product screenshots
├── logs/                        # Application logs
├── pyproject.toml               # Dependencies
├── README.md                    # This file
└── SETUP.md                     # Detailed setup guide
```

## Configuration

### Products Configuration

The `data/products.json` file defines which products to track:

- `id`: Unique identifier (use lowercase, hyphens)
- `name`: Product display name
- `url`: Full Amazon AU product URL (must include `/dp/` or `/gp/product/`)
- `enabled`: Set to `false` to temporarily disable tracking
- `notes`: Optional notes for your reference

### Price History

The `data/price_history.json` file is automatically managed by the script. It stores:

- Complete price history for each product
- All-time low price and timestamp
- Screenshot paths for reference
- Last checked timestamp

## GitHub Actions Workflows

### Price Check Workflow (Daily)

**File:** `.github/workflows/price-check.yml`

- **Schedule:** Runs daily at 2:00 AM UTC (~12:00 PM Australian Eastern Time)
- **Manual Trigger:** Available via Actions tab
- **Functions:**
  - Scrapes prices for all enabled products
  - Updates price history
  - Sends email alerts for all-time lows
  - Commits updates back to repository
  - Cleans up screenshots older than 30 days
- **Artifacts:** Uploads logs for 30 days

### Test Email Workflow (Manual)

**File:** `.github/workflows/test-email.yml`

- **Schedule:** Manual trigger only (can be scheduled weekly if desired)
- **Purpose:** Verify email delivery without running price checks
- **Functions:**
  - Sends test email with sample data
  - Validates Gmail credentials
  - Tests HTML email formatting
- **Artifacts:** Uploads logs for 7 days

**To run:** Actions → Test Email Sending → Run workflow

## Email Notifications

### When Emails Are Sent

Emails are sent **only when all-time lows are detected**. First run initializes prices but won't send emails.

### Email Content

Each all-time low alert includes:

- Current price (prominently displayed)
- All-time low badge
- Previous low price with savings percentage
- Last 7 days price history table
- 30-day average price
- Product screenshot (single product emails only)
- Direct "View on Amazon" link

### Batch Alerts

When multiple products hit all-time lows on the same day, they're consolidated into a single email for convenience.

## Troubleshooting

### No emails received

1. **Run the test email workflow** to verify email setup:
   - Go to Actions → Test Email Sending → Run workflow
   - Check your inbox/spam folder for test email
2. Check GitHub Actions workflow runs for errors
3. Verify GitHub Secrets are set correctly (GMAIL_ADDRESS, GMAIL_APP_PASSWORD, RECIPIENT_EMAIL)
4. Ensure products are enabled in `products.json`
5. Remember: First run initializes prices (no emails sent)
6. Emails only sent for all-time lows (not every price change)

### Scraping errors

- Amazon occasionally shows CAPTCHAs (script will skip and retry next day)
- Price selectors may change (update `src/scraper.py`)
- Check screenshot in repository to debug

### Workflow fails

- Check Actions tab for error logs
- Verify all dependencies install correctly
- Ensure Playwright chromium installs successfully

## Quick Reference

### GitHub Actions Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| **Amazon Price Checker** | Daily at 2:00 AM UTC<br>Manual trigger | Check all product prices, send alerts, update history |
| **Test Email Sending** | Manual trigger only | Test email delivery without price checking |

**Manual Trigger:** Actions tab → Select workflow → Run workflow

### Command Line Interface

| Command | Description |
|---------|-------------|
| `python -m src.main` | Full run (scrapes prices, sends emails, saves history) |
| `python -m src.main --dry-run` | Preview run (no emails, no saves) |
| `python -m src.main --test-email` | Send test email to verify delivery |
| `python -m src.main --product PRODUCT_ID` | Check single product only |
| `python -m src.main --product PRODUCT_ID --dry-run` | Dry run for single product |

### Environment Variables

Required for email functionality:

| Variable | Description | Example |
|----------|-------------|---------|
| `GMAIL_ADDRESS` | Gmail account address | `yourname@gmail.com` |
| `GMAIL_APP_PASSWORD` | Gmail app-specific password | `abcdefghijklmnop` |
| `RECIPIENT_EMAIL` | Email to receive alerts | `recipient@example.com` |

Set in:
- GitHub: Settings → Secrets and variables → Actions
- Local: Create `.env` file in project root

### File Locations

| File/Directory | Purpose | Edit? |
|----------------|---------|-------|
| `data/products.json` | Product tracking list | ✅ Yes - Add/remove products |
| `data/price_history.json` | Historical price data | ❌ No - Auto-generated |
| `screenshots/` | Product page screenshots | ❌ No - Auto-generated |
| `logs/` | Application logs | ❌ No - Auto-generated |
| `.env` | Local environment variables | ✅ Yes - Local testing only |
| `.github/workflows/` | GitHub Actions config | ⚠️ Advanced users only |

## Advanced Usage

### Change Schedule

Edit `.github/workflows/price-check.yml`:

```yaml
schedule:
  - cron: '0 14 * * *'  # Run at 2:00 PM UTC instead
```

### Screenshot Cleanup

Screenshots are **automatically cleaned up** by the GitHub Actions workflow:
- The `cleanup-old-screenshots` job runs after each price check
- Deletes screenshots older than 30 days
- Automatically commits changes to the repository

Manual cleanup (if needed):

```bash
# Delete screenshots older than 30 days locally
find screenshots -name "*.png" -mtime +30 -delete
git add screenshots/
git commit -m "chore: clean up old screenshots"
git push
```

### Enable Weekly Email Tests

To enable automatic weekly email testing, edit `.github/workflows/test-email.yml`:

```yaml
on:
  workflow_dispatch:
  schedule:
    - cron: '0 12 * * 1'  # Weekly on Monday at 12:00 UTC
```

Uncomment the `schedule` section to run weekly tests.

## Privacy & Security

- **Never commit `.env` file** (contains credentials)
- **Use app-specific passwords** (not your main Gmail password)
- **Enable 2FA** on your Gmail account
- **Keep repository private** if tracking personal shopping lists
- **Monitor GitHub Actions logs** for sensitive data leaks

## Contributing

This is a personal project, but suggestions and improvements are welcome!

## License

MIT License - feel free to use and modify for your own needs.

## Acknowledgments

- Built with [Playwright](https://playwright.dev/) for reliable web scraping
- Automated with [GitHub Actions](https://github.com/features/actions)
- Email via Gmail SMTP

---

**Happy Price Hunting!** 🎯
