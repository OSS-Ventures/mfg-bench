"""Unit tests for harness/run.py's answer parsing: single-part, multi-part, and parse failures.
"""
from harness.run import (
    build_checklist_prompt,
    build_classification_prompt,
    build_prompt,
    build_simulated_prompt,
    is_multi_label_classification,
    num_parts_of,
    parse_checklist_answer,
    parse_classification_answer,
    parse_numeric_answer,
    parse_simulated_answer,
)


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


def test_parse_simulated_answer_valid_json_list():
    raw = '<answer>[{"assignments": {"m0": "j0"}}, {"assignments": {}}]</answer>'
    parsed, parse_failure = parse_simulated_answer(raw, "answer")
    assert parsed == [{"assignments": {"m0": "j0"}}, {"assignments": {}}]
    assert parse_failure is False


def test_parse_simulated_answer_missing_tag_is_failure():
    parsed, parse_failure = parse_simulated_answer("no tags here", "answer")
    assert parsed is None
    assert parse_failure is True


def test_parse_simulated_answer_invalid_json_is_failure():
    parsed, parse_failure = parse_simulated_answer("<answer>not json</answer>", "answer")
    assert parsed is None
    assert parse_failure is True


def test_parse_simulated_answer_non_list_json_is_failure():
    parsed, parse_failure = parse_simulated_answer('<answer>{"assignments": {}}</answer>', "answer")
    assert parsed is None
    assert parse_failure is True


def test_build_simulated_prompt_instructs_json_plan_of_the_right_horizon():
    task = {"prompt": "Decide the schedule.", "ground_truth": {"horizon": 3}}
    prompt = build_simulated_prompt(task, "answer")
    assert "exactly 3 objects" in prompt
    assert "<answer></answer>" in prompt


# --- classification prompt/parse ---


def test_is_multi_label_classification_single_label_task():
    assert is_multi_label_classification({"ground_truth": {"value": "D4"}}) is False


def test_is_multi_label_classification_multi_label_task():
    assert is_multi_label_classification({"ground_truth": {"value": ["a", "b"]}}) is True


def test_build_classification_prompt_single_label_instructs_one_label():
    task = {"prompt": "Which discipline?", "ground_truth": {"value": "D4"}}
    prompt = build_classification_prompt(task, "answer")
    assert "<answer></answer>" in prompt
    assert "comma-separated" not in prompt


def test_build_classification_prompt_multi_label_instructs_comma_separated_labels():
    task = {"prompt": "Which wastes?", "ground_truth": {"value": ["a", "b"]}}
    prompt = build_classification_prompt(task, "answer")
    assert "comma-separated" in prompt


def test_parse_classification_single_label_answer():
    parsed, parse_failure = parse_classification_answer("<answer>D4</answer>", "answer", multi_label=False)
    assert parsed == "D4"
    assert parse_failure is False


def test_parse_classification_single_label_strips_whitespace():
    parsed, parse_failure = parse_classification_answer(
        "<answer>  D4 \n</answer>", "answer", multi_label=False
    )
    assert parsed == "D4"
    assert parse_failure is False


def test_parse_classification_multi_label_answer():
    parsed, parse_failure = parse_classification_answer(
        "<answer>waste_a, waste_b</answer>", "answer", multi_label=True
    )
    assert parsed == ["waste_a", "waste_b"]
    assert parse_failure is False


def test_parse_classification_missing_tag_is_failure():
    parsed, parse_failure = parse_classification_answer("D4", "answer", multi_label=False)
    assert parsed is None
    assert parse_failure is True


def test_parse_classification_empty_tag_is_failure():
    parsed, parse_failure = parse_classification_answer("<answer></answer>", "answer", multi_label=False)
    assert parsed is None
    assert parse_failure is True


def test_parse_classification_multi_label_empty_tag_is_failure():
    parsed, parse_failure = parse_classification_answer("<answer></answer>", "answer", multi_label=True)
    assert parsed is None
    assert parse_failure is True


# --- checklist prompt/parse ---


def test_build_checklist_prompt_mentions_leaving_tag_empty():
    task = {"prompt": "Which elements apply?"}
    prompt = build_checklist_prompt(task, "answer")
    assert "leave the tag empty" in prompt


def test_parse_checklist_answer_comma_separated_items():
    parsed, parse_failure = parse_checklist_answer(
        "<answer>Design FMEA, Control Plan</answer>", "answer"
    )
    assert parsed == ["Design FMEA", "Control Plan"]
    assert parse_failure is False


def test_parse_checklist_answer_empty_tag_is_a_legitimate_empty_list():
    parsed, parse_failure = parse_checklist_answer("<answer></answer>", "answer")
    assert parsed == []
    assert parse_failure is False


def test_parse_checklist_answer_missing_tag_is_failure():
    parsed, parse_failure = parse_checklist_answer("no tags here", "answer")
    assert parsed is None
    assert parse_failure is True
