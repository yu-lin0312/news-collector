import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class EmailNotifier:
    def __init__(self):
        self.sender = os.getenv('EMAIL_SENDER')
        self.password = os.getenv('EMAIL_PASSWORD')
        self.recipients = os.getenv('EMAIL_RECIPIENTS')

        # Clean up password (remove spaces if any)
        if self.password:
            self.password = self.password.replace(' ', '')

        if not self.sender or not self.password:
            print("Warning: EMAIL_SENDER or EMAIL_PASSWORD not set in .env")

    def generate_html_content(self, top10_data, daily_summary=None):
        """
        Generates a beautiful HTML email content from the news data.
        """
        today_str = datetime.now().strftime('%Y-%m-%d')
        
        # HTML Header & Style
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    background-color: #f4f4f4;
                    margin: 0;
                    padding: 0;
                }}
                .container {{
                    max-width: 600px;
                    margin: 20px auto;
                    background: #ffffff;
                    border-radius: 8px;
                    overflow: hidden;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                }}
                .header {{
                    background: #1a73e8;
                    color: white;
                    padding: 20px;
                    text-align: center;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 24px;
                }}
                .date {{
                    font-size: 14px;
                    opacity: 0.8;
                    margin-top: 5px;
                }}
                .summary-card {{
                    background: #e8f0fe;
                    border-left: 4px solid #1a73e8;
                    margin: 20px;
                    padding: 15px;
                    border-radius: 4px;
                }}
                .summary-title {{
                    font-weight: bold;
                    color: #1a73e8;
                    margin-bottom: 8px;
                }}
                .news-list {{
                    padding: 0 20px 20px 20px;
                }}
                .news-item {{
                    border-bottom: 1px solid #eee;
                    padding: 15px 0;
                }}
                .news-item:last-child {{
                    border-bottom: none;
                }}
                .news-rank {{
                    font-weight: bold;
                    color: #1a73e8;
                    font-size: 14px;
                }}
                .news-title {{
                    font-size: 18px;
                    font-weight: bold;
                    margin: 5px 0;
                    display: block;
                    text-decoration: none;
                    color: #202124;
                }}
                .news-title:hover {{
                    color: #1a73e8;
                }}
                .news-meta {{
                    font-size: 12px;
                    color: #5f6368;
                    margin-bottom: 8px;
                }}
                .category-tag {{
                    display: inline-block;
                    padding: 2px 6px;
                    border-radius: 4px;
                    background: #f1f3f4;
                    color: #5f6368;
                    font-size: 11px;
                    margin-left: 5px;
                }}
                .news-rundown {{
                    font-size: 14px;
                    color: #444;
                }}
                .footer {{
                    background: #f8f9fa;
                    padding: 20px;
                    text-align: center;
                    font-size: 12px;
                    color: #5f6368;
                    border-top: 1px solid #eee;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📡 AI News Radar</h1>
                    <div class="date">{today_str} Daily Briefing</div>
                </div>
        """

        # Daily Summary
        if daily_summary:
            html += f"""
                <div class="summary-card">
                    <div class="summary-title">今日重點總結</div>
                    <div>{daily_summary}</div>
                </div>
            """

        # News List
        html += '<div class="news-list">'
        
        for i, item in enumerate(top10_data):
            rank = i + 1
            title = item.get('title', 'No Title')
            url = item.get('url', '#')
            source = item.get('source', 'Unknown')
            category = item.get('ai_category', 'General')
            rundown = item.get('ai_rundown', 'No summary available.')
            
            html += f"""
                <div class="news-item">
                    <div class="news-rank">#{rank:02d}</div>
                    <a href="{url}" class="news-title" target="_blank">{title}</a>
                    <div class="news-meta">
                        {source}
                        <span class="category-tag">{category}</span>
                    </div>
                    <div class="news-rundown">{rundown}</div>
                </div>
            """
            
        html += """
                </div>
                <div class="footer">
                    Sent by AI News Collector • <a href="http://localhost:8501">View Dashboard</a>
                </div>
            </div>
        </body>
        </html>
        """
        return html

    def send_daily_briefing(self, top10_data, daily_summary=None):
        """
        Sends the daily briefing email.
        """
        if not self.sender or not self.password or not self.recipients:
            print("❌ Email configuration missing. Skipping notification.")
            return False

        try:
            # Prepare content
            html_content = self.generate_html_content(top10_data, daily_summary)
            today_str = datetime.now().strftime('%Y-%m-%d')
            subject = f"📡 AI News Briefing - {today_str}"

            # Create Message
            msg = MIMEMultipart()
            msg['From'] = self.sender
            msg['Subject'] = subject
            msg.attach(MIMEText(html_content, 'html'))

            # Parse Recipients
            recipient_list = [r.strip() for r in self.recipients.split(',') if r.strip()]
            msg['To'] = ", ".join(recipient_list)

            # Connect to SMTP (Gmail) - Using SSL (Port 465)
            print(f"Connecting to SMTP server (Gmail SSL)...")
            server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            # server.starttls() # No need for starttls with SMTP_SSL
            server.login(self.sender, self.password)
            
            # Send
            print(f"Sending email to {len(recipient_list)} recipients...")
            server.sendmail(self.sender, recipient_list, msg.as_string())
            server.quit()
            
            print("✅ Email notification sent successfully!")
            return True

        except Exception as e:
            print(f"❌ Failed to send email: {e}")
            return False

if __name__ == "__main__":
    # Test execution
    notifier = EmailNotifier()
    
    # Mock Data
    mock_data = [
        {
            "title": "OpenAI Announces GPT-5 Testing Phase",
            "url": "https://example.com/gpt5",
            "source": "TechCrunch",
            "ai_category": "Breaking",
            "ai_rundown": "OpenAI has officially started internal testing for GPT-5, promising significant reasoning improvements."
        },
        {
            "title": "Google DeepMind Reveals New Robotics AI",
            "url": "https://example.com/robotics",
            "source": "Google Blog",
            "ai_category": "Research",
            "ai_rundown": "A new foundation model for robotics control has been released, enabling more general-purpose tasks."
        }
    ]
    
    print("Running test email...")
    notifier.send_daily_briefing(mock_data, "Today is a big day for AI with major releases from OpenAI and Google.")
