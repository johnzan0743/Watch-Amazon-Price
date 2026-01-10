# Setup Guide

Complete step-by-step instructions for setting up the Amazon AU Price Tracker.

## Prerequisites

- GitHub account
- Gmail account with 2FA enabled
- Python 3.12+ (for local testing)

## Part 1: Gmail App Password Setup

### Step 1: Enable 2-Factor Authentication

1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Under "How you sign in to Google", click on "2-Step Verification"
3. Follow the prompts to enable 2FA if not already enabled

### Step 2: Create App Password

1. Go to [App Passwords](https://myaccount.google.com/apppasswords)
   - Or: Google Account → Security → 2-Step Verification → App passwords (at bottom)
2. Click "Select app" and choose "Mail"
3. Click "Select device" and choose "Other (Custom name)"
4. Enter name: "Amazon Price Tracker"
5. Click "Generate"
6. **Copy the 16-character password** (looks like: `abcd efgh ijkl mnop`)
   - Remove spaces when using: `abcdefghijklmnop`
7. Click "Done"

**Important:** Save this password securely - you won't be able to see it again!

## Part 2: GitHub Repository Setup

### Step 1: Create Repository

1. Go to [GitHub](https://github.com) and create a new repository
2. Name it: `Watch-Amazon-Price` (or your preferred name)
3. Choose **Private** (recommended for personal shopping lists)
4. Don't initialize with README (we already have one)

### Step 2: Push Code

```bash
cd "/Users/yuanzhuang/Claude Projects/Watch-Amazon-Price"

# Initialize git (if not already done)
git init
git branch -M main

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit: Amazon AU price tracker"

# Add remote (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/Watch-Amazon-Price.git

# Push to GitHub
git push -u origin main
```

### Step 3: Configure GitHub Secrets

1. Go to your repository on GitHub
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**

Add these three secrets:

#### Secret 1: GMAIL_ADDRESS
- Name: `GMAIL_ADDRESS`
- Value: Your Gmail address (e.g., `yourname@gmail.com`)
- Click "Add secret"

#### Secret 2: GMAIL_APP_PASSWORD
- Name: `GMAIL_APP_PASSWORD`
- Value: Your 16-character app password from Part 1 (without spaces)
- Click "Add secret"

#### Secret 3: RECIPIENT_EMAIL
- Name: `RECIPIENT_EMAIL`
- Value: Email address to receive alerts (can be same as GMAIL_ADDRESS)
- Click "Add secret"

**Verify:** You should see 3 secrets listed. The values will be hidden (shown as `***`).

## Part 3: Product Configuration

### Add Your Products

1. Edit `data/products.json` in your repository
2. Replace the example product with your actual products:

```json
{
  "products": [
    {
      "id": "product-001",
      "name": "Sony WH-1000XM5 Headphones",
      "url": "https://www.amazon.com.au/dp/B09XS7JWHH",
      "enabled": true,
      "notes": "Flagship noise-canceling headphones"
    },
    {
      "id": "product-002",
      "name": "Logitech MX Master 3S",
      "url": "https://www.amazon.com.au/dp/B09HM94VDS",
      "enabled": true,
      "notes": "Wireless mouse"
    }
  ]
}
```

**Tips:**
- Find product URLs by searching on amazon.com.au
- Copy the URL from the browser address bar
- The URL should contain `/dp/XXXXXXXXXX` (ASIN code)
- Use descriptive IDs (lowercase, hyphens, no spaces)

### Commit Changes

```bash
git add data/products.json
git commit -m "Add products to track"
git push
```

## Part 4: Enable GitHub Actions

### Step 1: Enable Actions

1. Go to your repository on GitHub
2. Click the **Actions** tab
3. If prompted, click "I understand my workflows, go ahead and enable them"

### Step 2: Verify Workflow

1. You should see "Amazon Price Checker" workflow listed
2. The workflow will run automatically daily at 2:00 AM UTC
3. Or you can trigger it manually (see below)

### Step 3: Manual Test Run

1. Go to **Actions** tab
2. Click "Amazon Price Checker" in the left sidebar
3. Click **Run workflow** button (on the right)
4. Click the green **Run workflow** button in the dropdown
5. Wait for the workflow to complete (2-5 minutes)

### Step 4: Check Results

After the workflow completes:

1. **Check the workflow log:**
   - Click on the workflow run
   - Click on "check-prices" job
   - Review logs for any errors

2. **Check for commits:**
   - Go to repository main page
   - You should see a new commit: "chore: update price history"
   - Click on `data/price_history.json` to see tracked prices

3. **Check for email:**
   - If any all-time lows were detected, check your email
   - First run initializes prices (no emails sent)
   - Subsequent runs will send emails for new all-time lows

## Part 5: Local Testing (Optional)

### Setup Local Environment

```bash
# Navigate to project directory
cd "/Users/yuanzhuang/Claude Projects/Watch-Amazon-Price"

# Create virtual environment
uv venv .venv
source .venv/bin/activate  # On macOS/Linux
# .venv\Scripts\activate   # On Windows

# Install dependencies
uv pip install -e .

# Install Playwright browser
playwright install chromium
```

### Create .env File

```bash
cat > .env << EOF
GMAIL_ADDRESS=your-email@gmail.com
GMAIL_APP_PASSWORD=your-16-char-app-password
RECIPIENT_EMAIL=recipient@example.com
EOF
```

**Important:** Never commit `.env` file! It's already in `.gitignore`.

### Test Locally

```bash
# Test email sending
python -m src.main --test-email

# Test single product (dry run)
python -m src.main --product product-001 --dry-run

# Full run locally (dry run)
python -m src.main --dry-run

# Full run (will save and send emails)
python -m src.main
```

## Verification Checklist

- [ ] Gmail app password created successfully
- [ ] Repository created on GitHub (private recommended)
- [ ] Code pushed to GitHub
- [ ] 3 GitHub Secrets configured
- [ ] Products added to `data/products.json`
- [ ] GitHub Actions enabled
- [ ] First workflow run completed successfully
- [ ] `price_history.json` created with initial prices
- [ ] (Optional) Local testing works

## Troubleshooting

### "Error: Environment variable GMAIL_ADDRESS is not set"

**Solution:** GitHub Secrets not configured correctly. Go to Settings → Secrets and verify all 3 secrets are set.

### "Authentication failed" when sending email

**Solution:**
1. Verify app password is correct (16 characters, no spaces)
2. Ensure 2FA is enabled on your Gmail account
3. Try creating a new app password

### Workflow fails with "Playwright browser not installed"

**Solution:** This should auto-install in the workflow. If it fails:
1. Check the workflow logs for specific errors
2. Verify the workflow YAML is correct

### No email received (but workflow succeeded)

**Possible reasons:**
1. **First run:** First run initializes prices but doesn't send emails (expected)
2. **No all-time lows:** Emails only sent for new all-time lows
3. **Spam folder:** Check spam/junk folder
4. **Wrong recipient:** Verify `RECIPIENT_EMAIL` secret

### Products not being tracked

**Solutions:**
1. Verify `enabled: true` in products.json
2. Check URL format (must be amazon.com.au with /dp/ or /gp/product/)
3. Review workflow logs for specific errors

### Price scraping fails

**Possible causes:**
1. **CAPTCHA:** Amazon showing CAPTCHA (will retry next day)
2. **Invalid URL:** Check product URL format
3. **Product unavailable:** Product might be out of stock
4. **Selector changed:** Amazon may have updated their HTML (need to update scraper.py)

**Debug:**
1. Check screenshots in `screenshots/` folder
2. Review workflow logs for specific errors
3. Test locally with `--dry-run` to see detailed output

## Maintenance

### Weekly

- Review GitHub Actions runs for any failures
- Check email inbox for alerts

### Monthly

- Update dependencies for security patches:
  ```bash
  uv pip install --upgrade playwright beautifulsoup4 python-dotenv pytz
  ```

### As Needed

- Add/remove products in `data/products.json`
- Rotate Gmail app password (good security practice every 6-12 months)

## Support

For issues or questions:
1. Check the [README.md](README.md) troubleshooting section
2. Review GitHub Actions workflow logs
3. Test locally with `--dry-run` flag for detailed output
4. Check the screenshots in the repository for visual debugging

## Next Steps

After setup is complete:

1. **Wait for daily run** - The workflow runs at 2:00 AM UTC
2. **Monitor email** - You'll receive alerts only for all-time lows
3. **Review history** - Check `data/price_history.json` for tracked prices
4. **Add more products** - Edit `data/products.json` anytime

Enjoy automated price tracking! 🎯
