from __future__ import annotations

import pytest

from exan_sidecar.grading import (
    AnswerItem,
    KeyItem,
    check_answer,
    grade_sheet,
    normalize_answer,
    parse_choice,
    parse_number,
    question_key,
    summarize,
)


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("1", "1"),
        ("1.", "1"),
        ("1)", "1"),
        ("Q1", "1"),
        ("Frage 1", "1"),
        ("Question 01", "1"),
        ("Aufgabe 3a", "3a"),
        ("3 a", "3a"),
        ("3(a)", "3a"),
        ("3.a", "3a"),
        ("2-1", "2.1"),
        ("2.1", "2.1"),
        ("Nr. 7", "7"),
    ],
)
def test_question_key(label: str, expected: str) -> None:
    assert question_key(label) == expected


def test_normalize_answer() -> None:
    assert normalize_answer("  „Paris“. ") == "paris"
    assert normalize_answer("(B)") == "b"
    assert normalize_answer("Hello   World!") == "hello world"


@pytest.mark.parametrize(
    ("expected", "given", "verdict", "reason"),
    [
        ("B", "b", "correct", "exact"),
        ("B", "(b)", "correct", "exact"),
        ("B", "b) Paris", "correct", "choice"),
        ("B", "C", "incorrect", "choice"),
        ("A, C", "C and A", "correct", "choice"),
        ("A, C", "A", "incorrect", "choice"),
        ("B) Paris", "Paris", "correct", "choice_text"),
        ("B", "Paris", "review", "format"),
        ("true", "wahr", "correct", "true_false"),
        ("falsch", "F", "correct", "true_false"),
        ("richtig", "no", "incorrect", "true_false"),
        ("true", "maybe", "review", "format"),
        ("3,5", "3.5", "correct", "number"),
        ("0.5", "1/2", "correct", "number"),
        ("12", "13", "incorrect", "number"),
        ("12", "12 apples", "review", "format"),
        ("10 cm", "10cm", "correct", "spacing"),
        ("Málaga", "Malaga", "review", "accent"),
        ("Straße", "Strasse", "correct", "exact"),
        ("Café", "Cafe", "review", "accent"),
        ("New York", "new-york", "review", "punctuation"),
        ("red green", "green red", "review", "order"),
        ("photosynthesis", "photosynthesys", "review", "similar"),
        ("photosynthesis", "respiration", "incorrect", "different"),
        ("Paris", "", "missing", "blank"),
        ("Paris", "—", "missing", "blank"),
        ("", "Paris", "review", "no_key"),
        ("Paris | Parigi", "parigi", "correct", "exact"),
        ("colour / color", "color", "correct", "exact"),
    ],
)
def test_check_answer(expected: str, given: str, verdict: str, reason: str) -> None:
    check = check_answer(expected, given)
    assert (check.verdict, check.reason) == (verdict, reason)


def test_parse_helpers() -> None:
    assert parse_choice("a, c") is not None
    assert parse_choice("a, c").letters == frozenset("ac")
    assert parse_choice("paris") is None
    assert parse_number("1/0") is None
    assert parse_number("-2,25") == parse_number("-9/4")


def test_grade_sheet_scores_and_overrides() -> None:
    key = [KeyItem("1", "B"), KeyItem("2", "Paris", points=2), KeyItem("3", "true"), KeyItem("Q1", "dup")]
    answers = [AnswerItem("Frage 1", "b"), AnswerItem("2", "Pariis"), AnswerItem("4", "extra")]

    result = grade_sheet(key, answers)
    finals = [(q.question, q.final) for q in result.questions]
    assert finals == [("1", "correct"), ("2", "review"), ("3", "missing")]
    assert result.score == 1 and result.max_score == 4
    assert result.percent == 25.0
    assert result.counts() == {"correct": 1, "incorrect": 0, "review": 1, "missing": 1}
    assert [a.question for a in result.extra] == ["4"]

    overridden = grade_sheet(key, answers, {"2": "correct", "1": "incorrect"})
    assert overridden.score == 2
    assert overridden.questions[0].auto == "correct" and overridden.questions[0].final == "incorrect"


def test_blank_answers_do_not_hide_later_duplicates() -> None:
    result = grade_sheet([KeyItem("1", "A")], [AnswerItem("1", ""), AnswerItem("1.", "A")])
    assert result.questions[0].final == "correct"


def test_summarize() -> None:
    key = [KeyItem("1", "A"), KeyItem("2", "B")]
    results = [
        grade_sheet(key, [AnswerItem("1", "A"), AnswerItem("2", "B")]),
        grade_sheet(key, [AnswerItem("1", "A"), AnswerItem("2", "C")]),
    ]
    stats = summarize(key, results)
    assert stats["graded"] == 2
    assert stats["average"] == 75.0
    assert stats["best"] == 100.0 and stats["worst"] == 50.0
    assert [q["rate"] for q in stats["questions"]] == [100.0, 50.0]
    assert summarize(key, [])["average"] is None
