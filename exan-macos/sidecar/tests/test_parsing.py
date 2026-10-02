from __future__ import annotations

import pytest

from exan_sidecar.parsing import ParsedSheet, parse_model_output, parse_text, sheet_from_json


def test_structured_json() -> None:
    sheet = parse_model_output(
        '{"name": "Ana Ruiz", "answers": [{"question": "1", "answer": "B"}, {"question": "2", "answer": ""}]}'
    )
    assert sheet.name == "Ana Ruiz"
    assert sheet.answers == [("1", "B"), ("2", "")]


@pytest.mark.parametrize(
    "payload",
    [
        '```json\n{"answers": {"1": "B", "2": "C"}}\n```',
        '{"1": "B", "2": "C", "comment": "ignored"}',
        '[{"q": 1, "a": "B"}, {"q": 2, "a": "C"}]',
        '{"responses": [["1", "B"], ["2", "C"]]}',
        '["B", "C"]',
        '<think>reading the page…</think>{"answers": [{"number": 1, "selected": ["B"]}, {"number": 2, "selected": "C"}]}',
        'Here is the result:\n{"answers": [{"question": "1", "answer": "B"}, {"question": "2", "answer": "C"}]}\nDone.',
    ],
)
def test_json_variants(payload: str) -> None:
    assert parse_model_output(payload).answers == [("1", "B"), ("2", "C")]


def test_json_booleans_and_numbers() -> None:
    sheet = sheet_from_json({"answers": [{"question": 1, "answer": True}, {"question": 2.0, "answer": 3.0}]})
    assert sheet.answers == [("1", "true"), ("2", "3")]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1. B\n2) C\n3: true", [("1", "B"), ("2", "C"), ("3", "true")]),
        ("Frage 1 - B\nFrage 2 – C", [("1", "B"), ("2", "C")]),
        ("**1.** B\n**2.** C", [("1", "B"), ("2", "C")]),
        ("1-B, 2-C, 3-D", [("1", "B"), ("2", "C"), ("3", "D")]),
        ("1B\n2C", [("1", "B"), ("2", "C")]),
        ("| Nr | Antwort |\n|---|---|\n| 1 | B |\n| 2 | C |", [("1", "B"), ("2", "C")]),
        (
            "<table><tr><td>1</td><td>B</td></tr><tr><td>2</td><td>C</td></tr></table>",
            [("1", "B"), ("2", "C")],
        ),
        ("1.\nParis\n2.\nBerlin", [("1", "Paris"), ("2", "Berlin")]),
        ("1. [ ] A [x] B [ ] C\n2. ☐ A ☒ C", [("1", "B"), ("2", "C")]),
        ("1. Answer: Paris", [("1", "Paris")]),
    ],
)
def test_text_variants(text: str, expected: list[tuple[str, str]]) -> None:
    assert parse_text(text).answers == expected


def test_name_line() -> None:
    sheet = parse_text("Name: Max Mustermann\n1. A\n2. B")
    assert sheet.name == "Max Mustermann"
    assert sheet.answers == [("1", "A"), ("2", "B")]


def test_deepseek_grounding_tags_are_removed() -> None:
    text = (
        "<|ref|>1. B<|/ref|><|det|>[[10, 20, 30, 40]]<|/det|>\n<|ref|>2. C<|/ref|><|det|>[[1,2,3,4]]<|/det|>"
    )
    assert parse_model_output(text).answers == [("1", "B"), ("2", "C")]


def test_doctags_output() -> None:
    text = (
        "<doctag><text><loc_10><loc_20><loc_200><loc_30>Name: Lea</text>"
        "<text><loc_10><loc_40><loc_200><loc_50>1. B</text>"
        "<otsl><loc_1><loc_2><loc_3><loc_4><ched>Nr<ched>Answer<nl><fcel>2<fcel>C<nl><fcel>3<fcel>true<nl></otsl>"
        "</doctag>"
    )
    sheet = parse_model_output(text)
    assert sheet.name == "Lea"
    assert sheet.answers == [("1", "B"), ("2", "C"), ("3", "true")]


def test_merge_prefers_first_non_blank() -> None:
    sheet = ParsedSheet(answers=[("1", ""), ("2", "B")])
    sheet.merge(ParsedSheet(name="Kim", answers=[("1.", "A"), ("2", "C"), ("3", "D")]))
    assert sheet.name == "Kim"
    assert sheet.answers == [("1", "A"), ("2", "B"), ("3", "D")]


def test_garbage_gives_nothing() -> None:
    assert parse_model_output("I cannot read this image.").answers == []
    assert parse_model_output("").answers == []
