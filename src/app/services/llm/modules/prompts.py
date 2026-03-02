"""
LLM Prompt templates

Prompt templates for generating questions via LLM.
"""
from src.app.models import Category


class LPrompts:
    """Prompt templates for LLM question generation"""

    @staticmethod
    def get_lucu_prompt(count: int = 5) -> str:
        """
        Get prompt for generating 'lucu' (funny) category questions.

        Args:
            count: Number of questions to generate

        Returns:
            Prompt string for LLM
        """
        return f"""Generate {count} Indonesian word scramble questions for a fun Telegram game.

Requirements:
- Category: Funny/Slang/Jokes (Lucu)
- Words must be Indonesian: common slang, funny words, meme references, or everyday words with amusing meanings
- Difficulty: Mix of easy and medium
- Format: JSON array of objects

For each question provide:
{{
  "word": "SCRAMBLED_LETTERS",
  "answer": "CORRECT_ANSWER",
  "category": "lucu",
  "difficulty": "easy|medium|hard",
  "hint": "Subtle clue about the word",
  "points": 50-150
}}

Examples:
- "BUCUAT" → "UCUP" (common nickname)
- "AGNAMA" → "MANGGA" (everyday word)
- "ASAYAN" → "YASAN" (slang)

Return ONLY valid JSON. No explanation."""

    @staticmethod
    def get_mind_blowing_prompt(count: int = 5) -> str:
        """
        Get prompt for generating 'mind_blowing' category questions.

        Args:
            count: Number of questions to generate

        Returns:
            Prompt string for LLM
        """
        return f"""Generate {count} Indonesian word scramble questions for a fun Telegram game.

Requirements:
- Category: Mind Blowing (Riddles, Puzzles, Fun Facts, Logical Words)
- Words must be Indonesian: abstract concepts, scientific terms, philosophical words, or surprising words
- Difficulty: Medium to Hard
- Format: JSON array of objects

For each question provide:
{{
  "word": "SCRAMBLED_LETTERS",
  "answer": "CORRECT_ANSWER",
  "category": "mind_blowing",
  "difficulty": "medium|hard",
  "hint": "Think about... [context clue]",
  "points": 100-200
}}

Examples:
- "ASKAJAR" → "KASAJAR" (abstract concept)
- "MAIKSEM" → "KESIMA" (uncommon word)
- "GANUJI" → "JUANG" (meaningful word)

Return ONLY valid JSON. No explanation."""

    @staticmethod
    def get_prompt(category: Category, count: int = 5) -> str:
        """
        Get the appropriate prompt based on category.

        Args:
            category: Question category
            count: Number of questions to generate

        Returns:
            Prompt string for LLM
        """
        if category == Category.LUCU:
            return LPrompts.get_lucu_prompt(count)
        elif category == Category.MIND_BLOWING:
            return LPrompts.get_mind_blowing_prompt(count)
        else:
            return LPrompts.get_lucu_prompt(count)  # Default to lucu

    @staticmethod
    def get_system_prompt() -> str:
        """
        Get the system prompt for the LLM.

        Returns:
            System prompt string
        """
        return """You are a creative word puzzle generator for an Indonesian Telegram game. Your task is to generate fun, engaging word scramble questions that are culturally relevant to Indonesian speakers. Always respond with valid JSON only, no additional text."""
