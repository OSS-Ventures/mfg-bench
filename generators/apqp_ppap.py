"""APQP (Advanced Product Quality Planning) phase-classification and PPAP (Production Part
Approval Process) element-identification generators.

Both APQP's five phases and PPAP's eighteen elements are canonical, widely published
structures (see the *_SOURCE_URL constants below) -- fixed lookups, not a model's opinion, per
GOALS.md's non-negotiable rule.

Per SPEC.md's Family B licensing rule: no paywalled AIAG standard text is reproduced anywhere
below. Every phase activity and every PPAP element description is an original paraphrase of the
general, freely published purpose of that phase or element.
"""
from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any

from generators.base import Generator

APQP_SOURCE = "6Sigma.us -- Advanced Product Quality Planning (APQP)"
APQP_SOURCE_URL = (
    "https://www.6sigma.us/six-sigma-in-focus/advanced-product-quality-planning-apqp/"
)

PPAP_SOURCE = "Quality-One International -- PPAP: Production Part Approval Process"
PPAP_SOURCE_URL = "https://quality-one.com/ppap/"

#: The canonical 5 APQP phases, in order.
APQP_PHASES: dict[str, str] = {
    "Phase 1": "Plan and Define the Program",
    "Phase 2": "Product Design and Development",
    "Phase 3": "Process Design and Development",
    "Phase 4": "Product and Process Validation",
    "Phase 5": "Feedback, Assessment, and Corrective Action",
}

#: Original paraphrases of a concrete activity performed during each phase. "hard" entries are
#: written to be easy to confuse with an adjacent phase, requiring closer reading than
#: "standard" entries.
APQP_ACTIVITIES: dict[str, dict[str, list[str]]] = {
    "Phase 1": {
        "standard": [
            "The team gathered voice-of-customer input and translated it into a program plan "
            "with quality objectives, targets, and a timing chart.",
            "A preliminary bill of materials and product assurance plan were drafted based on "
            "the customer's initial requirements, before any detailed design work began.",
        ],
        "hard": [
            "Reliability and cost targets were finalized based on customer and management "
            "requirements, before any design or process work had started.",
        ],
    },
    "Phase 2": {
        "standard": [
            "The team ran a Design FMEA and built and tested prototypes to confirm the design "
            "would meet the customer's specifications.",
            "Design reviews were held and drawings were released after prototype testing "
            "verified the design intent was met.",
        ],
        "hard": [
            "Engineering specifications were converted into a design verification plan while "
            "the manufacturing process itself had not yet been laid out.",
        ],
    },
    "Phase 3": {
        "standard": [
            "The team created the process flow diagram, ran a Process FMEA, and drafted the "
            "control plan describing how the process would be monitored.",
            "Packaging standards and the plant floor layout were finalized based on the "
            "process flow already defined for this part.",
        ],
        "hard": [
            "Measurement systems for the process's key characteristics were selected and their "
            "capability evaluated, before any production trial run took place.",
        ],
    },
    "Phase 4": {
        "standard": [
            "A significant production run was completed at the intended line rate, and initial "
            "process-capability plus dimensional and functional test results were reviewed "
            "before sign-off.",
            "The team validated the process on a pilot production run and reviewed the results "
            "against the control plan before approving the part for full-volume production.",
        ],
        "hard": [
            "A run-at-rate trial confirmed the process could meet the customer's required "
            "volume, using the exact tooling and equipment intended for regular production.",
        ],
    },
    "Phase 5": {
        "standard": [
            "The team reviewed field and customer feedback after launch and used it to drive "
            "corrective actions and reduce variation going forward.",
            "Lessons learned from this program's launch were captured and fed back into future "
            "program planning.",
        ],
        "hard": [
            "Warranty and field-return data collected months after launch triggered a "
            "re-evaluation of the control plan for one of the part's key characteristics.",
        ],
    },
}

#: The 18 canonical PPAP elements: name -> an original paraphrase of what a package including
#: that element would contain.
PPAP_ELEMENTS: dict[str, str] = {
    "Design Records": "a copy of the released engineering drawing for the part",
    "Engineering Change Documents": (
        "documentation of engineering changes made since the last submission, where not "
        "already reflected on the design record"
    ),
    "Customer Engineering Approval": (
        "evidence of customer engineering approval, such as a signed customer drawing, where "
        "the customer requires it"
    ),
    "Design FMEA": "the design failure mode and effects analysis for the part",
    "Process Flow Diagram": (
        "a diagram of the process steps and their sequence used to produce the part"
    ),
    "Process FMEA": "the process failure mode and effects analysis for the manufacturing process",
    "Control Plan": (
        "the control plan describing how the process controls the part's and process's "
        "characteristics"
    ),
    "Measurement System Analysis Studies": (
        "gauge repeatability-and-reproducibility and other measurement-system studies for the "
        "gauges used"
    ),
    "Dimensional Results": (
        "a dimensional layout report showing measured results for every dimension on the "
        "drawing"
    ),
    "Material and Performance Test Results": (
        "test results demonstrating the part meets its material and performance specifications"
    ),
    "Initial Process Studies": (
        "initial process-capability study results for the process's key characteristics"
    ),
    "Qualified Laboratory Documentation": (
        "accreditation or qualification documentation for the laboratory that ran the tests"
    ),
    "Appearance Approval Report": (
        "a signed appearance approval report, for a part with appearance requirements"
    ),
    "Sample Production Parts": "a sample part taken from the initial production run",
    "Master Sample": "a retained master sample signed off by both the supplier and the customer",
    "Checking Aids": (
        "a record of the checking aids used to inspect the part, including their calibration"
    ),
    "Customer-Specific Requirements Records": (
        "records showing each customer-specific requirement has been met"
    ),
    "Part Submission Warrant": "a signed Part Submission Warrant summarizing the submission",
}


class ApqpPhaseGenerator(Generator):
    name = "apqp_phase"

    def generate(self, seed: int, difficulty: str = "standard") -> dict[str, Any]:
        rng = random.Random(seed)

        phase = rng.choice(sorted(APQP_PHASES, key=lambda p: int(p.split()[1])))
        pool_key = "standard" if difficulty == "standard" else "hard"
        activity = rng.choice(APQP_ACTIVITIES[phase][pool_key])

        options = "\n".join(f"{code} - {desc}" for code, desc in APQP_PHASES.items())
        prompt = (
            "During a new part's Advanced Product Quality Planning (APQP) program, the "
            f"following activity took place:\n\n\"{activity}\"\n\n"
            "The APQP phases are:\n"
            f"{options}\n\n"
            "Which single phase does this activity belong to? Respond with just the phase "
            "label (e.g. Phase 3)."
        )

        return {
            "id": f"source.apqp_phase.{seed:06d}",
            "family": "source_grounded",
            "domain": "compliance_interpretation",
            "reasoning_tier": "L2",
            "answer_format": "classification",
            "prompt": prompt,
            "context": {"activity": activity, "phases": APQP_PHASES},
            "ground_truth": {"value": phase},
            "scorer": "classification",
            "generator": self.name,
            "seed": seed,
            "difficulty": difficulty,
            "source": APQP_SOURCE,
            "source_url": APQP_SOURCE_URL,
            "created": datetime.now(timezone.utc).date().isoformat(),
            "public": True,
        }


class PpapElementsGenerator(Generator):
    name = "ppap_elements"

    def generate(self, seed: int, difficulty: str = "standard") -> dict[str, Any]:
        rng = random.Random(seed)

        num_items = 3 if difficulty == "standard" else 5
        all_elements = sorted(PPAP_ELEMENTS)
        included = sorted(rng.sample(all_elements, num_items))

        package_description = "; ".join(PPAP_ELEMENTS[name] for name in included)
        options = "\n".join(f"- {name}" for name in all_elements)
        prompt = (
            "A supplier's PPAP (Production Part Approval Process) submission package for a new "
            f"part included: {package_description}.\n\n"
            "The 18 canonical PPAP elements are:\n"
            f"{options}\n\n"
            "Which of the 18 canonical PPAP elements does this package's contents satisfy? "
            "List every element name that applies."
        )

        return {
            "id": f"source.ppap_elements.{seed:06d}",
            "family": "source_grounded",
            "domain": "compliance_interpretation",
            "reasoning_tier": "L2",
            "answer_format": "checklist",
            "prompt": prompt,
            "context": {"included_elements": included, "all_elements": all_elements},
            "ground_truth": {"required_items": included},
            "scorer": "checklist",
            "generator": self.name,
            "seed": seed,
            "difficulty": difficulty,
            "source": PPAP_SOURCE,
            "source_url": PPAP_SOURCE_URL,
            "created": datetime.now(timezone.utc).date().isoformat(),
            "public": True,
        }
