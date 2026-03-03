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
        return f"""Buat {count} soal tebak-tebakan gaya TTS Cak Lontong dalam Bahasa Indonesia.

Target:
- Kategori: lucu
- Format: permainan punchline absurd tapi tetap masuk akal kalau dibaca keterangannya
- Gaya jawaban: singkat (1-3 kata), bukan jawaban literal yang "benar ilmiah"
- Tidak boleh mengandung SARA, pornografi, atau hinaan personal
- Pertanyaan harus unik dan tidak menyalin contoh mentah

Output HARUS JSON array. Tiap item wajib punya:
{{
  "word": "Teks pertanyaan, contoh: Ada udang di balik...",
  "answer": "Jawaban punchline, contoh: Gnadu",
  "hint": "Keterangan lucu yang menjelaskan twist jawabannya",
  "difficulty": "easy|medium|hard",
  "points": 80-140
}}

Contoh gaya:
- Pertanyaan: "Es es apa yang bisa jalan?"
  Jawaban: "Eskalator"
  Keterangan: "Kalau ga jalan ya tangga."

- Pertanyaan: "Kirimin uang lewat atm?"
  Jawaban: "Thanksya"
  Keterangan: "Thanks ya, sudah diterima."

Keluarkan JSON valid saja, tanpa markdown, tanpa teks tambahan."""

    @staticmethod
    def get_mind_blowing_prompt(count: int = 5) -> str:
        """
        Get prompt for generating 'mind_blowing' category questions.

        Args:
            count: Number of questions to generate

        Returns:
            Prompt string for LLM
        """
        return f"""Buat {count} soal tebak-tebakan gaya TTS Cak Lontong dalam Bahasa Indonesia.

Target:
- Kategori: mind_blowing
- Pertanyaan bernuansa logika, paradoks ringan, atau sudut pandang tak terduga
- Jawaban tetap punchline singkat (1-3 kata) dan nyeleneh
- Keterangan harus membuat jawaban terasa "oh iya juga"
- Tidak boleh mengandung SARA, pornografi, atau hinaan personal

Output HARUS JSON array. Tiap item wajib punya:
{{
  "word": "Teks pertanyaan",
  "answer": "Jawaban punchline",
  "hint": "Keterangan/twist penjelas",
  "difficulty": "medium|hard",
  "points": 100-180
}}

Contoh gaya:
- Pertanyaan: "Yang menyebabkan haus saat ramadan?"
  Jawaban: "Cuaca"
  Keterangan: "Kalau panas ya bikin haus."

- Pertanyaan: "Hati senang walaupun tak punya..."
  Jawaban: "Kaca"
  Keterangan: "Punya kaca juga tidak wajib."

Keluarkan JSON valid saja, tanpa markdown, tanpa teks tambahan."""

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
        return """Kamu adalah penulis soal TTS Cak Lontong berbahasa Indonesia untuk bot Telegram.
Fokusmu: pertanyaan jebakan + jawaban punchline + keterangan lucu yang membuat twist jadi masuk akal.
Selalu balas JSON valid saja tanpa teks tambahan."""
