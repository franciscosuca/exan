"""Anthropic Claude provider."""

import base64
import json

import anthropic

from ..config import settings
from . import BaseProvider
from .prompts import ANALYZE_STRUCTURE_PROMPT, EXTRACT_ANSWERS_PROMPT, grade_exam_prompt


class ClaudeProvider(BaseProvider):
    name = "claude"

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = "claude-sonnet-4-20250514"

    def _build_content(self, image_data: list[bytes], mime_types: list[str], prompt: str):
        content = []
        for data, mime in zip(image_data, mime_types):
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": mime,
                        "data": base64.b64encode(data).decode(),
                    },
                }
            )
        content.append({"type": "text", "text": prompt})
        return content

    def _parse_json(self, text: str) -> dict:
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            text = text.rsplit("```", 1)[0]
        return json.loads(text)

    async def analyze_exam_structure(self, image_data: list[bytes], mime_types: list[str]) -> dict:
        content = self._build_content(image_data, mime_types, ANALYZE_STRUCTURE_PROMPT)
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": content}],
        )
        return self._with_metadata(self._parse_json(response.content[0].text), response)

    async def extract_answers(self, image_data: list[bytes], mime_types: list[str]) -> dict:
        content = self._build_content(image_data, mime_types, EXTRACT_ANSWERS_PROMPT)
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": content}],
        )
        return self._with_metadata(self._parse_json(response.content[0].text), response)

    async def grade_exam(
        self,
        student_images: list[bytes],
        student_mime_types: list[str],
        exam_structure: dict,
        answer_key: dict,
    ) -> dict:
        prompt = grade_exam_prompt(exam_structure, answer_key)
        content = self._build_content(student_images, student_mime_types, prompt)
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": content}],
        )
        return self._with_metadata(self._parse_json(response.content[0].text), response)

    async def evaluate_text(self, text: str, prompt: str) -> dict:
        full_prompt = prompt + text
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": [{"type": "text", "text": full_prompt}]}],
        )
        return self._with_metadata(self._parse_json(response.content[0].text), response)
