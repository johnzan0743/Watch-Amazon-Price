# Amazon AU Price Tracker

Automated price monitoring for Amazon Australia products with email alerts for all-time low prices.

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

# Send test email
python -m src.main --test-email

# Full run (dry run)
python -m src.main --dry-run

# Full run (with emails and save)
python -m src.main
```

## Project Structure

```
Watch-Amazon-Price/
├── .github/workflows/
│   └── price-check.yml          # GitHub Actions workflow
├── src/
│   ├── config.py                # Configuration loader
│   ├── scraper.py               # Playwright scraping
│   ├── price_tracker.py         # Price history management
│   ├── email_sender.py          # Gmail notifications
│   └── main.py                  # Main orchestration
├── data/
│   ├── products.json            # Product list (edit this!)
│   └── price_history.json       # Price tracking (auto-updated)
├── screenshots/                 # Product screenshots
├── pyproject.toml               # Dependencies
└── README.md                    # This file
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

## Email Notifications

Emails are sent **only when all-time lows are detected**. Each email includes:

- Current price (prominently displayed)
- All-time low badge
- Previous low price with savings percentage
- Last 7 days price history table
- 30-day average price
- Product screenshot
- Direct "View on Amazon" link

## Troubleshooting

### No emails received

- Check GitHub Actions workflow runs for errors
- Verify GitHub Secrets are set correctly
- Ensure products are enabled in `products.json`
- Check spam folder

### Scraping errors

- Amazon occasionally shows CAPTCHAs (script will skip and retry next day)
- Price selectors may change (update `src/scraper.py`)
- Check screenshot in repository to debug

### Workflow fails

- Check Actions tab for error logs
- Verify all dependencies install correctly
- Ensure Playwright chromium installs successfully

## Advanced Usage

### Change Schedule

Edit `.github/workflows/price-check.yml`:

```yaml
schedule:
  - cron: '0 14 * * *'  # Run at 2:00 PM UTC instead
```

### Screenshot Cleanup

Screenshots accumulate over time. To clean up old screenshots:

```bash
# Delete screenshots older than 30 days
find screenshots -name "*.png" -mtime +30 -delete
git add screenshots/
git commit -m "chore: clean up old screenshots"
git push
```

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
