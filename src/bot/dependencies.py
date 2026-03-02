"""Bot dependency providers.

Keep service factory functions separate from bot entrypoint to avoid
circular imports between handlers and main module.
"""

import src.config.env as env
from src.app.services.game import GameService
from src.app.services.llm import LLMService
from src.database.session import SessionLocal


def get_game_service() -> GameService:
    """Get a game service instance with a fresh DB session."""
    db = SessionLocal()
    return GameService(
        db=db,
        game_timeout=env.GAME_TIMEOUT,
        hint_penalty=env.HINT_PENALTY,
        max_hints=env.MAX_HINTS,
    )


def get_llm_service() -> LLMService:
    """Get an LLM service instance with a fresh DB session."""
    db = SessionLocal()
    return LLMService(
        db=db,
        llm_url=env.LLM_URL,
        llm_header_api_key=env.LLM_HEADER_API_KEY,
        llm_model_api_key=env.LLM_MODEL_API_KEY,
        llm_agent_id=env.LLM_AGENT_ID,
        llm_output_type=env.LLM_OUTPUT_TYPE,
    )
