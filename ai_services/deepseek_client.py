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
        
        if language == 'sl':
            prompt = f"""
            Poišči pomemben zgodovinski dogodek iz sveta alpinizma, planinarstva ali gorništva, 
            ki se je zgodil na današnji dan v zgodovini (poljubno leto).
            
            PREDNOSTNO vključi dogodke povezane s:
            - Slovenskim alpinizmom (Julijske Alpe, Kamniške Alpe, Triglav)
            - Slovenskimi alpinisti (Aleš Česen, Tomaž Humar, Silvo Karo, etc.)
            - Vzhodnimi Alpami in sosednjimi gorami
            - Zgodovino slovenskega gorništva in PZS
            
            Če ni slovenskega dogodka, poišči mednarodni dogodek.
            
            Odgovori SAMO v JSON formatu z naslednjimi polji:
            {{
                "year": leto_dogodka,
                "title": "kratek_naslov_v_slovenščini",
                "description": "opis_2_3_stavki_v_slovenščini", 
                "location": "lokacija",
                "people": ["ime1", "ime2"],
                "category": "first_ascent|tragedy|discovery|achievement|expedition"
            }}
            
            Pomembno: Odgovori SAMO z JSON, brez dodatnega besedila.
            """
        else:
            prompt = f"""
            Find an important historical event from mountaineering, alpinism or climbing 
            that happened on this day in history (any year).
            
            Respond ONLY in JSON format with these fields:
            {{
                "year": event_year,
                "title": "short_title_in_english",
                "description": "description_2_3_sentences_in_english",
                "location": "location", 
                "people": ["name1", "name2"],
                "category": "first_ascent|tragedy|discovery|achievement|expedition"
            }}
            
            Important: Respond ONLY with JSON, no additional text.
            """
        
        messages = [
            {"role": "system", "content": "You are an expert in mountaineering history. Always respond with valid JSON only."},
            {"role": "user", "content": prompt}
        ]
        
        response = self._make_request(messages, temperature=0.8, max_tokens=600)
        
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
        
        if language == 'sl':
            prompt = f"""
            Povzemi ta članek o alpinizmu/plezanju v slovenščini. 
            Povzetek naj bo kratek ({max_length} znakov), informativen in zanimiv za člane planinskega društva.
            
            Naslov: {title}
            Vsebina: {content[:2000]}
            
            Odgovori SAMO s povzetkom, brez dodatnega besedila.
            """
        else:
            prompt = f"""
            Summarize this mountaineering/climbing article in English.
            Keep it short ({max_length} characters), informative and interesting for mountaineering club members.
            
            Title: {title}
            Content: {content[:2000]}
            
            Respond ONLY with the summary, no additional text.
            """
        
        messages = [
            {"role": "system", "content": "You are an expert at summarizing mountaineering content."},
            {"role": "user", "content": prompt}
        ]
        
        response = self._make_request(messages, temperature=0.3, max_tokens=200)
        
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
        
        interests = club_interests or [
            'alpinizem', 'plezanje', 'gorništvo', 'varnost', 
            'oprema', 'julijske alpe', 'slovenija'
        ]
        
        prompt = f"""
        Oceni relevantnost tega članka za slovensko planinsko društvo na lestvici 1-10.
        
        Kriteriji:
        - 9-10: Zelo pomembno (varnost, lokalni dogodki, nova oprema)
        - 7-8: Pomembno (mednarodni alpinizem, tehnike)
        - 5-6: Zanimivo (splošno plezanje, potovanja)
        - 3-4: Manj relevantno (oddaljene lokacije, specifični športi)
        - 1-2: Ni relevantno
        
        Interesi društva: {', '.join(interests)}
        
        Naslov: {title}
        Vsebina: {content[:1000]}
        
        Odgovori SAMO s številko (npr. 7.5), brez dodatnega besedila.
        """
        
        messages = [
            {"role": "system", "content": "You are an expert at evaluating content relevance for mountaineering clubs."},
            {"role": "user", "content": prompt}
        ]
        
        response = self._make_request(messages, temperature=0.2, max_tokens=10)
        
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
        
        if target_language == 'sl':
            prompt = f"""
            Prevedi to besedilo v slovenščino. Ohrani terminologijo alpinizma in plezanja.
            
            Besedilo: {text}
            
            Odgovori SAMO s prevodom, brez dodatnega besedila.
            """
        else:
            prompt = f"""
            Translate this text to English. Preserve mountaineering and climbing terminology.
            
            Text: {text}
            
            Respond ONLY with the translation, no additional text.
            """
        
        messages = [
            {"role": "system", "content": "You are an expert translator specializing in mountaineering content."},
            {"role": "user", "content": prompt}
        ]
        
        response = self._make_request(messages, temperature=0.3, max_tokens=500)
        
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