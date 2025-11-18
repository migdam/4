"""
Enhancement 5-6: Multi-language Support and Translation
"""
from typing import Optional, Dict
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
import config


class LanguageDetector:
    """Detect and translate job descriptions"""

    SUPPORTED_LANGUAGES = {
        'en': 'English',
        'pl': 'Polish',
        'de': 'German',
        'fr': 'French',
        'es': 'Spanish',
        'it': 'Italian',
        'pt': 'Portuguese'
    }

    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.3,
            openai_api_key=config.OPENAI_API_KEY
        )

    def detect_language(self, text: str) -> str:
        """Detect the language of text"""
        if not text:
            return 'en'

        # Simple heuristic detection
        text_lower = text.lower()

        # Polish indicators
        polish_chars = ['ą', 'ć', 'ę', 'ł', 'ń', 'ó', 'ś', 'ź', 'ż']
        polish_words = ['praca', 'stanowisko', 'wymagania', 'oferujemy', 'zakres']

        if any(char in text_lower for char in polish_chars):
            return 'pl'
        if sum(1 for word in polish_words if word in text_lower) >= 2:
            return 'pl'

        # German indicators
        german_chars = ['ä', 'ö', 'ü', 'ß']
        german_words = ['arbeit', 'stelle', 'anforderungen', 'wir bieten', 'aufgaben']

        if any(char in text_lower for char in german_chars):
            return 'de'
        if sum(1 for word in german_words if word in text_lower) >= 2:
            return 'de'

        # Default to English
        return 'en'

    def translate_text(self, text: str, target_language: str = 'en') -> str:
        """Translate text to target language using LLM"""
        if not text:
            return text

        source_language = self.detect_language(text)

        if source_language == target_language:
            return text

        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a professional translator. Translate the following text to {target_lang}.
            Maintain the original meaning, tone, and technical terms.
            For job postings, preserve role titles, company names, and technical skills in their original form."""),
            ("human", "{text}")
        ])

        messages = prompt.format_messages(
            target_lang=self.SUPPORTED_LANGUAGES.get(target_language, 'English'),
            text=text[:2000]  # Limit to 2000 chars to save tokens
        )

        try:
            response = self.llm.invoke(messages)
            return response.content.strip()
        except Exception as e:
            # If translation fails, return original
            return text

    def create_bilingual_content(self, text: str, target_language: str = 'en') -> Dict[str, str]:
        """Create content in both original and translated language"""
        source_language = self.detect_language(text)
        translated = self.translate_text(text, target_language) if source_language != target_language else text

        return {
            'original': text,
            'original_language': source_language,
            'translated': translated,
            'target_language': target_language
        }
