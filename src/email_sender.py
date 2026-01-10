import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from pathlib import Path
from typing import Optional

from src.timezone_utils import parse_timestamp
from src.config import Product
from src.price_tracker import PriceStats
from src.logger import get_logger


PROJECT_ROOT = Path(__file__).parent.parent
logger = get_logger()


class EmailSender:
    """Handles email notifications via Gmail SMTP."""

    def __init__(self, gmail_address: str, gmail_app_password: str):
        self.gmail_address = gmail_address
        self.gmail_app_password = gmail_app_password
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587

    def _format_timestamp(self, iso_timestamp: str) -> str:
        """Convert timestamp to Sydney time for display."""
        try:
            sydney_time = parse_timestamp(iso_timestamp)
            return sydney_time.strftime('%d %b %Y %I:%M %p %Z')
        except Exception:
            return iso_timestamp

    def _create_price_history_table(self, stats: PriceStats) -> str:
        """Create HTML table for last 7 days of price history."""
        if not stats.price_history_7_day:
            return "<p>No recent price history available.</p>"

        rows = []
        for i, record in enumerate(stats.price_history_7_day):
            # Calculate change from previous
            change_html = ""
            if i < len(stats.price_history_7_day) - 1:
                prev_price = stats.price_history_7_day[i + 1].price
                change = record.price - prev_price
                if abs(change) > 0.01:
                    color = "green" if change < 0 else "red"
                    symbol = "▼" if change < 0 else "▲"
                    change_html = f'<span style="color: {color};">{symbol} ${abs(change):.2f}</span>'
                else:
                    change_html = '<span style="color: #999;">—</span>'

            formatted_date = self._format_timestamp(record.timestamp)

            rows.append(f"""
                <tr>
                    <td>{formatted_date}</td>
                    <td style="font-weight: bold;">${record.price:.2f}</td>
                    <td>{change_html}</td>
                </tr>
            """)

        return f"""
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
            <thead>
                <tr style="background-color: #f5f5f5;">
                    <th style="padding: 10px; text-align: left; border-bottom: 2px solid #ddd;">Date</th>
                    <th style="padding: 10px; text-align: left; border-bottom: 2px solid #ddd;">Price</th>
                    <th style="padding: 10px; text-align: left; border-bottom: 2px solid #ddd;">Change</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
        """

    def create_email_content(self, product: Product, stats: PriceStats) -> str:
        """Generate HTML email content for all-time low alert."""
        price_history_table = self._create_price_history_table(stats)

        avg_30_day_html = ""
        if stats.avg_30_day:
            avg_30_day_html = f"""
            <p><strong>30-day average:</strong> ${stats.avg_30_day:.2f}</p>
            """

        savings_html = ""
        if stats.savings_percentage > 0:
            savings_html = f'<p style="color: #666;">Previous low: ${stats.previous_low:.2f} ({stats.savings_percentage:.1f}% cheaper now!)</p>'

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f9f9f9;
        }}
        .container {{
            background-color: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .header {{
            background: linear-gradient(135deg, #ff9900 0%, #ff7700 100%);
            color: white;
            padding: 30px 20px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 28px;
        }}
        .content {{
            padding: 30px 20px;
        }}
        .product-name {{
            font-size: 22px;
            color: #333;
            margin-bottom: 15px;
        }}
        .all-time-low {{
            background: #e3f2e1;
            border-left: 4px solid #4CAF50;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
        }}
        .price-badge {{
            font-size: 42px;
            color: #B12704;
            font-weight: bold;
            margin: 15px 0;
        }}
        .product-image {{
            max-width: 100%;
            border: 1px solid #ddd;
            border-radius: 4px;
            margin: 20px 0;
        }}
        .cta-button {{
            display: inline-block;
            background: #ff9900;
            color: white;
            padding: 14px 28px;
            text-decoration: none;
            border-radius: 4px;
            font-weight: bold;
            margin: 20px 0;
        }}
        .cta-button:hover {{
            background: #ff7700;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎉 All-Time Low Price Alert!</h1>
        </div>

        <div class="content">
            <h2 class="product-name">{product.name}</h2>

            <div class="all-time-low">
                <strong>🏆 New All-Time Low Detected!</strong><br>
                This is the lowest price ever recorded for this product.
            </div>

            <div class="price-badge">AUD ${stats.current_price:.2f}</div>
            {savings_html}

            <img src="cid:product_screenshot" alt="{product.name}" class="product-image" />

            <h3>Price History (Last 7 Days)</h3>
            {price_history_table}

            {avg_30_day_html}

            <p><strong>Checked:</strong> {self._format_timestamp(stats.current_timestamp)}</p>

            <div style="text-align: center;">
                <a href="{product.url}" class="cta-button">View on Amazon AU →</a>
            </div>
        </div>

        <div class="footer">
            Automated by Watch-Amazon-Price<br>
            Prices checked daily at 2:00 AM UTC
        </div>
    </div>
</body>
</html>
        """

        return html.strip()

    def send_email(
        self,
        to: str,
        subject: str,
        html_content: str,
        screenshot_path: Optional[str] = None
    ) -> bool:
        """Send email via Gmail SMTP."""
        try:
            # Create message
            msg = MIMEMultipart('related')
            msg['From'] = self.gmail_address
            msg['To'] = to
            msg['Subject'] = subject

            # Attach HTML content
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)

            # Attach screenshot if provided
            if screenshot_path:
                full_path = PROJECT_ROOT / screenshot_path
                if full_path.exists():
                    with open(full_path, 'rb') as f:
                        img_data = f.read()
                        image = MIMEImage(img_data, name=full_path.name)
                        image.add_header('Content-ID', '<product_screenshot>')
                        image.add_header('Content-Disposition', 'inline', filename=full_path.name)
                        msg.attach(image)
                else:
                    logger.warning(f"Screenshot not found: {full_path}")

            # Connect to Gmail SMTP server
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.gmail_address, self.gmail_app_password)
                server.send_message(msg)

            logger.info(f"✓ Email sent to {to}: {subject}")
            return True

        except Exception as e:
            logger.error(f"✗ Failed to send email: {e}")
            return False

    def create_batch_email_content(self, products_data: list[tuple[Product, PriceStats]]) -> str:
        """Generate HTML email content for multiple all-time low alerts."""
        products_html = []

        for i, (product, stats) in enumerate(products_data):
            savings_html = ""
            if stats.savings_percentage > 0:
                savings_html = f'<p style="color: #666; margin: 5px 0;">Previous low: ${stats.previous_low:.2f} ({stats.savings_percentage:.1f}% cheaper now!)</p>'

            avg_30_day_html = ""
            if stats.avg_30_day:
                avg_30_day_html = f'<p style="color: #666; margin: 5px 0;">30-day average: ${stats.avg_30_day:.2f}</p>'

            product_html = f"""
            <div style="border-bottom: 2px solid #eee; padding: 25px 0; {'' if i == len(products_data) - 1 else ''}">
                <h2 style="color: #333; margin-top: 0;">{product.name}</h2>

                <div style="background: #e3f2e1; border-left: 4px solid #4CAF50; padding: 12px; margin: 15px 0; border-radius: 4px;">
                    <strong>🏆 New All-Time Low!</strong>
                </div>

                <div style="font-size: 36px; color: #B12704; font-weight: bold; margin: 15px 0;">
                    AUD ${stats.current_price:.2f}
                </div>

                {savings_html}
                {avg_30_day_html}

                <p style="color: #666; margin: 10px 0;">
                    <strong>Checked:</strong> {self._format_timestamp(stats.current_timestamp)}
                </p>

                <div style="margin-top: 15px;">
                    <a href="{product.url}" style="display: inline-block; background: #ff9900; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; font-weight: bold;">
                        View on Amazon AU →
                    </a>
                </div>
            </div>
            """
            products_html.append(product_html)

        count = len(products_data)
        title = f"🎉 {count} Product{'s' if count > 1 else ''} Hit All-Time Low!"

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 700px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f9f9f9;
        }}
        .container {{
            background-color: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .header {{
            background: linear-gradient(135deg, #ff9900 0%, #ff7700 100%);
            color: white;
            padding: 30px 20px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 28px;
        }}
        .content {{
            padding: 30px 20px;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: 12px;
            background-color: #f5f5f5;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{title}</h1>
        </div>

        <div class="content">
            {''.join(products_html)}
        </div>

        <div class="footer">
            Automated by Watch-Amazon-Price<br>
            Prices checked daily at 2:00 AM UTC
        </div>
    </div>
</body>
</html>
        """

        return html.strip()

    def send_batch_all_time_low_alert(
        self,
        products_data: list[tuple[Product, PriceStats]],
        recipient: str
    ) -> bool:
        """Send consolidated all-time low price alert email for multiple products."""
        if not products_data:
            return False

        count = len(products_data)
        if count == 1:
            # If only one product, use the single product email format
            product, stats = products_data[0]
            return self.send_all_time_low_alert(product, stats, recipient)

        subject = f"🎉 {count} Products Hit All-Time Low!"
        html_content = self.create_batch_email_content(products_data)

        # Don't attach screenshots for batch emails (would be too many images)
        return self.send_email(
            to=recipient,
            subject=subject,
            html_content=html_content,
            screenshot_path=None
        )

    def send_all_time_low_alert(
        self,
        product: Product,
        stats: PriceStats,
        recipient: str
    ) -> bool:
        """Send all-time low price alert email."""
        subject = f"🎉 All-Time Low Price Alert: {product.name}"
        html_content = self.create_email_content(product, stats)

        # Get screenshot path from current price record
        screenshot_path = stats.price_history_7_day[0].screenshot if stats.price_history_7_day else None

        return self.send_email(
            to=recipient,
            subject=subject,
            html_content=html_content,
            screenshot_path=screenshot_path
        )
