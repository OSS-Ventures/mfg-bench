"""SMED (Single-Minute Exchange of Die) internal-vs-external setup classification generator.

SMED's foundational, canonical distinction -- widely published in free Lean references -- is
between "internal setup" (a changeover step that can only be done while the machine or process
is stopped) and "external setup" (a changeover step that can be done while the machine or
process is still running, before or after the actual changeover). Ground truth here is that
fixed, cited distinction -- never a model's opinion, per GOALS.md's non-negotiable rule: given a
paraphrased description of one changeover step, the correct classification is whichever one that
step actually is, a fixed lookup, not a judgment call.

Per SPEC.md's Family B licensing rule: no source text is reproduced anywhere below. Every step
description is an original paraphrase of the general, freely published concept (see SOURCE_URL),
not a quotation from any paywalled text.
"""
from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any

from generators.base import Generator

SOURCE = "Lean Production -- SMED (Single-Minute Exchange of Die)"
SOURCE_URL = "https://www.leanproduction.com/smed/"

#: The canonical SMED classification: label -> its meaning.
CATEGORIES: dict[str, str] = {
    "Internal": "A changeover step that can only be performed while the machine or process is "
    "stopped",
    "External": "A changeover step that can be performed while the machine or process is still "
    "running, either before or after the actual changeover",
}

#: Original paraphrases of a concrete changeover step for each classification. "hard" entries
#: are written to be easy to mistake for the other category, requiring closer reading than
#: "standard" entries.
STEPS: dict[str, dict[str, list[str]]] = {
    "Internal": {
        "standard": [
            "Removing the old die from the press and bolting the new die into place.",
            "Physically swapping the mold cavity on the injection molding machine once "
            "production of the current part has stopped.",
        ],
        "hard": [
            "Fine-tuning the alignment of the newly installed die by making small adjustments "
            "and running trial shots until the first good part comes off the machine.",
            "Re-threading the material web through the machine's rollers after the previous "
            "roll has run out and the machine has already been stopped.",
        ],
    },
    "External": {
        "standard": [
            "Gathering the tools, fixtures, and the next die from the tool crib and staging "
            "them next to the machine while the current job is still running.",
            "Pre-heating the next mold to operating temperature on a separate stand while the "
            "current part is still being produced.",
        ],
        "hard": [
            "Checking and pre-setting the next die's shim thickness on a bench fixture while "
            "the current die is still mounted and running in the press.",
            "Confirming the next job's raw material has already been inspected and moved to a "
            "staging location beside the machine well before the current run finishes.",
        ],
    },
}


class SmedSetupClassificationGenerator(Generator):
    name = "smed"

    def generate(self, seed: int, difficulty: str = "standard") -> dict[str, Any]:
        rng = random.Random(seed)

        category = rng.choice(sorted(CATEGORIES))
        pool_key = "standard" if difficulty == "standard" else "hard"
        step = rng.choice(STEPS[category][pool_key])

        options = "\n".join(f"{name} - {desc}" for name, desc in CATEGORIES.items())
        prompt = (
            "During a machine changeover, the following step took place:\n\n"
            f"\"{step}\"\n\n"
            "In SMED (Single-Minute Exchange of Die) terms, a changeover step is classified "
            "as:\n"
            f"{options}\n\n"
            "Which classification does this step belong to? Respond with just the "
            "classification name."
        )

        return {
            "id": f"source.smed.{seed:06d}",
            "family": "source_grounded",
            "domain": "methods_industrialization",
            "reasoning_tier": "L2",
            "answer_format": "classification",
            "prompt": prompt,
            "context": {"step": step, "categories": CATEGORIES},
            "ground_truth": {"value": category},
            "scorer": "classification",
            "generator": self.name,
            "seed": seed,
            "difficulty": difficulty,
            "source": SOURCE,
            "source_url": SOURCE_URL,
            "created": datetime.now(timezone.utc).date().isoformat(),
            "public": True,
        }
