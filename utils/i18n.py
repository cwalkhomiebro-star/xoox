import os
import json
import logging

logger = logging.getLogger(__name__)

LOCALES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "locales")

_translations = {}

def load_locales():
    """Loads all JSON files from the locales directory into memory."""
    global _translations
    if not os.path.exists(LOCALES_DIR):
        logger.warning(f"Locales directory not found: {LOCALES_DIR}")
        return

    for filename in os.listdir(LOCALES_DIR):
        if filename.endswith(".json"):
            lang_code = filename.replace(".json", "")
            filepath = os.path.join(LOCALES_DIR, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    _translations[lang_code] = json.load(f)
                logger.info(f"Loaded locale: {lang_code}")
            except Exception as e:
                logger.error(f"Failed to load locale {filename}: {e}")

def get_text(key: str, lang: str = "en", **kwargs) -> str:
    """
    Retrieves a translation string by key and language.
    Falls back to 'en' if the language or key is missing.
    Supports basic string formatting using kwargs.
    """
    # Fallback to English if the specific language isn't loaded
    if lang not in _translations:
        lang = "en"
        
    # Get the dictionary for the language
    lang_dict = _translations.get(lang, {})
    
    # Try to get the text, fallback to English if key is missing in target language
    text = lang_dict.get(key)
    if text is None:
        text = _translations.get("en", {}).get(key, key) # Fallback to key itself if entirely missing
        
    # Format the text if kwargs are provided
    if kwargs:
        try:
            return text.format(**kwargs)
        except KeyError as e:
            logger.error(f"Missing format key {e} in translation string for '{key}'")
            return text
            
    return text

# Initialize locales on module import
load_locales()
