#!/usr/bin/env python3
"""
Daily Racing News & Betting Moves Email
Scrapes UK racing news, market movers, and relevant content
Sends formatted email at 7am daily
"""

import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import time
import re
from typing import List, Dict
import json

class RacingNewsScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.news_items = []
        self.market_movers = []
        self.entries = []
        
    def get_article_content(self, url):
        """Fetch full article content and create a summary"""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
                script.decompose()
            
            # Try to find article content
            content = None
            paragraphs = []
            
            # Common article content selectors - try in order
            selectors = [
                'article',
                'div[class*="article-content"]',
                'div[class*="article-body"]',
                'div[class*="entry-content"]',
                'div[class*="post-content"]',
                'div[class*="content"]',
                'main'
            ]
            
            for selector in selectors:
                content_div = soup.select_one(selector)
                if content_div:
                    # Get all paragraphs
                    paragraphs = content_div.find_all('p')
                    if len(paragraphs) >= 2:
                        break
            
            if not paragraphs:
                # Fallback - get all p tags
                paragraphs = soup.find_all('p')
            
            # Extract text from first 5 paragraphs
            text_parts = []
            for p in paragraphs[:5]:
                text = p.get_text(strip=True)
                if len(text) > 30:  # Only substantial paragraphs
                    text_parts.append(text)
                if len(text_parts) >= 3:  # Get up to 3 good paragraphs
                    break
            
            if text_parts:
                # Join and create summary (first 400 chars from article)
                full_text = ' '.join(text_parts)
                # Clean up whitespace
                full_text = ' '.join(full_text.split())
                
                # Create a summary - take first 300-400 characters
                if len(full_text) > 400:
                    summary = full_text[:400].rsplit('.', 1)[0] + '.'
                else:
                    summary = full_text
                
                return summary
            
            return None
            
        except Exception as e:
            return None
    
    def get_sporting_life_news(self):
        """Scrape Sporting Life racing news"""
        try:
            url = "https://www.sportinglife.com/racing/news"
            response = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            articles = soup.find_all('article', limit=5)
            for article in articles:
                try:
                    headline = article.find('h3') or article.find('h2')
                    link = article.find('a')
                    
                    if headline and link:
                        article_url = 'https://www.sportinglife.com' + link.get('href') if link.get('href').startswith('/') else link.get('href')
                        
                        # Try to get summary from article preview first
                        summary = None
                        preview = article.find('p')
                        if preview:
                            summary = preview.get_text(strip=True)
                        
                        # If no preview, fetch the full article
                        if not summary or len(summary) < 100:
                            time.sleep(0.5)  # Be polite to the server
                            fetched_summary = self.get_article_content(article_url)
                            if fetched_summary:
                                summary = fetched_summary
                        
                        self.news_items.append({
                            'source': 'Sporting Life',
                            'headline': headline.get_text(strip=True),
                            'url': article_url,
                            'summary': summary
                        })
                except Exception as e:
                    continue
                    
            print(f"✓ Sporting Life: {len([n for n in self.news_items if n['source'] == 'Sporting Life'])} articles")
        except Exception as e:
            print(f"✗ Sporting Life failed: {e}")
    
    def get_attheraces_news(self):
        """Scrape At The Races news"""
        try:
            url = "https://www.attheraces.com/news"
            response = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for news articles
            articles = soup.find_all(['article', 'div'], class_=re.compile('news|article'), limit=5)
            for article in articles:
                try:
                    headline = article.find(['h2', 'h3', 'h4'])
                    link = article.find('a')
                    
                    if headline and link:
                        href = link.get('href', '')
                        full_url = href if href.startswith('http') else f"https://www.attheraces.com{href}"
                        
                        # Try to get summary from preview
                        summary = None
                        preview = article.find('p')
                        if preview:
                            summary = preview.get_text(strip=True)
                        
                        # If no preview, fetch the article
                        if not summary or len(summary) < 100:
                            time.sleep(0.5)
                            fetched_summary = self.get_article_content(full_url)
                            if fetched_summary:
                                summary = fetched_summary
                        
                        self.news_items.append({
                            'source': 'At The Races',
                            'headline': headline.get_text(strip=True),
                            'url': full_url,
                            'summary': summary
                        })
                except Exception as e:
                    continue
                    
            print(f"✓ At The Races: {len([n for n in self.news_items if n['source'] == 'At The Races'])} articles")
        except Exception as e:
            print(f"✗ At The Races failed: {e}")
    
    def get_racing_post_headlines(self):
        """Scrape Racing Post public headlines (no login required)"""
        try:
            url = "https://www.racingpost.com/news"
            response = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Racing Post uses various article containers
            articles = soup.find_all(['article', 'div'], limit=8)
            for article in articles:
                try:
                    headline = article.find(['h2', 'h3', 'h4'])
                    link = article.find('a')
                    
                    if headline and link:
                        href = link.get('href', '')
                        # Skip navigation links
                        if '/news/' in href or '/horses/' in href:
                            full_url = href if href.startswith('http') else f"https://www.racingpost.com{href}"
                            
                            # Try to get summary from preview
                            summary = None
                            preview = article.find('p')
                            if preview:
                                summary = preview.get_text(strip=True)
                            
                            # If no preview, fetch the article  
                            if not summary or len(summary) < 100:
                                time.sleep(0.5)
                                fetched_summary = self.get_article_content(full_url)
                                if fetched_summary:
                                    summary = fetched_summary
                            
                            self.news_items.append({
                                'source': 'Racing Post',
                                'headline': headline.get_text(strip=True),
                                'url': full_url,
                                'summary': summary
                            })
                except Exception as e:
                    continue
                    
            print(f"✓ Racing Post: {len([n for n in self.news_items if n['source'] == 'Racing Post'])} articles")
        except Exception as e:
            print(f"✗ Racing Post failed: {e}")
    
    def get_timeform_news(self):
        """Scrape Timeform news"""
        try:
            url = "https://www.timeform.com/horse-racing/news"
            response = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            articles = soup.find_all(['article', 'div'], class_=re.compile('article|news'), limit=5)
            for article in articles:
                try:
                    headline = article.find(['h2', 'h3', 'h4'])
                    link = article.find('a')
                    
                    if headline and link:
                        href = link.get('href', '')
                        full_url = href if href.startswith('http') else f"https://www.timeform.com{href}"
                        
                        # Try to get summary from preview
                        summary = None
                        preview = article.find('p')
                        if preview:
                            summary = preview.get_text(strip=True)
                        
                        # If no preview, fetch the article
                        if not summary or len(summary) < 100:
                            time.sleep(0.5)
                            fetched_summary = self.get_article_content(full_url)
                            if fetched_summary:
                                summary = fetched_summary
                        
                        self.news_items.append({
                            'source': 'Timeform',
                            'headline': headline.get_text(strip=True),
                            'url': full_url,
                            'summary': summary
                        })
                except Exception as e:
                    continue
                    
            print(f"✓ Timeform: {len([n for n in self.news_items if n['source'] == 'Timeform'])} articles")
        except Exception as e:
            print(f"✗ Timeform failed: {e}")
    
    def get_oddschecker_movers(self):
        """Get market movers from Oddschecker"""
        try:
            # Try to get horse racing odds movers
            url = "https://www.oddschecker.com/horse-racing"
            response = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for odds or movers sections
            # Note: Oddschecker structure changes frequently, this is a best-effort approach
            movers_section = soup.find_all(['div', 'table'], class_=re.compile('mover|odds|market'), limit=10)
            
            for section in movers_section:
                try:
                    horse_name = section.find(['span', 'div'], class_=re.compile('runner|horse|selection'))
                    odds = section.find(['span', 'div'], class_=re.compile('odd|price'))
                    
                    if horse_name and odds:
                        self.market_movers.append({
                            'horse': horse_name.get_text(strip=True),
                            'odds': odds.get_text(strip=True),
                            'source': 'Oddschecker'
                        })
                except Exception as e:
                    continue
            
            if self.market_movers:
                print(f"✓ Oddschecker: {len(self.market_movers)} movers found")
            else:
                print("✓ Oddschecker: No movers data (may need manual check)")
        except Exception as e:
            print(f"✗ Oddschecker failed: {e}")
    
    def get_todays_racing(self):
        """Get today's race meetings info"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            
            # Try Racing Post race cards
            url = f"https://www.racingpost.com/racecards/{today}"
            response = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for race meetings
            meetings = soup.find_all(['div', 'section'], class_=re.compile('meeting|course|racecourse'), limit=10)
            
            for meeting in meetings:
                try:
                    course_name = meeting.find(['h2', 'h3', 'h4', 'span'])
                    if course_name:
                        course_text = course_name.get_text(strip=True)
                        if course_text and len(course_text) > 2:
                            self.entries.append({
                                'type': 'Meeting',
                                'course': course_text,
                                'info': 'Racing Today'
                            })
                except Exception as e:
                    continue
            
            if self.entries:
                print(f"✓ Today's Racing: {len(self.entries)} meetings found")
            else:
                print("✓ Today's Racing: Data available on Racing Post website")
        except Exception as e:
            print(f"✗ Today's Racing failed: {e}")
    
    def format_email_html(self):
        """Format all collected data into HTML email"""
        today = datetime.now().strftime("%A, %B %d, %Y")
        
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
                h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
                h2 {{ color: #34495e; margin-top: 30px; border-left: 4px solid #3498db; padding-left: 10px; }}
                .news-item {{ margin: 15px 0; padding: 10px; background: #f8f9fa; border-radius: 5px; }}
                .news-item h3 {{ margin: 0 0 5px 0; font-size: 16px; }}
                .source {{ color: #7f8c8d; font-size: 12px; font-weight: bold; }}
                .mover {{ padding: 8px; margin: 8px 0; background: #fff3cd; border-left: 3px solid #ffc107; }}
                .meeting {{ padding: 8px; margin: 8px 0; background: #d1ecf1; border-left: 3px solid #17a2b8; }}
                a {{ color: #3498db; text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
                .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #7f8c8d; font-size: 12px; }}
            </style>
        </head>
        <body>
            <h1>🏇 Daily Racing Briefing</h1>
            <p><strong>{today}</strong></p>
        """
        
        # Today's Racing Meetings
        if self.entries:
            html += "<h2>📅 Today's Racing</h2>"
            for entry in self.entries[:10]:
                html += f"""
                <div class="meeting">
                    <strong>{entry.get('course', 'Unknown')}</strong> - {entry.get('info', '')}
                </div>
                """
        else:
            html += "<h2>📅 Today's Racing</h2>"
            html += "<p>Check <a href='https://www.racingpost.com/racecards'>Racing Post Racecards</a> for today's meetings</p>"
        
        # Market Movers
        if self.market_movers:
            html += "<h2>📈 Market Movers</h2>"
            for mover in self.market_movers[:15]:
                html += f"""
                <div class="mover">
                    <strong>{mover.get('horse', 'Unknown')}</strong> - {mover.get('odds', '')} 
                    <span class="source">({mover.get('source', '')})</span>
                </div>
                """
        else:
            html += "<h2>📈 Market Movers</h2>"
            html += "<p>Check <a href='https://www.oddschecker.com/horse-racing'>Oddschecker</a> and <a href='https://www.betfair.com/exchange/plus/horse-racing'>Betfair</a> for latest market moves</p>"
        
        # News Headlines
        if self.news_items:
            html += "<h2>📰 Racing News</h2>"
            
            # Remove duplicates based on headline similarity
            unique_news = []
            seen_headlines = set()
            
            for item in self.news_items:
                headline_key = item['headline'][:50].lower()
                if headline_key not in seen_headlines:
                    seen_headlines.add(headline_key)
                    unique_news.append(item)
            
            for item in unique_news[:15]:
                summary_html = ""
                if item.get('summary'):
                    summary_html = f"<p style='color: #555; font-size: 14px; margin: 5px 0;'><strong>TLDR:</strong> {item['summary']}</p>"
                
                html += f"""
                <div class="news-item">
                    <h3><a href="{item['url']}" target="_blank">{item['headline']}</a></h3>
                    {summary_html}
                    <span class="source">{item['source']}</span>
                </div>
                """
        else:
            html += "<h2>📰 Racing News</h2>"
            html += "<p>No news items scraped. Check sources manually:</p>"
            html += "<ul>"
            html += "<li><a href='https://www.racingpost.com/news'>Racing Post</a></li>"
            html += "<li><a href='https://www.sportinglife.com/racing/news'>Sporting Life</a></li>"
            html += "<li><a href='https://www.timeform.com/horse-racing/news'>Timeform</a></li>"
            html += "</ul>"
        
        # Useful Links
        html += """
        <h2>🔗 Quick Links</h2>
        <ul>
            <li><a href="https://www.racingpost.com/racecards">Racing Post - Today's Racecards</a></li>
            <li><a href="https://www.sportinglife.com/racing/results">Sporting Life - Results</a></li>
            <li><a href="https://www.oddschecker.com/horse-racing">Oddschecker - Racing Odds</a></li>
            <li><a href="https://www.betfair.com/exchange/plus/horse-racing">Betfair Exchange</a></li>
            <li><a href="https://www.timeform.com/horse-racing">Timeform</a></li>
            <li><a href="https://twitter.com/search?q=%23HorseRacing&f=live">Twitter - #HorseRacing</a></li>
        </ul>
        
        <div class="footer">
            <p>Generated automatically for @getyourtipsout</p>
            <p>Data sources: Racing Post, Sporting Life, At The Races, Timeform, Oddschecker</p>
        </div>
        </body>
        </html>
        """
        
        return html
    
    def send_email(self, html_content):
        """Send email via Gmail SMTP"""
        try:
            sender_email = "davidpotter2550@gmail.com"
            app_password = "ywaikzhpfzueroai"
            recipients = ["davidpotter255@hotmail.com", "getyourtipsout@hotmail.co.uk"]
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"🏇 Daily Racing Briefing - {datetime.now().strftime('%d/%m/%Y')}"
            msg['From'] = sender_email
            msg['To'] = ", ".join(recipients)
            
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(sender_email, app_password)
                server.send_message(msg)
            
            print(f"\n✓ Email sent successfully to {', '.join(recipients)}")
            return True
            
        except Exception as e:
            print(f"\n✗ Email failed: {e}")
            return False
    
    def run(self):
        """Main execution"""
        print("=" * 60)
        print("DAILY RACING NEWS SCRAPER")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # Scrape all sources
        print("\n📊 Scraping news sources...")
        self.get_racing_post_headlines()
        time.sleep(1)
        self.get_sporting_life_news()
        time.sleep(1)
        self.get_attheraces_news()
        time.sleep(1)
        self.get_timeform_news()
        
        print("\n📈 Checking market movers...")
        self.get_oddschecker_movers()
        
        print("\n🏇 Getting today's racing...")
        self.get_todays_racing()
        
        # Generate and send email
        print("\n📧 Generating email...")
        html_content = self.format_email_html()
        
        print(f"\nCollected:")
        print(f"  • News items: {len(self.news_items)}")
        print(f"  • Market movers: {len(self.market_movers)}")
        print(f"  • Race meetings: {len(self.entries)}")
        
        success = self.send_email(html_content)
        
        print("=" * 60)
        print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        return success

if __name__ == "__main__":
    scraper = RacingNewsScraper()
    scraper.run()
