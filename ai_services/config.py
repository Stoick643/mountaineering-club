"""
Configuration for AI Services
"""

import os

# AI Service Configuration
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

# Feature Flags
FEATURE_FLAGS = {
    'today_in_history': os.environ.get('FEATURE_TODAY_IN_HISTORY', 'True').lower() == 'true',
    'news_curation': os.environ.get('FEATURE_NEWS_CURATION', 'True').lower() == 'true',
    'ai_generation': os.environ.get('FEATURE_AI_GENERATION', 'True').lower() == 'true',
    'auto_translation': os.environ.get('FEATURE_AUTO_TRANSLATION', 'True').lower() == 'true',
}

# Content Settings
DEFAULT_LANGUAGE = os.environ.get('DEFAULT_LANGUAGE', 'sl')
CONTENT_CACHE_DURATION = int(os.environ.get('CONTENT_CACHE_DURATION', 24))  # hours
NEWS_UPDATE_INTERVAL = int(os.environ.get('NEWS_UPDATE_INTERVAL', 24))  # hours
MAX_DAILY_ARTICLES = int(os.environ.get('MAX_DAILY_ARTICLES', 5))
RELEVANCE_THRESHOLD = float(os.environ.get('RELEVANCE_THRESHOLD', 6.0))

# News Sources Configuration
NEWS_SOURCES = {
    "international": [
        "https://www.climbing.com/feed/",
        "https://www.alpinist.com/feed/", 
        "https://www.planetmountain.com/rss.xml"
    ],
    "regional": [
        "https://www.plezanje.net/rss/",
        "https://www.gore-ljudje.net/feed/"
    ],
    "safety": [
        "https://avalanche.si/rss/",
        "https://meteo.arso.gov.si/rss/"
    ]
}

# Historical Events Categories
EVENT_CATEGORIES = [
    'first_ascent',      # Prvi vzponi
    'tragedy',           # Tragedije 
    'discovery',         # Odkritja
    'achievement',       # Dosežki
    'expedition',        # Odprave
    'rescue',           # Reševanja
    'equipment',        # Oprema/tehnologija
    'club_history'      # Zgodovina kluba
]

# Slovenian Keywords for Relevance Scoring
MOUNTAINEERING_KEYWORDS_SL = [
    'alpinizem', 'plezanje', 'gorništvo', 'planinarstvo',
    'gore', 'vrh', 'plezalnica', 'via ferrata',
    'turno smučanje', 'pohodništvo', 'planinska pot',
    'varnost', 'oprema', 'plezalni pas', 'čelada',
    'julijske alpe', 'kamniške alpe', 'dolomiti',
    'triglav', 'everest', 'mont blanc', 'matterhorn'
]

MOUNTAINEERING_KEYWORDS_EN = [
    'mountaineering', 'climbing', 'alpinism', 'hiking',
    'summit', 'peak', 'route', 'expedition', 'rescue',
    'safety', 'equipment', 'gear', 'alps', 'mountain'
]