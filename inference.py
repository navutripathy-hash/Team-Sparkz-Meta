"""
inference.py -- AuditRepairEnv++ Baseline Inference Agent
=========================================================
OpenEnv Submission | Cost-Constrained Ledger Repair

STDOUT format (strict -- must match exactly):

[START]
Task: easy

[STEP]
Action: FIX_ENTRY 1
Reward: 0.2

[END]
Final Score: 0.85

Uses OpenAI Client for LLM calls.
Reads env variables: API_BASE_URL, MODEL_NAME, HF_TOKEN
Runs all tasks: easy, medium, hard
"""

import asyncio
import json
import os
import textwrap
import urllib.request
import urllib.error
from typing import List, Optional

from openai import OpenAI


# ──────────────────────────────────────────────────────────
# ENVIRONMENT CONFIGURATION
# ──────────────────────────────────────────────────────────
HF_TOKEN     = os.getenv("HF_TOKEN")
API_KEY      = HF_TOKEN or os.getenv("API_KEY", "")
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME   = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")

# Validate HF_TOKEN before proceeding
if not HF_TOKEN:
    raise ValueError(
        "HF_TOKEN environment variable is required. "
        "Set it via: export HF_TOKEN='your_token_here'"
    )
if not API_KEY:
    raise ValueError(
        "API_KEY environment variable must be set (or HF_TOKEN)"
    )

# Environment server URL
ENV_BASE_URL = os.getenv("ENV_BASE_URL", "http://localhost:7860")

BENCHMARK    = "auditrepairenv"
TASKS        = ["easy", "medium", "hard"]

MAX_STEPS               = 15
MAX_TOTAL_REWARD         = 2.0
SUCCESS_SCORE_THRESHOLD = 0.5
TEMPERATURE             = 0.2
MAX_TOKENS              = 300


# ──────────────────────────────────────────────────────────
# STDOUT LOGGING (strict OpenEnv format)
# ──────────────────────────────────────────────────────────
def log_start(task: str) -> None:
    print(f"\n[START]\nTask: {task}", flush=True)


def log_step(action: str, reward: float) -> None:
    action_clean = action.replace("\n", " ").replace("\r", "").strip()[:200]
    print(f"\n[STEP]\nAction: {action_clean}\nReward: {reward}", flush=True)


def log_end(score: float) -> None:
    print(f"\n[END]\nFinal Score: {score}", flush=True)


# ──────────────────────────────────────────────────────────
# ENVIRONMENT HTTP CLIENT (calls our OpenEnv server)
# ──────────────────────────────────────────────────────────
def env_request(path: str, method: str = "GET", body: dict = None) -> dict:
    url = ENV_BASE_URL.rstrip("/") + path
    data = json.dumps(body or {}).encode() if body is not None else b"{}"
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode()[:100]}"}
    except Exception as ex:
        return {"error": str(ex)}


def env_reset(task_id: str) -> dict:
    return env_request("/reset", "POST", {"task_id": task_id})


def env_step(message: str) -> dict:
    return env_request("/step", "POST", {"message": message})


# ──────────────────────────────────────────────────────────
# AGENT PROMPT
# ──────────────────────────────────────────────────────────
SYSTEM_PROMPT = textwrap.dedent("""
    You are AuditRepairAgent -- an AI that repairs financial ledger inconsistencies.

    You are given a ledger with entries that may have errors (value != expected_value).
    Each entry has an id, value, expected_value, and dependencies list.

    Available actions (respond with exactly ONE per step):
        FIX_ENTRY <id>            -- Sets value = expected_value. May trigger dependency changes.
        ADJUST_ENTRY <id> <delta> -- Increment/decrement the entry's value by delta.
        REVERT_ENTRY <id>         -- Undo the last change to an entry.
        NO_OP                     -- Do nothing.

    Rules:
    1. Each action costs budget. Minimize total actions.
    2. Fixing an already-correct entry is overcorrection (penalty).
    3. Dependencies: fixing one entry may change expected_value of other entries.
    4. Goal: fix all errors within budget.

    Respond with ONLY the action, nothing else:
    FIX_ENTRY 3
""").strip()


def build_prompt(obs: dict, step_num: int, last_echoed: str,
                 last_reward: float, history: List[str]) -> str:
    """Build user prompt from the current observation."""
    ledger_str = ""
    for entry in obs.get("ledger", []):
        status = "OK" if entry["value"] == entry["expected_value"] else "ERR"
        deps = entry.get("dependencies", [])
        dep_str = f", deps={deps}" if deps else ""
        ledger_str += (
            f"  [{status}] id={entry['id']}: value={entry['value']}, "
            f"expected={entry['expected_value']}{dep_str}\n"
        )

    errors_str = ""
    for err in obs.get("errors", []):
        errors_str += (
            f"  Entry {err['entry_id']}: value={err['current_value']}, "
            f"expected={err['expected_value']}, delta={err['delta']}\n"
        )

    history_block = "\n".join(history[-3:]) if history else "None"

    return textwrap.dedent(f"""
        Task: {obs.get('task_description', '')}
        Step {step_num} of {obs.get('max_steps', 10)}

        Ledger:
{ledger_str}
        Current Errors:
{errors_str if errors_str else '  None -- all entries correct!'}
        Budget: {obs.get('remaining_budget', 0)} / {obs.get('initial_budget', 0)}
        Last result: {last_echoed}
        Last reward: {last_reward:+.2f}
        History: {history_block}

        Respond with the single best action (e.g. FIX_ENTRY 3):
    """).strip()


def get_model_message(client: OpenAI, step_num: int, obs: dict,
                      last_echoed: str, last_reward: float,
                      history: List[str]) -> str:
    """Get agent action from LLM, with fallback to heuristic."""
    try:
        prompt = build_prompt(obs, step_num, last_echoed, last_reward, history)
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
        )
        response = (completion.choices[0].message.content or "").strip()
        # Extract just the action line
        for line in response.split("\n"):
            line = line.strip()
            if line and any(
                line.upper().startswith(a)
                for a in ["FIX_ENTRY", "ADJUST_ENTRY", "REVERT_ENTRY", "NO_OP"]
            ):
                return line
        return response.split("\n")[0].strip() if response else "NO_OP"
    except Exception:
        # Silently fallback
        return _fallback_action(obs)


def _fallback_action(obs: dict) -> str:
    """Deterministic fallback: fix the first error found."""
    errors = obs.get("errors", [])
    if errors:
        return f"FIX_ENTRY {errors[0]['entry_id']}"
    return "NO_OP"


# ──────────────────────────────────────────────────────────
# RUN ONE TASK
# ──────────────────────────────────────────────────────────
def run_task(client: OpenAI, task_id: str) -> float:
    """Run a single task episode. Returns score in [0.0, 1.0]."""
    history: List[str] = []
    rewards: List[float] = []
    score = 0.0

    log_start(task=task_id)

    try:
        # Reset
        result = env_reset(task_id)
        if "error" in result:
            log_end(score=0.0)
            return 0.0

        obs = result
        last_echoed = obs.get("echoed_message", "")
        last_reward = 0.0

        max_steps = obs.get("max_steps", MAX_STEPS)

        for step in range(1, max_steps + 1):
            if obs.get("done", False):
                break

            # Get agent action (text message)
            message = get_model_message(
                client, step, obs, last_echoed, last_reward, history
            )

            # Step the environment
            step_result = env_step(message)

            if "error" in step_result and "observation" not in step_result:
                reward = 0.0
                done = False
                error = step_result["error"][:80]
            else:
                reward = float(step_result.get("reward", 0) or 0)
                done = bool(step_result.get("done", False))
                error = step_result.get("last_action_error")
                obs = step_result.get("observation", obs)

            rewards.append(reward)
            last_echoed = obs.get("echoed_message", "")
            last_reward = reward

            log_step(action=message, reward=reward)

            history.append(f"Step {step}: {message!r} -> reward {reward:+.2f}")

            if done:
                # Extract final score from info
                info = step_result.get("info", {})
                final_score = info.get("final_score")
                if final_score is not None:
                    score = float(final_score)
                break

        # Compute score if not set from server
        if score == 0.0 and rewards:
            score = sum(rewards) / MAX_TOTAL_REWARD if MAX_TOTAL_REWARD > 0 else 0.0

        score = min(max(score, 0.0), 1.0)

    except Exception:
        pass

    finally:
        log_end(score=score)

    return score


# ──────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────
async def main() -> None:
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    for task_id in TASKS:
        run_task(client, task_id)


if __name__ == "__main__":
    asyncio.run(main())