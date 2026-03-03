"""
LLM Service

Facade service for LLM Agent API-based question generation.
Agent API format: /api/v1/agents/{agent_id}/execute
"""

import asyncio
import logging

from sqlalchemy.orm import Session

from src.app.models import Category
from src.app.repositories.question import QuestionRepository
from src.app.services.llm.modules import LLMGenerateService

logger = logging.getLogger(__name__)


class LLMService:
    """
    Main LLM service facade.

    Provides interface for generating questions via LLM Agent API.
    """

    def __init__(
        self,
        db: Session,
        llm_url: str,
        llm_header_api_key: str,
        llm_model_api_key: str,
        llm_agent_id: str,
        llm_output_type: str = "json",
    ):
        """
        Initialize the LLM service.

        Args:
            db: Database session
            llm_url: LLM API base URL (e.g., "https://agent.admasolusi.space")
            llm_header_api_key: API key for x-api-key request header
            llm_model_api_key: API key inside execute payload body (`api_key`)
            llm_agent_id: Agent ID for the execute endpoint
            llm_output_type: Requested output format (json|markdown|html)
        """
        self.db = db
        self.generate = LLMGenerateService(
            llm_url=llm_url,
            llm_header_api_key=llm_header_api_key,
            llm_model_api_key=llm_model_api_key,
            llm_agent_id=llm_agent_id,
            llm_output_type=llm_output_type,
        )

    async def refresh_questions(
        self, category: Category | None = None, count: int = 5
    ) -> tuple[bool, int, str]:
        """
        Generate new questions and save them to the database.

        Args:
            category: Category to generate questions for (default: both)
            count: Number of questions to generate per category

        Returns:
            Tuple of (success, total_added, message)
        """
        categories = [category] if category else [Category.MIND_BLOWING]
        total_added = 0
        messages = []
        results = await asyncio.gather(
            *(self.generate.generate_questions(cat, count) for cat in categories),
            return_exceptions=True,
        )

        for cat, result in zip(categories, results, strict=False):
            if isinstance(result, BaseException):
                messages.append(f"Gagal generate soal {cat.value}: {str(result)}")
                continue
            success, questions, error = result

            if not success:
                messages.append(f"Gagal generate soal {cat.value}: {error}")
                continue

            # Save questions to database
            try:
                created = QuestionRepository.bulk_create_questions(self.db, questions)
                total_added += len(created)
                messages.append(f"✅ Berhasil menambahkan {len(created)} soal {cat.value}")
            except Exception as e:
                logger.error(f"Failed to save questions to DB: {e}")
                messages.append(f"Gagal menyimpan soal {cat.value}: {str(e)}")

        final_message = "\n".join(messages) if messages else "Tidak ada soal yang ditambahkan."
        return total_added > 0, total_added, final_message

    async def generate_and_save(
        self, category: Category, count: int = 5
    ) -> tuple[bool, int, str | None]:
        """
        Generate and save questions for a specific category.

        Args:
            category: Category to generate
            count: Number of questions to generate

        Returns:
            Tuple of (success, count_added, message)
        """
        success, questions, error = await self.generate.generate_questions(category, count)

        if not success:
            return False, 0, error

        try:
            created = QuestionRepository.bulk_create_questions(self.db, questions)
            return True, len(created), f"Berhasil menambahkan {len(created)} soal."
        except Exception as e:
            logger.error(f"Failed to save questions to DB: {e}")
            return False, 0, f"Gagal menyimpan soal: {str(e)}"
