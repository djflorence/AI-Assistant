import requests
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

class RealtimeService:
    """
    A comprehensive service for fetching real-time data from various APIs.
    Supports multiple data types like weather, movies, stocks, news, etc.
    """
    
    def __init__(self):
        self.api_keys = {
            'openweather': os.getenv('OPENWEATHER_API_KEY'),
            'tmdb': os.getenv('TMDB_API_KEY'),
            'newsapi': os.getenv('NEWS_API_KEY'),
            'alphavantage': os.getenv('ALPHAVANTAGE_API_KEY')
        }
        
        self.base_urls = {
            'weather': "http://api.openweathermap.org/data/2.5/weather",
            'movies': "https://api.themoviedb.org/3",
            'news': "https://newsapi.org/v2/top-headlines",
            'stocks': "https://www.alphavantage.co/query"
        }
        
        # Cache for storing API responses
        self.cache = {}
        self.cache_duration = 300  # 5 minutes default cache duration
    
    def get_weather(self, city: str = "Boston", country_code: str = "US") -> Dict[str, Any]:
        """Get current weather data for a location"""
        cache_key = f"weather_{city}_{country_code}"
        
        # Check cache first
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]
            
        try:
            # Clean up city name
            city = city.strip().replace(',', ' ').replace('  ', ' ')
            
            params = {
                'q': f"{city},{country_code}",
                'appid': self.api_keys['openweather'],
                'units': 'imperial'
            }
            
            data = self._make_api_request('weather', params)
            
            formatted_data = {
                'temperature': round(data['main']['temp']),
                'feels_like': round(data['main']['feels_like']),
                'condition': data['weather'][0]['main'],
                'description': data['weather'][0]['description'].capitalize(),
                'humidity': data['main']['humidity'],
                'wind_speed': round(data['wind']['speed']),
                'location': data['name'],
                'timestamp': datetime.now().strftime('%I:%M %p')
            }
            
            # Cache the result
            self._cache_response(cache_key, formatted_data)
            return formatted_data
            
        except requests.exceptions.HTTPError as e:
            logging.error(f"Weather API error: {str(e)}")
            if "city not found" in str(e).lower():
                return None
            raise
        except Exception as e:
            logging.error(f"Weather API error: {str(e)}")
            raise
    
    def get_movies(self, location: str = "Boston") -> Dict[str, Any]:
        """Get current movie showtimes and listings"""
        cache_key = f"movies_{location}"
        
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]
            
        try:
            params = {
                'api_key': self.api_keys['tmdb'],
                'region': 'US',
                'with_release_type': 3  # Theatrical release
            }
            
            data = self._make_api_request('movies/now_playing', params)
            
            movies = [{
                'title': movie['title'],
                'rating': movie['vote_average'],
                'release_date': movie['release_date'],
                'overview': movie['overview']
            } for movie in data.get('results', [])]
            
            formatted_data = {
                'location': location,
                'movies': movies,
                'timestamp': datetime.now().strftime('%I:%M %p')
            }
            
            self._cache_response(cache_key, formatted_data)
            return formatted_data
            
        except Exception as e:
            logging.error(f"Movie API error: {str(e)}")
            raise
    
    def get_news(self, category: str = "technology", country: str = "us") -> Dict[str, Any]:
        """Get latest news headlines"""
        cache_key = f"news_{category}_{country}"
        
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]
            
        try:
            params = {
                'apiKey': self.api_keys['newsapi'],
                'category': category,
                'country': country
            }
            
            data = self._make_api_request('news', params)
            
            articles = [{
                'title': article['title'],
                'source': article['source']['name'],
                'url': article['url'],
                'published': article['publishedAt']
            } for article in data.get('articles', [])]
            
            formatted_data = {
                'category': category,
                'country': country,
                'articles': articles,
                'timestamp': datetime.now().strftime('%I:%M %p')
            }
            
            self._cache_response(cache_key, formatted_data)
            return formatted_data
            
        except Exception as e:
            logging.error(f"News API error: {str(e)}")
            raise
    
    def get_stocks(self, symbol: str) -> Dict[str, Any]:
        """Get real-time stock data"""
        cache_key = f"stocks_{symbol}"
        
        if self._is_cache_valid(cache_key, duration=60):  # 1 minute cache for stocks
            return self.cache[cache_key]
            
        try:
            params = {
                'function': 'GLOBAL_QUOTE',
                'symbol': symbol,
                'apikey': self.api_keys['alphavantage']
            }
            
            data = self._make_api_request('stocks', params)
            quote = data.get('Global Quote', {})
            
            formatted_data = {
                'symbol': symbol,
                'price': quote.get('05. price'),
                'change': quote.get('09. change'),
                'change_percent': quote.get('10. change percent'),
                'timestamp': datetime.now().strftime('%I:%M %p')
            }
            
            self._cache_response(cache_key, formatted_data, duration=60)
            return formatted_data
            
        except Exception as e:
            logging.error(f"Stock API error: {str(e)}")
            raise
    
    def _make_api_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make an API request with error handling and rate limiting"""
        base_url = self.base_urls.get(endpoint.split('/')[0])
        if not base_url:
            raise ValueError(f"Unknown API endpoint: {endpoint}")
            
        url = f"{base_url}/{endpoint}" if '/' in endpoint else base_url
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()  # This will raise an HTTPError for bad responses
            data = response.json()
            
            # Check for API-specific error responses
            if endpoint == 'weather' and data.get('cod') != 200:
                error_msg = data.get('message', 'Unknown error')
                raise requests.exceptions.HTTPError(f"Weather API error: {error_msg}")
                
            return data
            
        except requests.exceptions.RequestException as e:
            logging.error(f"API request failed: {str(e)}")
            raise
    
    def _cache_response(self, key: str, data: Dict[str, Any], duration: Optional[int] = None) -> None:
        """Cache API response with timestamp"""
        self.cache[key] = {
            'data': data,
            'timestamp': datetime.now(),
            'duration': duration or self.cache_duration
        }
    
    def _is_cache_valid(self, key: str, duration: Optional[int] = None) -> bool:
        """Check if cached data is still valid"""
        if key not in self.cache:
            return False
            
        cache_entry = self.cache[key]
        cache_age = (datetime.now() - cache_entry['timestamp']).total_seconds()
        max_age = duration or cache_entry.get('duration', self.cache_duration)
        
        return cache_age < max_age
