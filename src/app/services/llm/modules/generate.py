"""
LLM Generate module

Handles generating questions via LLM Agent API.
Format: /api/v1/agents/{agent_id}/execute
"""

import json
import logging
from typing import Any

import httpx

from src.app.models import Category, Difficulty, QuestionSource
from src.app.services.llm.modules.prompts import LPrompts

logger = logging.getLogger(__name__)


class LLMGenerateService:
    """Service for generating questions via LLM Agent API"""

    def __init__(
        self,
        llm_url: str,
        llm_header_api_key: str,
        llm_model_api_key: str,
        llm_agent_id: str,
        llm_output_type: str = "json",
    ):
        """
        Initialize the LLM generate service.

        Args:
            llm_url: LLM API base URL (e.g., "https://agent.admasolusi.space")
            llm_header_api_key: API key for x-api-key request header
            llm_model_api_key: API key inside execute payload body (`api_key`)
            llm_agent_id: Agent ID for the /api/v1/agents/{agent_id}/execute endpoint
            llm_output_type: Requested output format (json|markdown|html)
        """
        self.llm_url = llm_url.rstrip("/")
        self.llm_header_api_key = llm_header_api_key
        self.llm_model_api_key = llm_model_api_key
        self.llm_agent_id = llm_agent_id
        self.llm_output_type = llm_output_type or "json"
        self.prompts = LPrompts()

    async def generate_questions(
        self, category: Category, count: int = 5
    ) -> tuple[bool, list[dict[str, Any]], str | None]:
        """
        Generate questions via LLM Agent API.

        Args:
            category: Category of questions to generate
            count: Number of questions to generate

        Returns:
            Tuple of (success, questions_list, error_message)
        """
        try:
            # Build the agent API endpoint
            agent_url = f"{self.llm_url}/api/v1/agents/{self.llm_agent_id}/execute"

            # Get the appropriate prompt
            system_prompt = self.prompts.get_system_prompt()
            user_prompt = self.prompts.get_prompt(category, count)

            # Prepare the request headers
            headers = {
                "Content-Type": "application/json",
            }
            if self.llm_header_api_key:
                headers["x-api-key"] = self.llm_header_api_key

            # Build candidate payloads to handle different agent input schemas.
            payload_candidates = self._build_payload_candidates(system_prompt, user_prompt)

            response: httpx.Response | None = None
            last_422_detail = ""
            all_422_details: list[str] = []
            async with httpx.AsyncClient(timeout=60.0) as client:
                logger.info(f"Calling LLM Agent API: {agent_url}")
                for i, payload in enumerate(payload_candidates, start=1):
                    response = await client.post(
                        agent_url,
                        headers=headers,
                        json=payload,
                    )
                    if response.status_code == 422:
                        last_422_detail = self._extract_http_error_detail(response)
                        all_422_details.append(f"v{i}: {last_422_detail}")
                        logger.warning(
                            "LLM API 422 on payload variant %s/%s: %s",
                            i,
                            len(payload_candidates),
                            last_422_detail,
                        )
                        continue

                    response.raise_for_status()
                    break

                # If all payload variants returned 422.
                if response is None or response.status_code == 422:
                    detail = (
                        f" - {' | '.join(all_422_details[:3])}"
                        if all_422_details
                        else (f" - {last_422_detail}" if last_422_detail else "")
                    )
                    return False, [], f"LLM API error: 422{detail}"

            logger.info(f"LLM Agent API response status: {response.status_code}")
            logger.debug(f"LLM Agent API response: {response.text[:500]}")

            # Parse the response
            questions = self._parse_response(response.json())

            if not questions:
                return False, [], "Failed to parse LLM response"

            # Validate and normalize questions
            validated_questions = self._validate_questions(questions, category)

            return True, validated_questions, None

        except httpx.HTTPStatusError as e:
            detail = self._extract_http_error_detail(e.response)
            logger.error(f"LLM API error: {e.response.status_code} - {detail}")
            return False, [], f"LLM API error: {e.response.status_code} - {detail}"
        except httpx.RequestError as e:
            logger.error(f"LLM request error: {e}")
            return False, [], f"LLM request error: {str(e)}"
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}")
            return False, [], "Failed to parse LLM response"
        except Exception as e:
            logger.error(f"Unexpected error in LLM generation: {e}")
            return False, [], f"Unexpected error: {str(e)}"

    def _prepare_payload(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        """
        Prepare the API payload (not used for Agent API, kept for compatibility).

        Args:
            system_prompt: System prompt
            user_prompt: User prompt

        Returns:
            API payload dictionary
        """
        # For Agent API, use top-level user_prompt + model api_key.
        payload: dict[str, Any] = {"user_prompt": self._combine_prompts(system_prompt, user_prompt)}
        if self.llm_model_api_key:
            payload["api_key"] = self.llm_model_api_key
        return payload

    def _build_payload_candidates(
        self, system_prompt: str, user_prompt: str
    ) -> list[dict[str, Any]]:
        """Build payload candidates to support varying agent input schemas."""
        combined_prompt = self._combine_prompts(system_prompt, user_prompt)
        # Canonical payload for this agent endpoint:
        # body: user_prompt + model api_key
        # header: x-api-key (service gateway key)
        base_payload = {"user_prompt": combined_prompt}
        if self.llm_model_api_key:
            base_payload["api_key"] = self.llm_model_api_key
        prompt_only_payload = {"user_prompt": combined_prompt}
        payload_with_output_type = dict(base_payload)
        if self.llm_output_type:
            payload_with_output_type["output_type"] = self.llm_output_type

        return [
            # Exact schema confirmed by service.
            base_payload,
            # Optional extension for agents that consume output type.
            payload_with_output_type,
            # Strict fallback when only user_prompt is accepted.
            prompt_only_payload,
            # Variants for backward compatibility with older schemas.
            {"input": {"question": combined_prompt}},
            {
                "input": {
                    "instruction": system_prompt,
                    "question": user_prompt,
                    "api_key": self.llm_model_api_key,
                    "output_type": self.llm_output_type,
                }
            },
            {"input": {"prompt": user_prompt, "api_key": self.llm_model_api_key}},
            {"question": user_prompt},
            {
                "instruction": system_prompt,
                "question": user_prompt,
                "api_key": self.llm_model_api_key,
                "output_type": self.llm_output_type,
            },
        ]

    @staticmethod
    def _combine_prompts(system_prompt: str, user_prompt: str) -> str:
        """Combine system and user prompts for APIs that only accept one prompt field."""
        system = (system_prompt or "").strip()
        user = (user_prompt or "").strip()
        if not system:
            return user
        if not user:
            return system
        return f"{system}\n\n{user}"

    def _extract_http_error_detail(self, response: httpx.Response) -> str:
        """Extract concise error detail from API response."""
        try:
            payload = response.json()
            if isinstance(payload, dict):
                detail = payload.get("detail") or payload.get("message") or payload
            else:
                detail = payload
            text = json.dumps(detail, ensure_ascii=False)
        except Exception:
            text = response.text
        return text.strip().replace("\n", " ")[:280]

    def _parse_response(self, response_data: dict[str, Any]) -> list[dict[str, Any]] | None:
        """
        Parse the LLM Agent API response and extract questions.

        Expected response format:
        {
          "data": {
            "output": "JSON string or object"
          }
        }

        Args:
            response_data: Parsed JSON response from LLM Agent API

        Returns:
            List of question dictionaries or None
        """
        try:
            # Extract output from agent API response
            output_text = None

            if isinstance(response_data, dict):
                # Agent API format: data.output
                if "data" in response_data and isinstance(response_data["data"], dict):
                    output_text = response_data["data"].get("output")
                # Common wrapper format: { "result": "..." }
                elif "result" in response_data:
                    output_text = response_data["result"]
                # Alternative: direct output field
                elif "output" in response_data:
                    output_text = response_data["output"]
                # Alternative: data field containing the content
                elif "data" in response_data:
                    output_text = response_data["data"]

            if not output_text:
                logger.error(f"No output found in response: {response_data}")
                return None

            # Parse the output as JSON
            if isinstance(output_text, str):
                questions = json.loads(output_text)
            elif isinstance(output_text, list):
                questions = output_text
            else:
                logger.error(f"Unexpected output type: {type(output_text)}")
                return None

            # If response is a single object, wrap it in a list
            if isinstance(questions, dict):
                questions = [questions]

            return questions

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.error(f"Failed to parse LLM response: {e}, response: {response_data}")
            return None

    def _validate_questions(
        self, questions: list[dict[str, Any]], category: Category
    ) -> list[dict[str, Any]]:
        """
        Validate and normalize generated questions.

        Args:
            questions: Raw questions from LLM
            category: Expected category

        Returns:
            Validated and normalized questions
        """
        validated = []

        for q in questions:
            try:
                # Ensure required fields exist
                if not all(key in q for key in ["word", "answer"]):
                    logger.warning(f"Skipping invalid question: {q}")
                    continue

                # Normalize the question
                normalized = {
                    "word": q["word"].strip().upper(),
                    "answer": q["answer"].strip().upper(),
                    "category": category,
                    "difficulty": self._parse_difficulty(q.get("difficulty", "medium")),
                    "hint": q.get("hint", None),
                    "points": self._parse_points(q.get("points", 100)),
                    "source": QuestionSource.LLM,
                }

                validated.append(normalized)

            except Exception as e:
                logger.warning(f"Failed to validate question {q}: {e}")
                continue

        return validated

    def _parse_difficulty(self, difficulty: str) -> Difficulty:
        """Parse difficulty string to enum"""
        difficulty = difficulty.lower()
        if difficulty == "easy":
            return Difficulty.EASY
        elif difficulty == "hard":
            return Difficulty.HARD
        else:
            return Difficulty.MEDIUM

    def _parse_points(self, points: Any) -> int:
        """Parse points value"""
        try:
            return max(10, min(500, int(points)))
        except (ValueError, TypeError):
            return 100
