"""5S workplace-organization phase-classification generator.

The five phases of 5S (Sort, Set In Order, Shine, Standardize, Sustain -- Seiri, Seiton, Seiso,
Seiketsu, Shitsuke) are a canonical, widely published Lean structure. Ground truth here is that
fixed, cited structure -- never a model's opinion, per GOALS.md's non-negotiable rule: given a
paraphrased description of one workplace-organization activity, the correct phase is whichever
one that activity actually belongs to in the canonical structure, a fixed lookup, not a
judgment call.

Per SPEC.md's Family B licensing rule: no source text is reproduced anywhere below. Every
activity description is an original paraphrase of the general, freely published purpose of each
phase (see SOURCE_URL), not a quotation from any paywalled text.
"""
from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any

from generators.base import Generator

SOURCE = "ASQ -- 5S: What are The Five S's of Lean?"
SOURCE_URL = "https://asq.org/quality-resources/five-s-tutorial"

#: The canonical 5 phases of 5S, in order: phase name -> its purpose.
PHASES: dict[str, str] = {
    "Sort": "Remove items that are not needed for current operations from the work area, "
    "keeping only what is actually used",
    "Set In Order": "Arrange the items that remain so each has a clear, labeled place and can "
    "be quickly found, used, and put back",
    "Shine": "Clean the work area and equipment, using the cleaning process itself as a way to "
    "inspect for wear, leaks, or other problems",
    "Standardize": "Establish agreed-upon procedures and visual controls so Sort, Set In Order, "
    "and Shine are maintained the same way by everyone",
    "Sustain": "Build the habits, audits, and discipline needed to keep the standardized "
    "practices going over time, rather than slipping back to the old way",
}

#: Original paraphrases of a concrete activity performed during each phase. "hard" entries are
#: written to be easy to confuse with an adjacent phase, requiring closer reading than
#: "standard" entries.
ACTIVITIES: dict[str, dict[str, list[str]]] = {
    "Sort": {
        "standard": [
            "The team tagged every tool and fixture in the cell that had not been used in over "
            "a year and removed the tagged items from the work area.",
            "Broken jigs and obsolete work instructions were pulled out of the tool crib and "
            "discarded, leaving only what the current process actually needs.",
        ],
        "hard": [
            "A cross-functional team reviewed every item on the workbench against the current "
            "job's requirements and removed anything not needed for that job, before deciding "
            "where the remaining items should live.",
            "Spare parts left over from a discontinued product line were identified and hauled "
            "out of the cell, freeing up bench space that had not yet been reorganized.",
        ],
    },
    "Set In Order": {
        "standard": [
            "Shadow boards were installed above the workbench so each remaining tool has one "
            "labeled, visible spot to hang.",
            "Bins for each part number were arranged in the sequence the assembler uses them, "
            "with labels showing exactly which part goes where.",
        ],
        "hard": [
            "After the unneeded fixtures had already been cleared out, the team laid out the "
            "remaining ones by frequency of use, closest first, and labeled each spot on the "
            "bench.",
            "Floor markings were painted to define exactly where each cart and bin belongs, so "
            "anything out of place is immediately obvious at a glance.",
        ],
    },
    "Shine": {
        "standard": [
            "At the end of each shift, operators now wipe down the machine and sweep the "
            "surrounding floor, checking for oil leaks or loose fittings while they clean.",
            "A cleaning schedule was posted for the cell, and operators use the daily wipe-down "
            "to also look for early signs of wear on the equipment.",
        ],
        "hard": [
            "Once the shadow boards and labeled bins were in place, the team added a five-minute "
            "cleaning routine before every shift change so buildup around the equipment is "
            "caught before it becomes a bigger problem.",
            "A machine's coolant residue is now wiped away daily as part of routine cleaning, "
            "which recently helped an operator spot a small crack in a guard before it failed.",
        ],
    },
    "Standardize": {
        "standard": [
            "A one-page visual standard was created showing the agreed layout, cleaning "
            "checklist, and labeling scheme so every shift maintains the cell the same way.",
            "The team wrote a short checklist combining the cell's sorting rules, storage "
            "locations, and cleaning tasks so any operator on any shift follows the same "
            "routine.",
        ],
        "hard": [
            "Color-coded labels and a shared checklist were rolled out across all three shifts "
            "so the cell looks and is maintained identically no matter who is working it, after "
            "each shift had previously organized it differently.",
            "Photos of the cell's correct condition were posted at eye level so every operator "
            "can compare the current state to the agreed standard at a glance.",
        ],
    },
    "Sustain": {
        "standard": [
            "A weekly audit checklist and a recurring calendar reminder were set up so a "
            "supervisor checks that the agreed 5S standard is still being followed months "
            "later.",
            "The plant manager now reviews a 5S scorecard for each cell every month to make "
            "sure the organization achieved earlier has not quietly slipped back.",
        ],
        "hard": [
            "Six months after the visual standard was posted, leadership added a recurring "
            "audit and a recognition program specifically because a few cells had started "
            "drifting back toward their old, cluttered layout.",
            "New hires are now walked through the cell's posted standard during onboarding, and "
            "their team lead re-checks their workspace against it a month later.",
        ],
    },
}


class FiveSGenerator(Generator):
    name = "five_s"

    def generate(self, seed: int, difficulty: str = "standard") -> dict[str, Any]:
        rng = random.Random(seed)

        phase = rng.choice(list(PHASES))
        pool_key = "standard" if difficulty == "standard" else "hard"
        activity = rng.choice(ACTIVITIES[phase][pool_key])

        options = "\n".join(f"{name} - {desc}" for name, desc in PHASES.items())
        prompt = (
            "During a workplace-organization (5S) effort on a manufacturing cell, the "
            f"following activity took place:\n\n\"{activity}\"\n\n"
            "The 5S phases are:\n"
            f"{options}\n\n"
            "Which single phase does this activity belong to? Respond with just the phase "
            "name."
        )

        return {
            "id": f"source.five_s.{seed:06d}",
            "family": "source_grounded",
            "domain": "continuous_improvement",
            "reasoning_tier": "L2",
            "answer_format": "classification",
            "prompt": prompt,
            "context": {"activity": activity, "phases": PHASES},
            "ground_truth": {"value": phase},
            "scorer": "classification",
            "generator": self.name,
            "seed": seed,
            "difficulty": difficulty,
            "source": SOURCE,
            "source_url": SOURCE_URL,
            "created": datetime.now(timezone.utc).date().isoformat(),
            "public": True,
        }
