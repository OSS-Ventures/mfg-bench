"""Lean "8 Wastes" (TIMWOODS) waste-classification generator.

The eight wastes of Lean (Transportation, Inventory, Motion, Waiting, Overproduction,
Overprocessing, Defects, Skills/non-utilized talent -- the TIMWOODS acronym, an extension of
Taiichi Ohno's original seven Toyota Production System wastes) are a canonical, widely
published taxonomy. Ground truth here is that fixed, cited structure -- never a model's
opinion, per GOALS.md's non-negotiable rule: given a paraphrased shop-floor scenario, the
correct waste is whichever one the scenario actually demonstrates in the canonical taxonomy, a
fixed lookup, not a judgment call.

Per SPEC.md's Family B licensing rule: no source text is reproduced anywhere below. Every
scenario is an original paraphrase of the general, freely published meaning of each waste (see
SOURCE_URL), not a quotation from any paywalled text.
"""
from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any

from generators.base import Generator

SOURCE = "SixSigma.us -- What is TIMWOODS? 8 Wastes of Lean and How to Reduce Them"
SOURCE_URL = "https://www.6sigma.us/lean-waste/timwoods-8-waste-of-lean/"

#: The canonical 8 wastes (TIMWOODS): waste name -> its meaning, in TIMWOODS letter order.
WASTES: dict[str, str] = {
    "Transportation": "Unnecessary movement of materials, parts, or product between processes, "
    "storage locations, or facilities",
    "Inventory": "More raw material, work-in-process, or finished goods on hand than is "
    "immediately needed for the next step",
    "Motion": "Unnecessary movement by people -- reaching, walking, searching, bending -- that "
    "adds no value to the product",
    "Waiting": "Idle time when people, material, or equipment sit idle waiting for the next "
    "step, a decision, or a signal",
    "Overproduction": "Producing more, sooner, or faster than the next process or the customer "
    "actually needs right now",
    "Overprocessing": "Doing more work, or higher-precision work, on a product than what the "
    "customer actually requires",
    "Defects": "Effort spent producing, inspecting, sorting, or repairing nonconforming output",
    "Skills": "Failing to use employees' knowledge, skills, experience, or improvement ideas",
}

#: Original paraphrases of a concrete shop-floor scenario demonstrating each waste. "hard"
#: entries are written to be easy to confuse with an adjacent waste, requiring closer reading
#: than "standard" entries.
SCENARIOS: dict[str, dict[str, list[str]]] = {
    "Transportation": {
        "standard": [
            "Partially finished parts are trucked back and forth twice a day between two "
            "buildings on the same site because the two process steps that need them are "
            "located in different buildings.",
            "A pallet of components is moved through four different staging areas before it "
            "ever reaches the machine that actually uses it.",
        ],
        "hard": [
            "To free up floor space in one building, a batch of subassemblies is now shipped "
            "to a nearby warehouse for temporary storage and then shipped back a week later "
            "for final assembly, even though nothing about the subassemblies changes in "
            "between.",
            "A redesign of the plant layout doubled the distance a cart travels between the "
            "welding cell and the paint booth, even though both cells' own output rates stayed "
            "the same.",
        ],
    },
    "Inventory": {
        "standard": [
            "A supervisor keeps three weeks of raw-material stock on the floor even though the "
            "line only consumes about four days of it before the next scheduled delivery "
            "arrives.",
            "Finished goods pile up in a staging area for two weeks awaiting a customer pickup "
            "date that was already known when the units were produced.",
        ],
        "hard": [
            "A buyer increases the standing order quantity for a fast-moving component to "
            "qualify for a small per-unit discount, and the resulting stock now sits in the "
            "warehouse for months at a time before it is consumed.",
            "Because changeovers on one machine are slow, the plant runs unusually large batches "
            "of each part, leaving large quantities of work-in-process sitting between that "
            "machine and the next step for weeks at a time.",
        ],
    },
    "Motion": {
        "standard": [
            "An operator has to walk to a supply cabinet on the other side of the cell several "
            "times per shift because the fasteners used at that station are not stored at the "
            "workstation itself.",
            "A technician bends down and reaches into a low, cluttered bin to search for the "
            "right-size wrench every time a fixture needs adjusting.",
        ],
        "hard": [
            "An assembler has to twist and reach across their own workstation to grab a tool "
            "that is hung on the wrong side of the bench for a right-handed operator, on every "
            "single cycle.",
            "A machine operator has to walk around the machine and back six times per shift "
            "just to reach a control panel that was installed on the far side from the loading "
            "point.",
        ],
    },
    "Waiting": {
        "standard": [
            "A machine sits idle for twenty minutes each shift because the operator has to wait "
            "for a forklift to bring the next batch of raw material.",
            "An inspector cannot start checking a finished lot until a supervisor's sign-off "
            "arrives by email, which typically takes over an hour.",
        ],
        "hard": [
            "Downstream operators stand around for the first fifteen minutes of every shift "
            "because the upstream process, which runs a different, longer cycle time, has not "
            "yet produced its first unit of the day.",
            "A CNC machine finishes its cycle and then sits idle for several minutes because the "
            "next operator is still finishing paperwork from the previous job before loading "
            "the new one.",
        ],
    },
    "Overproduction": {
        "standard": [
            "A workstation keeps running at full speed and building extra units even after the "
            "downstream process has signaled it has enough inventory to last the rest of the "
            "shift.",
            "A line produces a full day's worth of a part because the machine is already set up "
            "for it, even though the schedule only calls for a half-day's worth.",
        ],
        "hard": [
            "To avoid a changeover later in the week, an operator runs an extra batch of a part "
            "today well beyond what this week's actual customer orders require, and the extra "
            "units sit unused.",
            "A department builds ahead of the published schedule during a slow morning because "
            "the machine would otherwise be idle, even though the extra units will not be "
            "needed for two more weeks.",
        ],
    },
    "Overprocessing": {
        "standard": [
            "An operator polishes a surface to a mirror finish on a bracket that will be "
            "welded over and never seen, even though the customer's specification does not "
            "require that finish.",
            "A part is inspected against a tolerance ten times tighter than what the customer's "
            "drawing actually calls for, adding inspection time with no benefit to the "
            "customer.",
        ],
        "hard": [
            "A form is filled out in triplicate and routed through two extra approval "
            "signatures for a low-risk purchase, a holdover from a process designed for a much "
            "higher-risk category of purchase.",
            "An assembly step applies an extra coat of sealant beyond what the engineering "
            "specification requires, because an operator years ago believed it made the part "
            "look better, and the practice was never revisited.",
        ],
    },
    "Defects": {
        "standard": [
            "A batch of parts fails final inspection and has to be sorted, with the "
            "nonconforming units scrapped and the rest reworked before they can ship.",
            "A wiring error discovered at final test requires the unit to be partially "
            "disassembled and rewired before it can pass and ship to the customer.",
        ],
        "hard": [
            "A supplier's drawing revision was not updated on the shop floor, so an entire "
            "day's production ran against the old dimensions and now has to be 100% "
            "re-inspected and sorted before any of it can ship.",
            "A measurement fixture drifted out of calibration for a week without anyone "
            "noticing, and now every unit produced during that week has to be pulled back and "
            "re-checked.",
        ],
    },
    "Skills": {
        "standard": [
            "An experienced operator has repeatedly suggested a simple fixture change that "
            "would cut cycle time, but no one on the engineering team has ever asked for or "
            "acted on the idea.",
            "A technician with a background in electronics is kept doing purely manual "
            "assembly work and is never consulted when the line has a recurring electrical "
            "fault.",
        ],
        "hard": [
            "A new hire with prior process-improvement experience from a previous employer is "
            "never asked for input during a kaizen event on their own line, and the team "
            "solves the problem without her.",
            "A team lead who has cross-trained on three different stations is never included in "
            "scheduling discussions, even though that knowledge would help balance the line "
            "better during absences.",
        ],
    },
}


class LeanWasteGenerator(Generator):
    name = "lean_waste"

    def generate(self, seed: int, difficulty: str = "standard") -> dict[str, Any]:
        rng = random.Random(seed)

        waste = rng.choice(sorted(WASTES))
        pool_key = "standard" if difficulty == "standard" else "hard"
        scenario = rng.choice(SCENARIOS[waste][pool_key])

        options = "\n".join(f"{name} - {desc}" for name, desc in WASTES.items())
        prompt = (
            "The following was observed on a manufacturing shop floor:\n\n"
            f"\"{scenario}\"\n\n"
            "The eight wastes of Lean (TIMWOODS) are:\n"
            f"{options}\n\n"
            "Which single waste does this scenario primarily demonstrate? Respond with just "
            "the waste name."
        )

        return {
            "id": f"source.lean_waste.{seed:06d}",
            "family": "source_grounded",
            "domain": "continuous_improvement",
            "reasoning_tier": "L2",
            "answer_format": "classification",
            "prompt": prompt,
            "context": {"scenario": scenario, "wastes": WASTES},
            "ground_truth": {"value": waste},
            "scorer": "classification",
            "generator": self.name,
            "seed": seed,
            "difficulty": difficulty,
            "source": SOURCE,
            "source_url": SOURCE_URL,
            "created": datetime.now(timezone.utc).date().isoformat(),
            "public": True,
        }
