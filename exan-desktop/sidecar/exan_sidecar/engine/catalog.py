"""Suggested small models that run on a typical school laptop.

Tags refer to the Ollama library (https://ollama.com/library). Any other installed vision model can
be selected as well; OpenAI-compatible servers (LM Studio, llama.cpp) list their own models.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

STRUCTURED = "structured"
OCR = "ocr"


@dataclass(frozen=True)
class CatalogModel:
    name: str
    label: str
    params: str
    download_gb: float
    min_ram_gb: int
    mode: str
    recommended: bool
    notes: str
    min_ollama: str = ""

    def view(self) -> dict:
        return asdict(self)


CATALOG: tuple[CatalogModel, ...] = (
    CatalogModel(
        name="qwen2.5vl:3b",
        label="Qwen2.5-VL 3B",
        params="3B",
        download_gb=3.2,
        min_ram_gb=8,
        mode=STRUCTURED,
        recommended=True,
        notes="Default. Reads handwriting, ticks and circled options; runs on most laptops with 8 GB RAM.",
    ),
    CatalogModel(
        name="qwen3-vl:4b",
        label="Qwen3-VL 4B",
        params="4B",
        download_gb=3.3,
        min_ram_gb=8,
        mode=STRUCTURED,
        recommended=False,
        notes="Newer Qwen vision model with stronger OCR. Needs a recent Ollama version.",
        min_ollama="0.12.7",
    ),
    CatalogModel(
        name="granite3.2-vision:2b",
        label="Granite 3.2 Vision 2B",
        params="2B",
        download_gb=2.4,
        min_ram_gb=6,
        mode=STRUCTURED,
        recommended=False,
        notes="Smallest option. Best with printed forms and clear handwriting.",
    ),
    CatalogModel(
        name="gemma3:4b",
        label="Gemma 3 4B",
        params="4B",
        download_gb=3.3,
        min_ram_gb=8,
        mode=STRUCTURED,
        recommended=False,
        notes="General vision model; good with typed answer sheets.",
    ),
    CatalogModel(
        name="qwen2.5vl:7b",
        label="Qwen2.5-VL 7B",
        params="7B",
        download_gb=6.0,
        min_ram_gb=16,
        mode=STRUCTURED,
        recommended=False,
        notes="More accurate with messy handwriting. Needs 16 GB RAM or a GPU.",
    ),
    CatalogModel(
        name="deepseek-ocr:3b",
        label="DeepSeek-OCR 3B",
        params="3B",
        download_gb=6.7,
        min_ram_gb=16,
        mode=OCR,
        recommended=False,
        notes="OCR specialist: transcribes the page, then Exan parses the lines. Best for written answers "
        "such as '1. B'; it cannot tell which printed option was circled.",
        min_ollama="0.13.0",
    ),
)

_OCR_HINTS = (
    "deepseek-ocr",
    "paddleocr",
    "olmocr",
    "nanonets-ocr",
    "dots.ocr",
    "dots-ocr",
    "docling",
    "chandra",
)


def resolve_mode(setting: str, model: str) -> str:
    """Pick structured (JSON) or OCR (transcribe + parse) mode for a model."""
    if setting in (STRUCTURED, OCR):
        return setting
    lowered = model.lower()
    for entry in CATALOG:
        if lowered == entry.name or lowered.startswith(entry.name.split(":")[0] + ":"):
            return entry.mode
    if any(hint in lowered for hint in _OCR_HINTS):
        return OCR
    return STRUCTURED


def catalog_view() -> list[dict]:
    return [entry.view() for entry in CATALOG]
