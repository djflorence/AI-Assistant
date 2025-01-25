import feedparser
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
from bs4 import BeautifulSoup
import threading
import time

@dataclass
class NewsItem:
    title: str
    source: str
    summary: str
    link: str
    published: str
    category: str

class RSSService:
    """Service for fetching and managing RSS news feeds"""
    
    def __init__(self):
        self.feeds = {
            'technology': [
                'https://feeds.feedburner.com/TechCrunch/',
                'https://www.wired.com/feed/rss',
                'https://www.theverge.com/rss/index.xml'
            ],
            'world': [
                'https://rss.nytimes.com/services/xml/rss/nyt/World.xml',
                'https://feeds.bbci.co.uk/news/world/rss.xml',
                'https://www.reuters.com/feed/world/'
            ],
            'science': [
                'https://www.sciencedaily.com/rss/all.xml',
                'https://rss.nationalgeographic.com/science',
                'https://www.newscientist.com/feed/home/'
            ],
            'business': [
                'https://feeds.bloomberg.com/markets/news.rss',
                'https://www.forbes.com/business/feed/',
                'https://rss.nytimes.com/services/xml/rss/nyt/Business.xml'
            ]
        }
        
        self.cache = {}
        self.cache_duration = 1800  # 30 minutes
        self.last_update = {}
        self.update_thread = None
        self.running = False
        
    def start_auto_update(self):
        """Start background thread for automatic feed updates"""
        if not self.update_thread:
            self.running = True
            self.update_thread = threading.Thread(target=self._auto_update_feeds)
            self.update_thread.daemon = True
            self.update_thread.start()
    
    def stop_auto_update(self):
        """Stop the background update thread"""
        self.running = False
        if self.update_thread:
            self.update_thread.join()
            self.update_thread = None
    
    def _auto_update_feeds(self):
        """Background task to update feeds periodically"""
        while self.running:
            self.update_all_feeds()
            time.sleep(self.cache_duration)
    
    def update_all_feeds(self):
        """Update all feed categories"""
        for category in self.feeds:
            self.get_news(category, force_update=True)
    
    def get_news(self, category: str = 'technology', force_update: bool = False) -> List[NewsItem]:
        """Get news items for a specific category"""
        category = category.lower()
        current_time = time.time()
        
        # Check if we need to update
        if not force_update and category in self.cache:
            last_update = self.last_update.get(category, 0)
            if current_time - last_update < self.cache_duration:
                return self.cache[category]
        
        news_items = []
        for feed_url in self.feeds.get(category, []):
            try:
                feed = feedparser.parse(feed_url)
                source = feed.feed.get('title', feed_url)
                
                for entry in feed.entries[:5]:  # Get top 5 items from each feed
                    try:
                        # Clean up the summary by removing HTML tags
                        summary_text = entry.get('summary', '')
                        if summary_text and isinstance(summary_text, str):
                            # Handle potential HTML content
                            if '<' in summary_text and '>' in summary_text:
                                summary = BeautifulSoup(summary_text, 'html.parser').get_text(separator=' ', strip=True)
                            else:
                                summary = summary_text.strip()
                        else:
                            summary = "No summary available"
                        summary = summary[:200] + '...' if len(summary) > 200 else summary
                        
                        news_item = NewsItem(
                            title=entry.get('title', 'No title'),
                            source=source,
                            summary=summary,
                            link=entry.get('link', ''),
                            published=entry.get('published', ''),
                            category=category
                        )
                        news_items.append(news_item)
                    except Exception as e:
                        logging.error(f"Error processing entry from {feed_url}: {str(e)}")
                        continue
                        
            except Exception as e:
                logging.error(f"Error fetching feed {feed_url}: {str(e)}")
                continue
        
        # Sort by most recent
        news_items.sort(key=lambda x: x.published, reverse=True)
        
        # Keep only top 10 items
        news_items = news_items[:10]
        
        # Update cache
        self.cache[category] = news_items
        self.last_update[category] = current_time
        
        return news_items
    
    def get_available_categories(self) -> List[str]:
        """Get list of available news categories"""
        return list(self.feeds.keys())
    
    def get_summary_for_voice(self, category: str = 'technology', num_items: int = 3) -> str:
        """Get a voice-friendly summary of top news items"""
        news_items = self.get_news(category)[:num_items]
        
        if not news_items:
            return f"Sorry, I couldn't find any {category} news at the moment."
        
        summary = f"Here are the top {num_items} {category} news stories:\n\n"
        
        for i, item in enumerate(news_items, 1):
            summary += f"{i}. {item.title}\n"
            summary += f"From {item.source}. {item.summary}\n\n"
        
        return summary
    
    def search_news(self, query: str) -> List[NewsItem]:
        """Search for news items across all categories"""
        query = query.lower()
        results = []
        
        # Search through all categories
        for category in self.feeds.keys():
            items = self.get_news(category)
            for item in items:
                if (query in item.title.lower() or 
                    query in item.summary.lower()):
                    results.append(item)
        
        # Sort by relevance (simple matching score)
        results.sort(key=lambda x: 
            x.title.lower().count(query) * 2 +  # Title matches count more
            x.summary.lower().count(query),
            reverse=True
        )
        
        return results[:10]  # Return top 10 matches
