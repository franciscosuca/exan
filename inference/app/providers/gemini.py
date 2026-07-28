"""Google Gemini provider using the google-genai SDK."""

import json

from google import genai
from google.genai import types

from ..config import settings
from . import BaseProvider
from .prompts import ANALYZE_STRUCTURE_PROMPT, EXTRACT_ANSWERS_PROMPT, grade_exam_prompt


class GeminiProvider(BaseProvider):
    name = "gemini"

    def __init__(self):
        self._client = None
        self.model = "gemini-2.5-flash"

    @property
    def client(self):
        if self._client is None:
            self._client = genai.Client(api_key=settings.gemini_api_key)
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

    async def analyze_exam_structure(self, image_data: list[bytes], mime_types: list[str]) -> dict:
        contents = self._build_content(image_data, mime_types, ANALYZE_STRUCTURE_PROMPT)
        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        return self._parse_json(response.text)

    async def extract_answers(self, image_data: list[bytes], mime_types: list[str]) -> dict:
        contents = self._build_content(image_data, mime_types, EXTRACT_ANSWERS_PROMPT)
        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        return self._parse_json(response.text)

    async def grade_exam(
        self,
        student_images: list[bytes],
        student_mime_types: list[str],
        exam_structure: dict,
        answer_key: dict,
    ) -> dict:
        prompt = grade_exam_prompt(exam_structure, answer_key)
        contents = self._build_content(student_images, student_mime_types, prompt)
        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        return self._parse_json(response.text)

    async def evaluate_text(self, text: str, prompt: str) -> dict:
        full_prompt = prompt + text
        response = self.client.models.generate_content(
            model=self.model,
            contents=full_prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        return self._parse_json(response.text)
