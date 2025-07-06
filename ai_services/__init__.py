"""
AI Services Package for Mountaineering Club Platform
Provides AI-powered content generation and curation features.
"""

from .deepseek_client import DeepSeekClient
from .content_generator import HistoricalEventGenerator
from .news_curator import NewsCurator

__version__ = "1.0.0"
__all__ = ['DeepSeekClient', 'HistoricalEventGenerator', 'NewsCurator']