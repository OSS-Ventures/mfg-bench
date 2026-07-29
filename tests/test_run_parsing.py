"""Unit tests for harness/run.py's answer parsing: single-part, multi-part, and parse failures.
"""
from harness.run import build_prompt, num_parts_of, parse_numeric_answer


def test_parse_single_part_answer():
    parsed, parse_failure = parse_numeric_answer("<answer>0.7594</answer>", "answer")
    assert parsed == 0.7594
    assert parse_failure is False


def test_parse_single_part_answer_strips_whitespace():
    parsed, parse_failure = parse_numeric_answer("<answer>  12.5 \n</answer>", "answer")
    assert parsed == 12.5
    assert parse_failure is False


def test_parse_single_part_missing_tag_is_failure():
    parsed, parse_failure = parse_numeric_answer("the answer is 0.75", "answer")
    assert parsed is None
    assert parse_failure is True


def test_parse_single_part_non_numeric_is_failure():
    parsed, parse_failure = parse_numeric_answer("<answer>not a number</answer>", "answer")
    assert parsed is None
    assert parse_failure is True


def test_parse_multi_part_answer():
    parsed, parse_failure = parse_numeric_answer("<answer>10, 200.5, -3</answer>", "answer", num_parts=3)
    assert parsed == [10.0, 200.5, -3.0]
    assert parse_failure is False


def test_parse_multi_part_wrong_count_is_failure():
    parsed, parse_failure = parse_numeric_answer("<answer>10, 200.5</answer>", "answer", num_parts=3)
    assert parsed is None
    assert parse_failure is True


def test_parse_multi_part_non_numeric_token_is_failure():
    parsed, parse_failure = parse_numeric_answer("<answer>10, abc</answer>", "answer", num_parts=2)
    assert parsed is None
    assert parse_failure is True


def test_parse_multi_part_missing_tag_is_failure():
    parsed, parse_failure = parse_numeric_answer("no tags here", "answer", num_parts=2)
    assert parsed is None
    assert parse_failure is True


def test_num_parts_of_single_part_task():
    task = {"ground_truth": {"value": 1.0, "tolerance": 0.01}}
    assert num_parts_of(task) == 1


def test_num_parts_of_multi_part_task():
    task = {"ground_truth": {"parts": [{"value": 1.0, "tolerance": 0.01}, {"value": 2.0, "tolerance": 0.01}]}}
    assert num_parts_of(task) == 2


def test_build_prompt_single_part_instructs_one_answer():
    task = {"prompt": "What is 2+2?"}
    prompt = build_prompt(task, "answer", num_parts=1)
    assert "<answer>0.1234</answer>" in prompt
    assert "comma-separated" not in prompt


def test_build_prompt_multi_part_instructs_comma_separated_answers():
    task = {"prompt": "What are the parts?"}
    prompt = build_prompt(task, "answer", num_parts=3)
    assert "comma-separated" in prompt
    assert "<answer>1, 2, 3</answer>" in prompt
