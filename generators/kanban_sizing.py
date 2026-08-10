"""Kanban card-count sizing generator (multiple-choice, via the `classification` scorer).

The number-of-kanban-cards formula -- N = ceil(daily demand x replenishment lead time x
(1 + safety factor) / container size) -- is a canonical, widely published Lean/pull-system
sizing rule (see SOURCE_URL). Ground truth here is computed directly from that fixed formula,
never a model's opinion, per GOALS.md's non-negotiable rule. Kept closed-form per SPEC.md's
Family B rule ("multiple-choice / classification / checklist") by presenting the correctly
computed count alongside three plausible wrong answers (a common calculation mistake each) and
asking the model to pick the correct one -- reusing the already-merged, unmodified
`scorers/classification.py` single-label exact-match scorer as the multiple-choice grading
mechanism, the same pattern unit 3.1 established for 8D/APQP phase classification.
"""
from __future__ import annotations

import math
import random
from datetime import datetime, timezone
from typing import Any

from generators.base import Generator

SOURCE = "DMAIC.com -- Kanban Calculation: How to Calculate Kanban Numbers"
SOURCE_URL = "https://www.dmaic.com/kanban-calculation-how-to-calculate-kanban-numbers/"

OPTION_LETTERS = ["A", "B", "C", "D"]


def _distinct_distractors(correct: int, no_safety: int, floored: int) -> list[int]:
    """Build 3 distinct wrong option values from common calculation mistakes, never equal to
    `correct` and never duplicated against each other. Falls back to a small offset from
    `correct` if a mistake happens to coincide with it or with an earlier candidate."""
    candidates = [no_safety, floored, correct - 1, correct + 1, correct + 2, correct - 2]
    distractors: list[int] = []
    for value in candidates:
        if value == correct or value < 0 or value in distractors:
            continue
        distractors.append(value)
        if len(distractors) == 3:
            return distractors

    # Extremely unlikely fallback (only if every candidate above collided): keep padding with an
    # increasing offset from `correct` until 3 distinct, non-negative distractors exist.
    offset = 3
    while len(distractors) < 3:
        for candidate in (correct + offset, correct - offset):
            if candidate != correct and candidate >= 0 and candidate not in distractors:
                distractors.append(candidate)
                if len(distractors) == 3:
                    break
        offset += 1
    return distractors


class KanbanSizingGenerator(Generator):
    name = "kanban_sizing"

    def generate(self, seed: int, difficulty: str = "standard") -> dict[str, Any]:
        rng = random.Random(seed)

        if difficulty == "standard":
            daily_demand = rng.randint(20, 200)
            lead_time_days = rng.randint(1, 5)
            safety_factor = rng.choice([0.1, 0.2, 0.3])
            container_size = rng.randint(5, 25)
        else:
            daily_demand = rng.randint(20, 500)
            lead_time_days = rng.choice([1, 2, 3, 4, 5, 6, 7, 1.5, 2.5, 3.5, 4.5])
            safety_factor = rng.choice([0.15, 0.25, 0.35, 0.45])
            container_size = rng.randint(5, 40)

        exact = daily_demand * lead_time_days * (1 + safety_factor) / container_size
        correct = math.ceil(exact)
        no_safety = math.ceil(daily_demand * lead_time_days / container_size)
        floored = math.floor(exact)

        distractors = _distinct_distractors(correct, no_safety, floored)
        values = [correct, *distractors]
        order = list(range(4))
        rng.shuffle(order)
        options = [values[i] for i in order]
        correct_letter = OPTION_LETTERS[options.index(correct)]

        options_text = "\n".join(
            f"{letter}) {value}" for letter, value in zip(OPTION_LETTERS, options)
        )
        prompt = (
            "A pull system replenishes a part with the following parameters:\n"
            f"- Average daily demand: {daily_demand} units/day\n"
            f"- Replenishment lead time: {lead_time_days} days\n"
            f"- Safety factor: {safety_factor:.0%} of lead-time demand\n"
            f"- Container (kanban) size: {container_size} units per card\n\n"
            "The number of kanban cards needed is the daily demand times the lead time times "
            "(1 + the safety factor), divided by the container size, rounded up to the next "
            "whole card.\n\n"
            "Which of the following is the correct number of kanban cards?\n"
            f"{options_text}\n\n"
            "Respond with just the letter of the correct option."
        )

        return {
            "id": f"source.kanban_sizing.{seed:06d}",
            "family": "source_grounded",
            "domain": "supply_chain_sop",
            "reasoning_tier": "L2",
            "answer_format": "classification",
            "prompt": prompt,
            "context": {
                "daily_demand": daily_demand,
                "lead_time_days": lead_time_days,
                "safety_factor": safety_factor,
                "container_size": container_size,
                "options": dict(zip(OPTION_LETTERS, options)),
                "correct_kanban_count": correct,
            },
            "ground_truth": {"value": correct_letter},
            "scorer": "classification",
            "generator": self.name,
            "seed": seed,
            "difficulty": difficulty,
            "source": SOURCE,
            "source_url": SOURCE_URL,
            "created": datetime.now(timezone.utc).date().isoformat(),
            "public": True,
        }
