"""8D (Eight Disciplines) problem-solving discipline-classification generator.

The 8 disciplines (plus D0) of the 8D corrective-action methodology are a canonical, widely
published structure (ASQ, AIAG, and dozens of free industry references all describe the same
nine steps under the same D0-D8 labels). Ground truth here is that fixed, cited structure --
never a model's opinion, per GOALS.md's non-negotiable rule: given a paraphrased description of
one activity performed during a corrective-action investigation, the correct discipline is
whichever one that activity actually belongs to in the canonical structure, a fixed lookup, not
a judgment call.

Per SPEC.md's Family B licensing rule: no standard text is reproduced anywhere below. Every
activity description is an original paraphrase of the general, freely published purpose of each
discipline (see SOURCE_URL), not a quotation from any paywalled AIAG manual.
"""
from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any

from generators.base import Generator

SOURCE = "ASQ -- What is 8D? Eight Disciplines Problem Solving Process"
SOURCE_URL = "https://asq.org/quality-resources/eight-disciplines-8d"

#: The canonical 8D structure: discipline code -> its purpose, in canonical D0-D8 order.
DISCIPLINES: dict[str, str] = {
    "D0": (
        "Plan and prepare for the 8D process (confirm the issue warrants a full 8D; take any "
        "needed emergency response action)"
    ),
    "D1": "Establish the team",
    "D2": "Describe the problem",
    "D3": "Develop and implement interim containment action(s)",
    "D4": "Determine and verify the root cause(s) (and the escape point)",
    "D5": "Choose and verify permanent corrective action(s)",
    "D6": "Implement and validate the permanent corrective action",
    "D7": "Prevent recurrence",
    "D8": "Recognize the team and close out",
}

#: Original paraphrases of each discipline's purpose, as a concrete activity a team might
#: perform. "hard" entries are deliberately written to be easy to confuse with an adjacent
#: discipline (e.g. D5 "select a fix" vs. D6 "roll it out"), requiring closer reading than
#: "standard" entries.
ACTIVITIES: dict[str, dict[str, list[str]]] = {
    "D0": {
        "standard": [
            "Before any team was assigned, a manager reviewed the initial customer complaint "
            "and decided the issue was serious enough to open a formal corrective-action "
            "investigation.",
            "The engineer logged the initial symptoms reported by the customer and confirmed "
            "emergency containment was needed before a full investigation began.",
        ],
        "hard": [
            "The plant manager authorized an emergency shipment hold on the affected part "
            "number the same day the complaint arrived, before any team had been assigned to "
            "investigate.",
            "A quality coordinator screened the incoming complaint against the criteria for "
            "opening a formal corrective-action report and decided this one qualified.",
        ],
    },
    "D1": {
        "standard": [
            "A cross-functional team of quality, engineering, and production representatives "
            "was assembled and given the authority and time to work the problem.",
            "Management appointed a team leader and identified which departments needed to "
            "contribute expertise to the investigation.",
        ],
        "hard": [
            "The team leader confirmed that every person assigned to the investigation "
            "actually had the process knowledge needed for this specific defect, before any "
            "analysis started.",
            "A champion was named to remove roadblocks for the newly formed investigation team "
            "and free up their time from other duties.",
        ],
    },
    "D2": {
        "standard": [
            "The team documented exactly what the defect was, where it was found, when it "
            "started, and how many units were affected, in specific, quantified terms.",
            "An is/is-not analysis was completed to bound precisely where the defect does and "
            "does not occur.",
        ],
        "hard": [
            "The team compared the defective units against similar, unaffected parts to "
            "precisely scope which conditions the problem occurs under, before forming any "
            "theory about its cause.",
            "The investigation team converted a vague field complaint into a specific "
            "statement of what, where, when, and how many, without yet proposing why it "
            "happened.",
        ],
    },
    "D3": {
        "standard": [
            "All suspect stock in the warehouse and in transit was quarantined and 100% sorted "
            "so no more defective parts could reach the customer while root-cause work "
            "continued.",
            "A temporary inspection step was added on the line to catch the defect before "
            "shipment, while the permanent fix was still being investigated.",
        ],
        "hard": [
            "Extra sorting stations were staffed at the customer's dock as a stop-gap measure, "
            "even though the underlying cause of the defect had not yet been identified.",
            "A temporary work-around was put in place to protect the customer while the team "
            "was still narrowing down which process step was actually causing the defect.",
        ],
    },
    "D4": {
        "standard": [
            "The team used a fishbone diagram and 5-Why analysis on the process data to "
            "identify the true cause of the nonconformance.",
            "The team ran a designed experiment varying suspected process inputs and confirmed "
            "which one actually produced the defect.",
        ],
        "hard": [
            "In addition to identifying why the defect occurred, the team investigated why the "
            "existing inspection process failed to catch it before shipment.",
            "The team statistically verified that the suspected cause, when reproduced "
            "deliberately, generated the same defect every time.",
        ],
    },
    "D5": {
        "standard": [
            "The team evaluated several candidate fixes against the confirmed root cause and "
            "selected the one that eliminated it without introducing new risks, verifying it "
            "on a pilot batch before rollout.",
            "A trial of the proposed corrective action was completed and its results were "
            "compared against acceptance criteria before the fix was approved for full "
            "production.",
        ],
        "hard": [
            "The team ran a small-scale validation of the chosen fix and confirmed it "
            "addressed the root cause identified earlier, without yet rolling it out to full "
            "production.",
            "Of three candidate corrective actions, the team picked the one best suited to "
            "eliminate the confirmed root cause, but had not yet installed it on the line.",
        ],
    },
    "D6": {
        "standard": [
            "The approved corrective action was rolled out to full production, the interim "
            "containment actions were removed, and follow-up data confirmed the defect no "
            "longer occurred.",
            "After implementation, the team tracked several weeks of production data to "
            "confirm the defect rate dropped to zero before declaring the fix effective.",
        ],
        "hard": [
            "Once production data confirmed the defect was gone under full-volume conditions, "
            "the temporary sorting station that had been screening parts was finally removed.",
            "The corrective action already selected and piloted in the prior step was now "
            "installed on every affected line and its effectiveness confirmed with real "
            "production data.",
        ],
    },
    "D7": {
        "standard": [
            "The control plan, FMEA, and work instructions were updated, and the lesson "
            "learned was shared with other lines making similar parts so the same failure mode "
            "could not recur.",
            "Standard operating procedures and training materials were revised to build in the "
            "fix so the same mistake could not repeat on future designs or processes.",
        ],
        "hard": [
            "The team searched for other product lines or plants using a similar process and "
            "proactively updated their FMEAs and control plans, even though no defect had "
            "occurred there yet.",
            "Beyond fixing this specific part, the team updated the design-standards checklist "
            "so the same failure mode would be designed out of future, unrelated programs.",
        ],
    },
    "D8": {
        "standard": [
            "The team's contributions were formally recognized, the corrective-action report "
            "was closed out, and the results were documented for future reference.",
            "Management congratulated the team members by name and archived the completed "
            "corrective-action report.",
        ],
        "hard": [
            "The completed report, including lessons learned, was archived and the individuals "
            "who contributed were formally thanked before the team was disbanded.",
            "After the fix had already been implemented and validated with production data, "
            "the team's final report was signed off and filed, and the team was thanked for "
            "its work.",
        ],
    },
}


class EightDGenerator(Generator):
    name = "eight_d"

    def generate(self, seed: int, difficulty: str = "standard") -> dict[str, Any]:
        rng = random.Random(seed)

        discipline = rng.choice(sorted(DISCIPLINES))
        pool_key = "standard" if difficulty == "standard" else "hard"
        activity = rng.choice(ACTIVITIES[discipline][pool_key])

        options = "\n".join(f"{code} - {desc}" for code, desc in DISCIPLINES.items())
        prompt = (
            "During a formal 8D corrective-action investigation of a manufacturing "
            f"non-conformance, the following activity took place:\n\n\"{activity}\"\n\n"
            "The 8D disciplines are:\n"
            f"{options}\n\n"
            "Which single discipline (D0-D8) does this activity belong to? Respond with just "
            "the discipline code."
        )

        return {
            "id": f"source.eight_d.{seed:06d}",
            "family": "source_grounded",
            "domain": "quality_problem_solving",
            "reasoning_tier": "L2",
            "answer_format": "classification",
            "prompt": prompt,
            "context": {"activity": activity, "disciplines": DISCIPLINES},
            "ground_truth": {"value": discipline},
            "scorer": "classification",
            "generator": self.name,
            "seed": seed,
            "difficulty": difficulty,
            "source": SOURCE,
            "source_url": SOURCE_URL,
            "created": datetime.now(timezone.utc).date().isoformat(),
            "public": True,
        }
