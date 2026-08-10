"""Google Gemini provider using the google-genai SDK."""

import json

from google import genai
from google.genai import types

from ..config import settings
from . import BaseProvider
from .prompts import (
    analyze_exam_structure_prompt,
    compare_exam_prompt,
    extract_answers_prompt,
)

GRAMMAR_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "grammar": {
            "type": "OBJECT",
            "properties": {
                "issues": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "original_text": {"type": "STRING"},
                            "corrected_text": {"type": "STRING"},
                        },
                        "required": ["original_text", "corrected_text"],
                    },
                },
                "summary": {"type": "STRING"},
            },
            "required": ["issues", "summary"],
        },
    },
    "required": ["grammar"],
}


class GeminiProvider(BaseProvider):
    name = "gemini"

    def __init__(self, model: str):
        if not isinstance(model, str) or not model.strip():
            raise ValueError("A Gemini model is required")
        self._client = None
        self.model = model

    @property
    def client(self):
        if self._client is None:
            self._client = get_gemini_client()
        return self._client

    def _build_content(self, image_data: list[bytes], mime_types: list[str], prompt: str):
        parts = []
        for data, mime in zip(image_data, mime_types):
            parts.append(types.Part.from_bytes(data=data, mime_type=mime))
        parts.append(types.Part.from_text(text=prompt))
        return parts

    def _parse_json(self, text: str) -> dict:
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            text = text.rsplit("```", 1)[0]
        return json.loads(text)

    @staticmethod
    def _is_grammar_prompt(prompt: str) -> bool:
        return '"grammar": {' in prompt and '"issues": [' in prompt

    @staticmethod
    def _supports_response_schema() -> bool:
        fields = getattr(types.GenerateContentConfig, "model_fields", None)
        if fields is None:
            fields = getattr(types.GenerateContentConfig, "__fields__", {})
        return "response_schema" in fields

    # TODO: add this method to the BaseProvider interface and implement it in other providers
    def _evaluation_config(self, prompt: str) -> types.GenerateContentConfig:
        config_kwargs: dict[str, object] = {"response_mime_type": "application/json"}
        if self._is_grammar_prompt(prompt) and self._supports_response_schema():
            config_kwargs["response_schema"] = GRAMMAR_RESPONSE_SCHEMA
        return types.GenerateContentConfig(**config_kwargs)

    async def analyze_exam_structure(
        self,
        image_data: list[bytes],
        mime_types: list[str],
        criteria: str | None = None,
    ) -> dict:
        contents = self._build_content(
            image_data,
            mime_types,
            analyze_exam_structure_prompt(criteria),
        )
        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        return self._with_metadata(self._parse_json(response.text), response)

    async def extract_answers(
        self,
        image_data: list[bytes],
        mime_types: list[str],
        criteria: str | None = None,
    ) -> dict:
        contents = self._build_content(
            image_data,
            mime_types,
            extract_answers_prompt(criteria),
        )
        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        return self._with_metadata(self._parse_json(response.text), response)

    async def compare_exam(
        self,
        student_images: list[bytes],
        student_mime_types: list[str],
        exam_structure: dict,
        answer_key: dict,
    ) -> dict:
        prompt = compare_exam_prompt(exam_structure, answer_key)
        contents = self._build_content(student_images, student_mime_types, prompt)
        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        return self._with_metadata(self._parse_json(response.text), response)

    async def evaluate_text(self, text: str, prompt: str) -> dict:
        full_prompt = prompt + text
        response = self.client.models.generate_content(
            model=self.model,
            contents=full_prompt,
            config=self._evaluation_config(prompt),
        )
        return self._with_metadata(self._parse_json(response.text), response)


def get_gemini_client():
    """Create the configured Gemini API client."""
    return genai.Client(api_key=settings.gemini_api_key)


def _model_field(model: object, field: str, default: object = None) -> object:
    if isinstance(model, dict):
        return model.get(field, default)
    return getattr(model, field, default)


def _supports_content_generation(actions: list[str]) -> bool:
    normalized = {action.replace("_", "").lower() for action in actions}
    return "generatecontent" in normalized or "textgeneration" in normalized


def _normalize_model_name(name: str) -> str:
    return name.removeprefix("models/")


def list_gemini_models() -> list[dict]:
    """Return Gemini models that can generate text or content."""
    catalogue: list[dict] = []
    client = get_gemini_client()
    for model in client.models.list():
        raw_name = _model_field(model, "name")
        if not isinstance(raw_name, str) or not raw_name:
            continue

        raw_actions = _model_field(model, "supported_actions")
        if raw_actions is None:
            raw_actions = _model_field(model, "supported_generation_methods", [])
        raw_actions = raw_actions or []
        if isinstance(raw_actions, str):
            raw_actions = [raw_actions]
        supported_actions = [str(action) for action in raw_actions]
        if not _supports_content_generation(supported_actions):
            continue

        model_id = _normalize_model_name(raw_name)
        if not model_id:
            continue
        display_name = _model_field(model, "display_name") or model_id
        catalogue.append(
            {
                "id": model_id,
                "name": model_id,
                "display_name": str(display_name),
                "supported_actions": supported_actions,
            }
        )
    return catalogue
