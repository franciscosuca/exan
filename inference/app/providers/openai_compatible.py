"""Shared provider implementation for OpenAI-compatible chat APIs."""

import base64
import json

from openai import OpenAI

from . import BaseProvider
from .prompts import ANALYZE_STRUCTURE_PROMPT, EXTRACT_ANSWERS_PROMPT, grade_exam_prompt


class OpenAICompatibleProvider(BaseProvider):
    """Base implementation for OpenAI-compatible multimodal providers."""

    def __init__(self, *, api_key: str, model: str, base_url: str | None = None):
        self._client = None
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

    @property
    def client(self):
        if self._client is None:
            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        return self._client

    def _build_content(self, image_data: list[bytes], mime_types: list[str], prompt: str):
        content = []
        for data, mime in zip(image_data, mime_types):
            encoded = base64.b64encode(data).decode()
            content.append(
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{encoded}"}}
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
        return self._complete(content)

    async def extract_answers(self, image_data: list[bytes], mime_types: list[str]) -> dict:
        content = self._build_content(image_data, mime_types, EXTRACT_ANSWERS_PROMPT)
        return self._complete(content)

    async def grade_exam(
        self,
        student_images: list[bytes],
        student_mime_types: list[str],
        exam_structure: dict,
        answer_key: dict,
    ) -> dict:
        prompt = grade_exam_prompt(exam_structure, answer_key)
        content = self._build_content(student_images, student_mime_types, prompt)
        return self._complete(content)

    async def evaluate_text(self, text: str, prompt: str) -> dict:
        content = [{"type": "text", "text": prompt + text}]
        return self._complete(content)

    def _complete(self, content: list[dict]) -> dict:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": content}],
            max_tokens=4096,
        )
        return self._parse_json(response.choices[0].message.content)
