"""Ollama provider for fully offline/local inference."""

import base64
import json

import httpx

from ..config import settings
from . import BaseProvider
from .prompts import (
    analyze_exam_structure_prompt,
    compare_exam_prompt,
    extract_answers_prompt,
)


class OllamaProvider(BaseProvider):
    name = "ollama"

    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_model

    def _build_messages(self, image_data: list[bytes], mime_types: list[str], prompt: str):
        images = [base64.b64encode(data).decode() for data in image_data]
        return [{"role": "user", "content": prompt, "images": images}]

    def _parse_json(self, text: str) -> dict:
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            text = text.rsplit("```", 1)[0]
        return json.loads(text)

    async def _chat(self, messages: list[dict]) -> dict:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={"model": self.model, "messages": messages, "stream": False},
            )
            response.raise_for_status()
            return response.json()

    async def analyze_exam_structure(
        self,
        image_data: list[bytes],
        mime_types: list[str],
        criteria: str | None = None,
    ) -> dict:
        messages = self._build_messages(
            image_data,
            mime_types,
            analyze_exam_structure_prompt(criteria),
        )
        response = await self._chat(messages)
        return self._with_metadata(self._parse_json(response["message"]["content"]), response)

    async def extract_answers(
        self,
        image_data: list[bytes],
        mime_types: list[str],
        criteria: str | None = None,
    ) -> dict:
        messages = self._build_messages(
            image_data,
            mime_types,
            extract_answers_prompt(criteria),
        )
        response = await self._chat(messages)
        return self._with_metadata(self._parse_json(response["message"]["content"]), response)

    async def compare_exam(
        self,
        student_images: list[bytes],
        student_mime_types: list[str],
        exam_structure: dict,
        answer_key: dict,
    ) -> dict:
        prompt = compare_exam_prompt(exam_structure, answer_key)
        messages = self._build_messages(student_images, student_mime_types, prompt)
        response = await self._chat(messages)
        return self._with_metadata(self._parse_json(response["message"]["content"]), response)

    async def evaluate_text(self, text: str, prompt: str) -> dict:
        full_prompt = prompt + text
        messages = [{"role": "user", "content": full_prompt}]
        response = await self._chat(messages)
        return self._with_metadata(self._parse_json(response["message"]["content"]), response)
