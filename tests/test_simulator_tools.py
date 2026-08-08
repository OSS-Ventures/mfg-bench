"""Tests for `simulator.tools` (roadmap unit 2.5): the turn-capped tool interface behind L5
agentic orchestration. All hand-verified against `simulator.engine.step`'s own documented
contract -- these tests never call a model.
"""
import copy

import pytest

from simulator import engine
from simulator.tools import TOOL_DEFINITIONS, SimulationSession, dispatch


def _one_machine_one_job_state(remaining_work=4.0, due=2, capacity=2.0):
    return {
        "time": 0,
        "jobs": {
            "j0": {
                "remaining_work": remaining_work,
                "release": 0,
                "due": due,
                "weight": 1.0,
                "completed_at": None,
            }
        },
        "machines": {"m0": {"capacity": capacity, "down_until": 0}},
        "cumulative": {
            "weighted_tardiness": 0.0,
            "overtime_cost": 0.0,
            "jobs_completed": 0,
            "jobs_completed_on_time": 0,
        },
    }


class TestToolDefinitions:
    def test_exposes_exactly_get_state_and_submit_action(self):
        names = {t["name"] for t in TOOL_DEFINITIONS}
        assert names == {"get_state", "submit_action"}

    def test_every_definition_has_a_valid_json_schema_shape(self):
        for tool in TOOL_DEFINITIONS:
            assert isinstance(tool["name"], str) and tool["name"]
            assert isinstance(tool["description"], str) and tool["description"]
            schema = tool["input_schema"]
            assert schema["type"] == "object"
            assert "properties" in schema


class TestGetState:
    def test_returns_a_snapshot_without_advancing_time_or_state(self):
        initial = _one_machine_one_job_state()
        session = SimulationSession(initial, horizon=2, max_turns=5)
        snapshot = session.get_state()
        assert snapshot["time"] == 0
        assert snapshot["jobs"]["j0"]["remaining_work"] == 4.0
        assert snapshot["done"] is False
        assert session.state["time"] == 0  # unchanged

    def test_consumes_one_turn(self):
        session = SimulationSession(_one_machine_one_job_state(), horizon=2, max_turns=5)
        session.get_state()
        assert session.turns_used == 1
        session.get_state()
        assert session.turns_used == 2

    def test_reports_turns_remaining(self):
        session = SimulationSession(_one_machine_one_job_state(), horizon=2, max_turns=3)
        snapshot = session.get_state()
        assert snapshot["turns_remaining"] == 2

    def test_refuses_once_turn_budget_is_exhausted(self):
        session = SimulationSession(_one_machine_one_job_state(), horizon=5, max_turns=1)
        session.get_state()
        result = session.get_state()
        assert result == {"error": "turn budget exhausted", "done": True}
        assert session.turns_used == 1  # pinned, never exceeds max_turns

    def test_does_not_mutate_the_session_internal_state_dict(self):
        session = SimulationSession(_one_machine_one_job_state(), horizon=2, max_turns=5)
        snapshot = session.get_state()
        snapshot["jobs"]["j0"]["remaining_work"] = 999.0
        assert session.state["jobs"]["j0"]["remaining_work"] == 4.0


class TestSubmitAction:
    def test_legal_action_advances_state_and_matches_engine_step_directly(self):
        initial = _one_machine_one_job_state(remaining_work=4.0, due=2, capacity=2.0)
        session = SimulationSession(initial, horizon=3, max_turns=5)
        expected_state, expected_kpis = engine.step(
            copy.deepcopy(initial), {"assignments": {"m0": "j0"}, "overtime": {}}
        )

        result = session.submit_action({"assignments": {"m0": "j0"}})

        assert session.state == expected_state
        assert result["time"] == 1
        assert result["kpis_this_step"]["tardiness_incurred"] == expected_kpis["tardiness_incurred"]
        assert result["cumulative"] == expected_state["cumulative"]

    def test_records_only_accepted_actions_in_history_in_order(self):
        session = SimulationSession(_one_machine_one_job_state(), horizon=3, max_turns=10)
        session.submit_action({"assignments": {"m0": "j0"}})
        assert session.history == [{"assignments": {"m0": "j0"}, "overtime": {}}]

    def test_omitting_assignments_or_overtime_defaults_to_idle_no_overtime(self):
        session = SimulationSession(_one_machine_one_job_state(), horizon=3, max_turns=5)
        result = session.submit_action({})
        assert "error" not in result
        assert session.history == [{"assignments": {}, "overtime": {}}]

    def test_illegal_action_is_rejected_without_advancing_state_but_spends_a_turn(self):
        session = SimulationSession(_one_machine_one_job_state(), horizon=3, max_turns=5)
        result = session.submit_action({"assignments": {"m0": "does-not-exist"}})
        assert "error" in result
        assert session.state["time"] == 0
        assert session.history == []
        assert session.turns_used == 1

    def test_malformed_assignments_type_is_rejected_without_raising(self):
        session = SimulationSession(_one_machine_one_job_state(), horizon=3, max_turns=5)
        result = session.submit_action({"assignments": "not-a-dict"})
        assert "error" in result
        assert session.turns_used == 1

    def test_refuses_once_turn_budget_is_exhausted(self):
        session = SimulationSession(_one_machine_one_job_state(), horizon=5, max_turns=1)
        session.submit_action({"assignments": {"m0": "j0"}})
        result = session.submit_action({"assignments": {"m0": "j0"}})
        assert result == {"error": "turn budget exhausted", "done": True}
        assert session.turns_used == 1

    def test_refuses_once_horizon_is_reached_and_marks_done(self):
        session = SimulationSession(_one_machine_one_job_state(), horizon=1, max_turns=10)
        first = session.submit_action({"assignments": {"m0": "j0"}})
        assert first["done"] is True
        second = session.submit_action({"assignments": {}})
        assert second["error"] == "simulation already complete"
        assert session.turns_used == 2  # the extra call still spent a turn
        assert len(session.history) == 1  # but did not apply a second action

    def test_done_is_true_once_horizon_reached_even_with_turns_left(self):
        session = SimulationSession(_one_machine_one_job_state(), horizon=1, max_turns=10)
        session.submit_action({"assignments": {"m0": "j0"}})
        assert session.done is True
        assert session.turns_used < session.max_turns


class TestDeterminism:
    def test_same_initial_state_and_action_sequence_yields_identical_sessions(self):
        initial = _one_machine_one_job_state()
        actions = [{"assignments": {"m0": "j0"}}, {"assignments": {}}]

        session_a = SimulationSession(initial, horizon=2, max_turns=10)
        session_b = SimulationSession(initial, horizon=2, max_turns=10)
        for action in actions:
            result_a = session_a.submit_action(action)
            result_b = session_b.submit_action(action)
            assert result_a == result_b

        assert session_a.state == session_b.state
        assert session_a.history == session_b.history


class TestDispatch:
    def test_routes_get_state(self):
        session = SimulationSession(_one_machine_one_job_state(), horizon=2, max_turns=5)
        result = dispatch(session, "get_state", {})
        assert result["time"] == 0
        assert session.turns_used == 1

    def test_routes_submit_action(self):
        session = SimulationSession(_one_machine_one_job_state(), horizon=2, max_turns=5)
        result = dispatch(session, "submit_action", {"assignments": {"m0": "j0"}})
        assert result["time"] == 1

    def test_submit_action_with_none_input_treated_as_idle(self):
        session = SimulationSession(_one_machine_one_job_state(), horizon=2, max_turns=5)
        result = dispatch(session, "submit_action", None)
        assert "error" not in result

    def test_unknown_tool_name_raises(self):
        session = SimulationSession(_one_machine_one_job_state(), horizon=2, max_turns=5)
        with pytest.raises(ValueError):
            dispatch(session, "delete_all_jobs", {})
