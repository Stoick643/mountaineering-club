"""
AI Prompt Templates for Mountaineering Club Content Generation
Contains all prompt templates used by AI services for content generation.
"""

# Historical Event Generation Prompts
HISTORICAL_EVENT_PROMPT_SL = """
Poišči pomemben zgodovinski dogodek iz sveta alpinizma, planinarstva ali gorništva, 
ki se je zgodil na današnji dan (primer: če je danes 10. julij 2025, je na današnji danes leta 2010 datum 10. julij 2010). 
Lahko je to tudi obletnica rojstva ali smrti znanega alpinista.

Prednostno vključi dogodke povezane s:
- Slovenskim alpinizmom (Julijske Alpe, Kamniške Alpe, Triglav)
- Slovenskimi alpinisti (Tomo Česen, Tomaž Humar, Silvo Karo, etc.)
- Julijskimi Alpami in sosednjimi gorami
- Zgodovino slovenskega gorništva in PZS

POMEMBNO: Če ni slovenskega dogodka, poišči mednarodni dogodek (lahko v angleščini).

Odgovori SAMO v JSON formatu z naslednjimi polji:
{{
    "year": leto_dogodka,
    "title": "kratek_naslov_v_slovenščini",
    "description": "opis_2_3_stavki_v_slovenščini", 
    "location": "lokacija",
    "people": ["ime1", "ime2"],
    "category": "first_ascent|tragedy|discovery|achievement|expedition",
    "reference_url": "URL vira (članka)"
}}

POMEMBNO: 
- Vrni rezultat samo, če je zraven URL!
- Odgovori samo z JSON, brez dodatnega besedila.
"""

HISTORICAL_EVENT_PROMPT_EN = """
Find an important historical event from mountaineering, alpinism or climbing 
that happened on {date} (MM-DD format, meaning month-day, any year).

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

# News Summarization Prompts
NEWS_SUMMARY_PROMPT_SL = """
Povzemi ta članek o alpinizmu/plezanju v slovenščini. 
Povzetek naj bo kratek ({max_length} znakov), informativen in zanimiv za člane planinskega društva.

Naslov: {title}
Vsebina: {content}

Odgovori SAMO s povzetkom, brez dodatnega besedila.
"""

NEWS_SUMMARY_PROMPT_EN = """
Summarize this mountaineering/climbing article in English.
Keep it short ({max_length} characters), informative and interesting for mountaineering club members.

Title: {title}
Content: {content}

Respond ONLY with the summary, no additional text.
"""

# Relevance Score Calculation Prompts
RELEVANCE_SCORE_PROMPT = """
Oceni relevantnost tega članka za slovensko planinsko društvo na lestvici 1-10.

Kriteriji:
- 9-10: Zelo pomembno (varnost, lokalni dogodki, nova oprema)
- 7-8: Pomembno (mednarodni alpinizem, tehnike)
- 5-6: Zanimivo (splošno plezanje, potovanja)
- 3-4: Manj relevantno (oddaljene lokacije, specifični športi)
- 1-2: Ni relevantno

Interesi društva: {interests}

Naslov: {title}
Vsebina: {content}

Odgovori SAMO s številko (npr. 7.5), brez dodatnega besedila.
"""

# Translation Prompts
TRANSLATION_PROMPT_TO_SL = """
Prevedi to besedilo v slovenščino. Ohrani terminologijo alpinizma in plezanja.

Besedilo: {text}

Odgovori SAMO s prevodom, brez dodatnega besedila.
"""

TRANSLATION_PROMPT_TO_EN = """
Translate this text to English. Preserve mountaineering and climbing terminology.

Text: {text}

Respond ONLY with the translation, no additional text.
"""

# System Messages for Different AI Tasks
SYSTEM_MESSAGES = {
    'historical_events': "You are an expert in mountaineering history. Always respond with valid JSON only.",
    'news_summary': "You are an expert at summarizing mountaineering content.",
    'relevance_score': "You are an expert at evaluating content relevance for mountaineering clubs.",
    'translation': "You are an expert translator specializing in mountaineering content."
}

# Default Configuration Values
DEFAULT_CLUB_INTERESTS = [
    'alpinizem', 'plezanje', 'gorništvo', 'varnost', 
    'oprema', 'julijske alpe', 'slovenija'
]

# Temperature Settings for Different Tasks
TEMPERATURE_SETTINGS = {
    'historical_events': 0.8,
    'news_summary': 0.3,
    'relevance_score': 0.2,
    'translation': 0.3
}

# Max Token Settings
MAX_TOKEN_SETTINGS = {
    'historical_events': 600,
    'news_summary': 200,
    'relevance_score': 10,
    'translation': 500
}