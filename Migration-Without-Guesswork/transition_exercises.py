"""Original fictional calculations; no platform, customer data or remote effects."""

import json
import math

STEPS = {
    "freeze": (10, ()),
    "apply": (12, ("freeze",)),
    "data": (18, ("apply",)),
    "access": (8, ("apply",)),
    "decide": (5, ("data", "access")),
    "switch": (5, ("decide",)),
    "check": (10, ("switch",)),
    "reopen": (5, ("check",)),
}


def schedule(steps):
    """Calculate dependency-only elapsed times from (duration, prerequisites) pairs.

    Durations are finite non-negative minutes. Each step starts after its slowest
    prerequisite. Independent steps assume separate available operators; resource
    contention, communication and failures are not modelled. Cycles are rejected."""
    result, visiting = ({}, set())

    def finish(name):
        """Resolve one step recursively, retaining results and detecting dependency cycles."""
        if name in result:
            return result[name]["finish"]
        if name in visiting:
            raise ValueError("dependency cycle")
        if name not in steps:
            raise ValueError("missing prerequisite: " + name)
        duration, deps = steps[name]
        if (
            isinstance(duration, bool)
            or not isinstance(duration, (int, float))
            or not math.isfinite(duration)
            or duration < 0
        ):
            raise ValueError("finite non-negative numeric duration required")
        visiting.add(name)
        start = max((finish(d) for d in deps), default=0)
        result[name] = {"start": start, "finish": start + duration}
        visiting.remove(name)
        return start + duration

    for name in steps:
        finish(name)
    return result


def latest_return_decision(window, return_time, allowance):
    """Return window minus return duration minus reserved allowance, in minutes.

    This clock calculation is usable only while the required pre-write state still
    exists. An accepted target business write can end that route before the clock limit.
    """
    if any(
        type(value) not in (int, float) or not math.isfinite(value)
        for value in (window, return_time, allowance)
    ):
        raise ValueError("finite numeric times required")
    if min(window, return_time, allowance) < 0:
        raise ValueError("negative time")
    deadline = window - return_time - allowance
    if deadline < 0:
        raise ValueError("return does not fit the window")
    return deadline


def prewrite_return_available(elapsed, target_work_accepted):
    """Check the fictional minute-60 clock bound and absence of accepted target work.

    Controlled business writes count. Unknown acceptance must be treated as
    possibly accepted by the operator; do not pass False merely because a reply was lost.
    """
    if type(elapsed) not in (int, float) or not math.isfinite(elapsed) or elapsed < 0:
        raise ValueError("elapsed must be finite non-negative minutes")
    if type(target_work_accepted) is not bool:
        raise ValueError(
            "target_work_accepted must be an explicit Boolean; investigate unknown state"
        )
    return elapsed <= latest_return_decision(90, 20, 10) and (not target_work_accepted)


def go_decision_on_time(completed_at):
    """Return whether the decision is completed at or before the hard minute-55 cutoff.

    Data arriving at 55 is not a completed decision; this function expects decision
    completion time, not evidence arrival time."""
    if (
        type(completed_at) not in (int, float)
        or not math.isfinite(completed_at)
        or completed_at < 0
    ):
        raise ValueError("completed_at must be finite non-negative minutes")
    return completed_at <= 55


BASE = {"T1/O-101": 4000, "T1/O-102": 6500, "T1/O-105": 5000, "T1/O-106": 2500}
JOURNAL = (
    ("insert", "T1/O-107", None, 3000),
    ("insert", "T1/O-108", None, 4500),
    ("update", "T1/O-102", 6500, 7000),
)
EXPECTED = {
    "T1/O-101": 4000,
    "T1/O-102": 7000,
    "T1/O-105": 5000,
    "T1/O-106": 2500,
    "T1/O-107": 3000,
    "T1/O-108": 4500,
}


def reconstruct(base, journal):
    """Apply an ordered, complete fictional journal to a copy of the baseline.

    Before-value checks reject mismatched updates and repeated inserts. This is
    not an idempotent replay engine: the journal must preserve order and obligations.
    A populated database alone does not prove invoice outcomes or service recovery."""
    state = dict(base)
    for op, key, before, after in journal:
        if op == "insert":
            if key in state:
                raise ValueError("insert conflict: " + key)
            state[key] = after
        elif op == "update":
            if key not in state or state[key] != before:
                raise ValueError("update conflict: " + key)
            state[key] = after
        else:
            raise ValueError("unsupported teaching operation")
    return state


class Authority:
    """Illustrate SOURCE/NONE/TARGET authority states, not distributed write fencing.

    NONE means neither side accepts business writes. Every change of writer passes
    through NONE; a verified flag is a caller assertion, not actual platform proof."""

    def __init__(self):
        """Start the logical teaching model with source write authority."""
        self.state = "SOURCE"

    def move(self, destination, verified=False):
        """Change logical authority only through NONE and require verification to open writes."""
        if (self.state, destination) not in {
            ("SOURCE", "NONE"),
            ("TARGET", "NONE"),
            ("NONE", "SOURCE"),
            ("NONE", "TARGET"),
        }:
            raise ValueError("unsupported authority transition")
        if destination != "NONE" and (not verified):
            raise ValueError("verification gate required")
        self.state = destination
        return self.state


def run():
    """Return the book’s cutover variants, reconstruction and logical authority example."""
    delayed_data = dict(STEPS, data=(33, ("apply",)))
    delayed_access = dict(STEPS, access=(24, ("apply",)))
    restored = reconstruct(BASE, JOURNAL)
    authority = Authority()
    states = [authority.state, authority.move("NONE"), authority.move("TARGET", True)]
    return {
        "planned": schedule(STEPS),
        "delayed_data": schedule(delayed_data),
        "delayed_access": schedule(delayed_access),
        "clock_only_pre_write_return_limit_minute": latest_return_decision(90, 20, 10),
        "planned_first_business_write_minute": 50,
        "hard_go_decision_cutoff_minute": 55,
        "delayed_data_forward_schedule_is_executed": False,
        "post_write_orders": restored,
        "post_write_rows": len(restored),
        "post_write_total_minor": sum(restored.values()),
        "exact_teaching_population_matches": restored == EXPECTED,
        "logical_authority_states": states,
        "fictional_timely_correct_fraction": 1990 / 2000,
        "scope": "fictional arithmetic and logical models; not service acceptance",
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
