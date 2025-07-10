"""
DeepSeek API Client for AI Content Generation
Handles communication with DeepSeek API for content generation and processing.
"""

import requests
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from .config import DEEPSEEK_API_KEY, DEEPSEEK_API_URL, DEFAULT_LANGUAGE
from .prompts import (
    HISTORICAL_EVENT_PROMPT_SL, HISTORICAL_EVENT_PROMPT_EN,
    NEWS_SUMMARY_PROMPT_SL, NEWS_SUMMARY_PROMPT_EN,
    RELEVANCE_SCORE_PROMPT, TRANSLATION_PROMPT_TO_SL, TRANSLATION_PROMPT_TO_EN,
    SYSTEM_MESSAGES, DEFAULT_CLUB_INTERESTS, TEMPERATURE_SETTINGS, MAX_TOKEN_SETTINGS
)

logger = logging.getLogger(__name__)

class DeepSeekClient:
    """Client for interacting with DeepSeek AI API"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or DEEPSEEK_API_KEY
        self.api_url = DEEPSEEK_API_URL
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        })
        
        if not self.api_key:
            logger.warning("DeepSeek API key not provided. AI features will be disabled.")
    
    def _make_request(self, messages: List[Dict], model: str = "deepseek-chat", 
                     temperature: float = 0.7, max_tokens: int = 500) -> Optional[str]:
        """Make a request to DeepSeek API"""
        
        if not self.api_key:
            logger.error("DeepSeek API key not configured")
            return None
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }
        
        try:
            response = self.session.post(self.api_url, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            return result['choices'][0]['message']['content']
            
        except requests.exceptions.RequestException as e:
            logger.error(f"DeepSeek API request failed: {e}")
            return None
        except (KeyError, IndexError) as e:
            logger.error(f"Invalid response format from DeepSeek API: {e}")
            return None
    
    def generate_historical_event(self, date: str, language: str = 'sl') -> Optional[Dict]:
        """
        Generate a historical mountaineering event for a specific date
        
        Args:
            date (str): Date in MM-DD format
            language (str): Target language ('sl' for Slovenian, 'en' for English)
            
        Returns:
            Dict: Generated historical event or None if failed
        """
        
        month_day = date
        
        # Select appropriate prompt template based on language and format with date
        if language == 'sl':
            prompt = HISTORICAL_EVENT_PROMPT_SL
        else:
            prompt = HISTORICAL_EVENT_PROMPT_EN.format(date=month_day)
        
        messages = [
            {"role": "system", "content": SYSTEM_MESSAGES['historical_events']},
            {"role": "user", "content": prompt}
        ]
        
        response = self._make_request(
            messages, 
            temperature=TEMPERATURE_SETTINGS['historical_events'], 
            max_tokens=MAX_TOKEN_SETTINGS['historical_events']
        )
        
        if not response:
            return None
        
        try:
            # Clean response (remove any markdown formatting)
            clean_response = response.strip()
            if clean_response.startswith('```json'):
                clean_response = clean_response.replace('```json', '').replace('```', '').strip()
            
            event_data = json.loads(clean_response)
            
            # Add metadata
            event_data.update({
                'date': date,
                'language': language,
                'source': 'AI-generated',
                'generated_at': datetime.utcnow().isoformat()
            })
            
            logger.info(f"Generated historical event for {date}: {event_data.get('title', 'Unknown')}")
            return event_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Raw response: {response}")
            return None
    
    def summarize_news_article(self, title: str, content: str, 
                              language: str = 'sl', max_length: int = 150) -> Optional[str]:
        """
        Summarize a news article in the target language
        
        Args:
            title (str): Article title
            content (str): Article content
            language (str): Target language
            max_length (int): Maximum summary length
            
        Returns:
            str: Summarized content or None if failed
        """
        
        # Select appropriate prompt template and format with data
        if language == 'sl':
            prompt = NEWS_SUMMARY_PROMPT_SL.format(
                max_length=max_length,
                title=title,
                content=content[:2000]
            )
        else:
            prompt = NEWS_SUMMARY_PROMPT_EN.format(
                max_length=max_length,
                title=title,
                content=content[:2000]
            )
        
        messages = [
            {"role": "system", "content": SYSTEM_MESSAGES['news_summary']},
            {"role": "user", "content": prompt}
        ]
        
        response = self._make_request(
            messages, 
            temperature=TEMPERATURE_SETTINGS['news_summary'], 
            max_tokens=MAX_TOKEN_SETTINGS['news_summary']
        )
        
        if response and len(response) <= max_length + 50:  # Allow small buffer
            logger.info(f"Summarized article: {title[:50]}...")
            return response.strip()
        
        return None
    
    def calculate_relevance_score(self, title: str, content: str, 
                                 club_interests: List[str] = None) -> float:
        """
        Calculate relevance score for an article (1-10)
        
        Args:
            title (str): Article title
            content (str): Article content  
            club_interests (List[str]): Specific club interests
            
        Returns:
            float: Relevance score from 1.0 to 10.0
        """
        
        interests = club_interests or DEFAULT_CLUB_INTERESTS
        
        prompt = RELEVANCE_SCORE_PROMPT.format(
            interests=', '.join(interests),
            title=title,
            content=content[:1000]
        )
        
        messages = [
            {"role": "system", "content": SYSTEM_MESSAGES['relevance_score']},
            {"role": "user", "content": prompt}
        ]
        
        response = self._make_request(
            messages, 
            temperature=TEMPERATURE_SETTINGS['relevance_score'], 
            max_tokens=MAX_TOKEN_SETTINGS['relevance_score']
        )
        
        if response:
            try:
                score = float(response.strip())
                if 1.0 <= score <= 10.0:
                    logger.info(f"Calculated relevance score {score} for: {title[:50]}...")
                    return score
            except ValueError:
                pass
        
        # Default score if AI fails
        logger.warning(f"Failed to calculate relevance score for: {title[:50]}...")
        return 5.0
    
    def translate_content(self, text: str, target_language: str = 'sl') -> Optional[str]:
        """
        Translate content to target language
        
        Args:
            text (str): Text to translate
            target_language (str): Target language code
            
        Returns:
            str: Translated text or None if failed
        """
        
        # Select appropriate prompt template and format with text
        if target_language == 'sl':
            prompt = TRANSLATION_PROMPT_TO_SL.format(text=text)
        else:
            prompt = TRANSLATION_PROMPT_TO_EN.format(text=text)
        
        messages = [
            {"role": "system", "content": SYSTEM_MESSAGES['translation']},
            {"role": "user", "content": prompt}
        ]
        
        response = self._make_request(
            messages, 
            temperature=TEMPERATURE_SETTINGS['translation'], 
            max_tokens=MAX_TOKEN_SETTINGS['translation']
        )
        
        if response:
            logger.info(f"Translated text to {target_language}")
            return response.strip()
        
        return None
    
    def is_available(self) -> bool:
        """Check if DeepSeek API is available and configured"""
        return bool(self.api_key)
    
    def test_connection(self) -> bool:
        """Test connection to DeepSeek API"""
        
        if not self.api_key:
            return False
        
        test_messages = [
            {"role": "user", "content": "Hello, respond with just 'OK' if you can hear me."}
        ]
        
        response = self._make_request(test_messages, max_tokens=5)
        return response is not None