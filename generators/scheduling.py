"""Scheduling generator.

Single-machine job sequencing: n jobs, each with a processing time, a due date, and (hard
difficulty only) a priority weight, all released at time 0, processed one at a time with no
preemption and no idle time. The ground truth is the minimum total (weighted) tardiness
achievable across every possible processing sequence, found by exhaustive search over all n!
permutations. n is kept small enough (5 for standard, 6 for hard) that brute force is exact and
tractable, so the reported "optimal" is provably correct -- never a model's opinion.
"""
from __future__ import annotations

import random
from datetime import datetime, timezone
from itertools import permutations
from typing import Any

from generators.base import Generator


class SchedulingGenerator(Generator):
    name = "scheduling"

    def generate(self, seed: int, difficulty: str = "standard") -> dict[str, Any]:
        rng = random.Random(seed)

        num_jobs = 5 if difficulty == "standard" else 6
        processing_times = [rng.randint(3, 15) for _ in range(num_jobs)]
        total_processing = sum(processing_times)

        due_low, due_high = (
            (round(0.5 * total_processing), round(1.3 * total_processing))
            if difficulty == "standard"
            else (round(0.3 * total_processing), round(1.1 * total_processing))
        )
        due_dates = [rng.randint(due_low, due_high) for _ in range(num_jobs)]

        weighted = difficulty != "standard"
        weights = [rng.randint(1, 5) for _ in range(num_jobs)] if weighted else [1] * num_jobs

        jobs = list(zip(processing_times, due_dates, weights))
        best_tardiness = min(
            self._total_tardiness(jobs, order) for order in permutations(range(num_jobs))
        )

        job_lines = "\n".join(
            f"Job {i + 1}: processing time = {p}, due date = {d}" + (f", weight = {w}" if weighted else "")
            for i, (p, d, w) in enumerate(jobs)
        )
        metric = "weighted tardiness" if weighted else "tardiness"

        prompt = (
            f"A single machine must process {num_jobs} jobs, all available at time 0, one at a "
            "time with no preemption (once started, a job runs to completion) and no idle time "
            "between jobs.\n\n"
            f"{job_lines}\n\n"
            "For a given sequence, each job's completion time is the sum of the processing "
            "times of every job up to and including it in that sequence. "
            "Tardiness for a job = max(0, completion time - due date). "
            + ("Weighted tardiness for a job = weight x tardiness. " if weighted else "")
            + f"Find the processing sequence that minimizes total {metric} across all jobs, "
            f"and report that minimum total {metric} value."
        )

        return {
            "id": f"compute.scheduling.{seed:06d}",
            "family": "computed",
            "domain": "production_scheduling",
            "reasoning_tier": "L4",
            "answer_format": "numeric",
            "prompt": prompt,
            "context": {
                "processing_times": processing_times,
                "due_dates": due_dates,
                "weights": weights,
            },
            "ground_truth": {
                "value": float(best_tardiness),
                "tolerance": 0.01,
                "tolerance_type": "absolute",
            },
            "scorer": "numeric",
            "generator": self.name,
            "seed": seed,
            "difficulty": difficulty,
            "source": None,
            "source_url": None,
            "created": datetime.now(timezone.utc).date().isoformat(),
            "public": True,
        }

    @staticmethod
    def _total_tardiness(jobs: list[tuple[int, int, int]], order: tuple[int, ...]) -> int:
        completion = 0
        total = 0
        for idx in order:
            processing_time, due_date, weight = jobs[idx]
            completion += processing_time
            total += weight * max(0, completion - due_date)
        return total
