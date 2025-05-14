from googletrans import Translator
from typing import Dict, Any

class TranslationService:
    def __init__(self):
        self.translator = Translator()

    def translate_text(self, text: str) -> Dict[str, Any]:
        try:
            # Translate from English to Vietnamese
            result = self.translator.translate(text, src='en', dest='vi')
            
            return {
                "status": "success",
                "original_text": text,
                "translated_text": result.text,
                "source_language": result.src,
                "target_language": result.dest
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            } 