"""
tasks.py -- AuditRepairEnv++ Core Environment
==============================================
Deterministic ledger repair environment with hidden dependency propagation.
Three difficulty tiers: easy (independent), medium (visible deps), hard (hidden 2-level cascading deps).

Safety guarantees:
  - Budget never goes negative
  - Out-of-range IDs return errors, never crash
  - step() always returns a valid observation
  - Scores strictly in [0.0, 1.0]
"""

import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ────────────────────────────────────────
# PYDANTIC MODELS
# ────────────────────────────────────────

class LedgerEntry(BaseModel):
    """Single ledger row."""
    id: int
    value: int
    expected_value: int
    dependencies: List[int] = Field(default_factory=list)


class AuditAction(BaseModel):
    """Parsed action from agent message."""
    action_type: str = Field(
        ..., description="FIX_ENTRY | ADJUST_ENTRY | REVERT_ENTRY | NO_OP"
    )
    target_id: Optional[int] = Field(
        default=None, description="Ledger entry ID to act on"
    )
    adjust_delta: Optional[int] = Field(
        default=None, description="+/- delta for ADJUST_ENTRY"
    )


class AuditObservation(BaseModel):
    """Full observation returned to agent -- OpenEnv compliant."""
    task_id: str
    task_description: str
    step: int
    max_steps: int
    ledger: List[LedgerEntry]
    errors: List[Dict[str, Any]]
    remaining_budget: int
    initial_budget: int
    done: bool = False
    echoed_message: str = ""
    last_action_result: Optional[str] = None
    last_action_error: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)


# ────────────────────────────────────────
# ACTION TEXT PARSER
# ────────────────────────────────────────

def parse_action_message(message: str) -> AuditAction:
    """
    Parse free-form text into an AuditAction.
    Accepted formats:
        FIX_ENTRY <id>
        ADJUST_ENTRY <id> <delta>
        REVERT_ENTRY <id>
        NO_OP
    Also handles 'ACTION:' prefix lines and regex fallback.
    """
    text = message.strip()

    # Extract ACTION: line if present
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.upper().startswith("ACTION:"):
            text = stripped[7:].strip()
            break

    parts = text.split()
    if not parts:
        return AuditAction(action_type="NO_OP")

    action_type = parts[0].upper().replace("-", "_")

    if action_type == "NO_OP":
        return AuditAction(action_type="NO_OP")

    if action_type == "FIX_ENTRY" and len(parts) >= 2:
        try:
            return AuditAction(action_type="FIX_ENTRY", target_id=int(parts[1]))
        except ValueError:
            pass

    if action_type == "ADJUST_ENTRY" and len(parts) >= 3:
        try:
            return AuditAction(
                action_type="ADJUST_ENTRY",
                target_id=int(parts[1]),
                adjust_delta=int(parts[2].replace("+", "")),
            )
        except ValueError:
            pass

    if action_type == "REVERT_ENTRY" and len(parts) >= 2:
        try:
            return AuditAction(action_type="REVERT_ENTRY", target_id=int(parts[1]))
        except ValueError:
            pass

    # Regex fallback for messy LLM output
    m = re.search(r"FIX_ENTRY\s+(\d+)", text, re.IGNORECASE)
    if m:
        return AuditAction(action_type="FIX_ENTRY", target_id=int(m.group(1)))

    m = re.search(r"ADJUST_ENTRY\s+(\d+)\s+([+-]?\d+)", text, re.IGNORECASE)
    if m:
        return AuditAction(
            action_type="ADJUST_ENTRY",
            target_id=int(m.group(1)),
            adjust_delta=int(m.group(2)),
        )

    m = re.search(r"REVERT_ENTRY\s+(\d+)", text, re.IGNORECASE)
    if m:
        return AuditAction(action_type="REVERT_ENTRY", target_id=int(m.group(1)))

    return AuditAction(action_type="NO_OP")


# ────────────────────────────────────────
# ENVIRONMENT
# ────────────────────────────────────────

class LedgerEnvironment:
    """
    Core environment with safety guarantees:
      - Budget never goes negative (checked before deduction)
      - Invalid IDs return error messages, never raise
      - All step results include a valid observation
      - Final score always in [0.0, 1.0]
    """

    def __init__(
        self,
        entries: List[Dict[str, Any]],
        budget: int,
        max_steps: int,
        task_id: str,
        task_description: str,
        action_cost: int = 1,
        hidden_deps: bool = False,
    ):
        self.initial_entries = [LedgerEntry(**e) for e in entries]
        self.ledger = [LedgerEntry(**e) for e in entries]
        self.initial_budget = budget
        self.remaining_budget = budget
        self.max_steps = max_steps
        self.task_id = task_id
        self.task_description = task_description
        self.action_cost = action_cost
        self.hidden_deps = hidden_deps
        self.step = 0
        self.done = False
        self.history: List[Dict[str, Any]] = []
        self.undo_stack: Dict[int, List[int]] = {}
        self.overcorrection_count = 0
        self._valid_ids = {e.id for e in self.ledger}
        self.optimal_steps = self._compute_optimal_steps()

    # ── HELPERS ──

    def _get_entry(self, entry_id: int) -> Optional[LedgerEntry]:
        for e in self.ledger:
            if e.id == entry_id:
                return e
        return None

    def _compute_optimal_steps(self) -> int:
        """Minimum FIX actions to solve all errors (ignoring propagation)."""
        return max(sum(1 for e in self.initial_entries if e.value != e.expected_value), 1)

    def _propagate_dependencies(self, entry_id: int) -> None:
        """
        When entry is fixed, update expected_value of ALL direct dependents.
        Propagation rule: dep.expected_value = entry.value + dep.id
        This creates cascading chains: A->B->C when B is also fixed later.
        """
        entry = self._get_entry(entry_id)
        if entry is None:
            return
        for dep_id in entry.dependencies:
            dep = self._get_entry(dep_id)
            if dep is not None:
                dep.expected_value = entry.value + dep.id

    def get_errors(self) -> List[Dict[str, Any]]:
        """List of entries where value != expected_value."""
        errors = []
        for e in self.ledger:
            if e.value != e.expected_value:
                err: Dict[str, Any] = {
                    "entry_id": e.id,
                    "current_value": e.value,
                    "expected_value": e.expected_value,
                    "delta": e.value - e.expected_value,
                }
                if not self.hidden_deps:
                    err["dependencies"] = e.dependencies
                errors.append(err)
        return errors

    def get_observation(self, echoed_message: str = "") -> AuditObservation:
        """Build current observation."""
        ledger_out = []
        for e in self.ledger:
            d = e.model_dump()
            if self.hidden_deps:
                d["dependencies"] = []
            ledger_out.append(LedgerEntry(**d))

        return AuditObservation(
            task_id=self.task_id,
            task_description=self.task_description,
            step=self.step,
            max_steps=self.max_steps,
            ledger=ledger_out,
            errors=self.get_errors(),
            remaining_budget=self.remaining_budget,
            initial_budget=self.initial_budget,
            done=self.done,
            echoed_message=echoed_message,
            last_action_result=None,
            last_action_error=None,
            context={
                "action_types": ["FIX_ENTRY", "ADJUST_ENTRY", "REVERT_ENTRY", "NO_OP"],
                "action_cost": self.action_cost,
                "hidden_dependencies": self.hidden_deps,
            },
        )

    # ── MAIN STEP ──

    def step_with_message(self, message: str) -> Dict[str, Any]:
        """
        Process agent text message as one environment step.
        ALL safety checks applied:
          - Budget checked BEFORE deduction
          - Invalid IDs rejected gracefully
          - Episode-done handled properly
        Returns dict with: observation, reward, done, result, error
        """
        if self.done:
            obs = self.get_observation(echoed_message=message)
            return {
                "observation": obs,
                "reward": 0.0,
                "done": True,
                "result": "Episode already finished.",
                "error": None,
            }

        action = parse_action_message(message)
        self.step += 1
        reward = 0.0
        info_msg = ""
        error = None

        # ── NO_OP ──
        if action.action_type == "NO_OP":
            info_msg = "No operation performed."

        # ── FIX_ENTRY ──
        elif action.action_type == "FIX_ENTRY":
            if action.target_id is None:
                error = "FIX_ENTRY requires a target_id."
                info_msg = error
            elif action.target_id not in self._valid_ids:
                error = f"Entry {action.target_id} does not exist. Valid IDs: {sorted(self._valid_ids)}"
                info_msg = error
            elif self.remaining_budget < self.action_cost:
                error = "Insufficient budget for this action."
                info_msg = error
            else:
                entry = self._get_entry(action.target_id)
                assert entry is not None  # guaranteed by _valid_ids check

                # Save undo state
                self.undo_stack.setdefault(entry.id, []).append(entry.value)

                was_wrong = entry.value != entry.expected_value
                entry.value = entry.expected_value
                self._propagate_dependencies(entry.id)
                self.remaining_budget -= self.action_cost

                if was_wrong:
                    reward = 0.2
                    info_msg = f"Fixed entry {entry.id} to {entry.value}."
                else:
                    self.overcorrection_count += 1
                    reward = -0.1
                    info_msg = f"Entry {entry.id} was already correct. Overcorrection penalty."

        # ── ADJUST_ENTRY ──
        elif action.action_type == "ADJUST_ENTRY":
            if action.target_id is None or action.adjust_delta is None:
                error = "ADJUST_ENTRY requires target_id and adjust_delta."
                info_msg = error
            elif action.target_id not in self._valid_ids:
                error = f"Entry {action.target_id} does not exist. Valid IDs: {sorted(self._valid_ids)}"
                info_msg = error
            elif self.remaining_budget < self.action_cost:
                error = "Insufficient budget for this action."
                info_msg = error
            else:
                entry = self._get_entry(action.target_id)
                assert entry is not None

                self.undo_stack.setdefault(entry.id, []).append(entry.value)
                entry.value += action.adjust_delta
                self.remaining_budget -= self.action_cost

                if entry.value == entry.expected_value:
                    reward = 0.15
                    info_msg = f"Adjusted entry {entry.id} to correct value {entry.value}."
                else:
                    reward = -0.05
                    info_msg = f"Adjusted entry {entry.id} to {entry.value} (expected {entry.expected_value})."

        # ── REVERT_ENTRY ──
        elif action.action_type == "REVERT_ENTRY":
            if action.target_id is None:
                error = "REVERT_ENTRY requires a target_id."
                info_msg = error
            elif action.target_id not in self._valid_ids:
                error = f"Entry {action.target_id} does not exist."
                info_msg = error
            elif self.remaining_budget < self.action_cost:
                error = "Insufficient budget for this action."
                info_msg = error
            elif action.target_id not in self.undo_stack or not self.undo_stack[action.target_id]:
                error = f"No previous value for entry {action.target_id}."
                info_msg = error
            else:
                entry = self._get_entry(action.target_id)
                assert entry is not None
                old_val = self.undo_stack[entry.id].pop()
                entry.value = old_val
                self.remaining_budget -= self.action_cost
                reward = 0.0
                info_msg = f"Reverted entry {entry.id} to {old_val}."

        # ── UNKNOWN ──
        else:
            error = f"Unknown action: {action.action_type}"
            info_msg = error

        # ── CHECK DONE CONDITIONS ──
        all_correct = all(e.value == e.expected_value for e in self.ledger)
        budget_exhausted = self.remaining_budget <= 0
        max_steps_hit = self.step >= self.max_steps

        if all_correct:
            self.done = True
            reward += 0.3  # completion bonus
            info_msg += " All entries correct! Ledger repaired."
        elif budget_exhausted:
            self.done = True
            info_msg += " Budget exhausted."
        elif max_steps_hit:
            self.done = True
            info_msg += " Max steps reached."

        obs = self.get_observation(echoed_message=message)
        obs.last_action_result = info_msg
        obs.last_action_error = error

        return {
            "observation": obs,
            "reward": round(reward, 4),
            "done": self.done,
            "result": info_msg,
            "error": error,
        }

    # ── SCORING ──

    def compute_final_score(self) -> float:
        """
        Deterministic grading:
          score = 0.5 * consistency + 0.3 * efficiency + 0.2 * budget_ratio
                  - overcorrection_penalty
        Always clamped to [0.0, 1.0].
        """
        total = len(self.ledger)
        correct = sum(1 for e in self.ledger if e.value == e.expected_value)
        consistency = correct / max(total, 1)

        actual = max(self.step, 1)
        efficiency = min(self.optimal_steps / actual, 1.0)

        budget_ratio = max(self.remaining_budget / max(self.initial_budget, 1), 0.0)

        penalty = 0.05 * self.overcorrection_count

        raw = 0.5 * consistency + 0.3 * efficiency + 0.2 * budget_ratio - penalty

        return round(max(0.0, min(1.0, raw)), 4)


# ────────────────────────────────────────
# TASK LEDGERS
# ────────────────────────────────────────

def _make_easy_ledger() -> List[Dict[str, Any]]:
    """Easy: 5 independent entries, no dependencies, 3 errors."""
    return [
        {"id": 0, "value": 100, "expected_value": 100, "dependencies": []},
        {"id": 1, "value": 250, "expected_value": 200, "dependencies": []},
        {"id": 2, "value": 300, "expected_value": 300, "dependencies": []},
        {"id": 3, "value": 400, "expected_value": 450, "dependencies": []},
        {"id": 4, "value": 600, "expected_value": 500, "dependencies": []},
    ]


def _make_medium_ledger() -> List[Dict[str, Any]]:
    """Medium: 8 entries with visible 1-level dependencies."""
    return [
        {"id": 0, "value": 100, "expected_value": 100, "dependencies": []},
        {"id": 1, "value": 180, "expected_value": 200, "dependencies": [3, 5]},
        {"id": 2, "value": 300, "expected_value": 300, "dependencies": []},
        {"id": 3, "value": 210, "expected_value": 203, "dependencies": [6]},
        {"id": 4, "value": 400, "expected_value": 400, "dependencies": []},
        {"id": 5, "value": 520, "expected_value": 205, "dependencies": []},
        {"id": 6, "value": 600, "expected_value": 609, "dependencies": []},
        {"id": 7, "value": 750, "expected_value": 700, "dependencies": []},
    ]


def _make_hard_ledger() -> List[Dict[str, Any]]:
    """
    Hard: 12 entries with HIDDEN 2-level dependency chains.

    Dependency graph (hidden from agent):
      Entry 0 -> [2, 4]       (level 0 root)
      Entry 1 -> [3]          (level 0 root)
      Entry 2 -> [5, 7]       (level 1 -- depends on 0)
      Entry 3 -> [6, 8]       (level 1 -- depends on 1)
      Entry 4 -> [9]          (level 1 -- depends on 0)
      Entry 5 -> [10]         (level 2 -- depends on 2 -> 0)
      Entry 6 -> [11]         (level 2 -- depends on 3 -> 1)
      Entry 7..11 -> []       (leaf nodes)

    Multi-level cascading chains:
      Fix 0 -> changes expected of 2,4 -> fix 2 -> changes expected of 5,7
                                        -> fix 4 -> changes expected of 9
      Fix 1 -> changes expected of 3   -> fix 3 -> changes expected of 6,8
                                                 -> fix 6 -> changes expected of 11

    This creates TRUE 3-level cascading: 0->2->5->10 and 1->3->6->11
    Agent must discover propagation order without seeing dependencies.
    """
    return [
        {"id": 0,  "value": 100, "expected_value": 100, "dependencies": [2, 4]},
        {"id": 1,  "value": 250, "expected_value": 200, "dependencies": [3]},
        {"id": 2,  "value": 310, "expected_value": 102, "dependencies": [5, 7]},
        {"id": 3,  "value": 350, "expected_value": 203, "dependencies": [6, 8]},
        {"id": 4,  "value": 420, "expected_value": 104, "dependencies": [9]},
        {"id": 5,  "value": 500, "expected_value": 107, "dependencies": [10]},
        {"id": 6,  "value": 620, "expected_value": 209, "dependencies": [11]},
        {"id": 7,  "value": 700, "expected_value": 109, "dependencies": []},
        {"id": 8,  "value": 810, "expected_value": 211, "dependencies": []},
        {"id": 9,  "value": 900, "expected_value": 113, "dependencies": []},
        {"id": 10, "value": 150, "expected_value": 117, "dependencies": []},
        {"id": 11, "value": 220, "expected_value": 220, "dependencies": []},
    ]


# ────────────────────────────────────────
# TASK CONFIG & REGISTRY
# ────────────────────────────────────────

class TaskConfig:
    """Configuration for one task tier."""

    def __init__(
        self,
        task_id: str,
        name: str,
        difficulty: str,
        description: str,
        ledger_fn,
        budget: int,
        max_steps: int,
        action_cost: int,
        hidden_deps: bool,
    ):
        self.task_id = task_id
        self.name = name
        self.difficulty = difficulty
        self.description = description
        self.ledger_fn = ledger_fn
        self.budget = budget
        self.max_steps = max_steps
        self.action_cost = action_cost
        self.hidden_deps = hidden_deps

    def create_env(self) -> LedgerEnvironment:
        return LedgerEnvironment(
            entries=self.ledger_fn(),
            budget=self.budget,
            max_steps=self.max_steps,
            task_id=self.task_id,
            task_description=self.description,
            action_cost=self.action_cost,
            hidden_deps=self.hidden_deps,
        )


TASK_CONFIGS: Dict[str, TaskConfig] = {
    "easy": TaskConfig(
        task_id="easy",
        name="Easy Ledger Repair",
        difficulty="easy",
        description=(
            "Repair a financial ledger with 5 independent entries. "
            "3 entries contain errors (value != expected_value). "
            "No dependencies between entries. Fix all errors within budget."
        ),
        ledger_fn=_make_easy_ledger,
        budget=10,
        max_steps=10,
        action_cost=1,
        hidden_deps=False,
    ),
    "medium": TaskConfig(
        task_id="medium",
        name="Medium Ledger Repair",
        difficulty="medium",
        description=(
            "Repair a financial ledger with 8 entries and visible dependencies. "
            "Fixing one entry may change the expected_value of dependent entries. "
            "Moderate budget. Plan your repair sequence carefully."
        ),
        ledger_fn=_make_medium_ledger,
        budget=12,
        max_steps=15,
        action_cost=1,
        hidden_deps=False,
    ),
    "hard": TaskConfig(
        task_id="hard",
        name="Hard Ledger Repair",
        difficulty="hard",
        description=(
            "Repair a complex financial ledger with 12 entries and HIDDEN dependencies. "
            "Dependencies are NOT visible in observations. Fixing entries causes multi-level "
            "cascading changes (A->B->C chains). Tight budget -- minimize overcorrection."
        ),
        ledger_fn=_make_hard_ledger,
        budget=10,
        max_steps=15,
        action_cost=1,
        hidden_deps=True,
    ),
}

TASK_IDS = list(TASK_CONFIGS.keys())