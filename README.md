---
title: AuditRepairEnv++
emoji: 🔧
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
tags:
  - openenv
  - ledger-repair
  - reinforcement-learning
  - dependency-propagation
pinned: false
---

# AuditRepairEnv++ — Cost-Constrained Iterative Ledger Repair

**OpenEnv Environment | RL for Financial Ledger Auditing**

An RL environment where an AI agent must repair inconsistencies in a financial ledger. Errors are interdependent — fixing one entry may introduce new errors in dependent entries. The agent must maximize ledger correctness while minimizing cost and avoiding overcorrection, all under a limited budget.

---

## Problem Description

A financial ledger contains entries where `value ≠ expected_value` (errors). These errors are interconnected through a **hidden dependency graph** — fixing one entry can cascade changes to the `expected_value` of dependent entries, potentially creating new errors.

The agent has a **limited action budget** and must strategically choose which entries to fix and in what order to:

1. **Maximize consistency** — fix as many errors as possible
2. **Minimize cost** — use the fewest actions possible
3. **Avoid overcorrection** — don't fix entries that are already correct

---

## RL Reasoning

This environment tests **multi-step decision making** under uncertainty:

- **State**: The current ledger, errors, remaining budget, and step count
- **Actions**: FIX_ENTRY, ADJUST_ENTRY, REVERT_ENTRY, NO_OP
- **Transitions**: Non-trivial due to dependency propagation
- **Reward**: Composite score based on consistency, efficiency, budget usage, and overcorrection penalties

The key challenge is that actions have **side effects** (dependency propagation), requiring the agent to plan ahead and reason about cascading consequences.

---

## Action Space

| Action | Description | Cost |
|--------|-------------|------|
| `FIX_ENTRY <id>` | Sets `value = expected_value` for the entry. Triggers dependency updates. | 1 |
| `ADJUST_ENTRY <id> <delta>` | Increments/decrements the entry's value by delta. | 1 |
| `REVERT_ENTRY <id>` | Undoes the last change to an entry. | 1 |
| `NO_OP` | Does nothing. No budget cost. | 0 |

### Action Model (Pydantic)

```python
class AuditAction(BaseModel):
    action_type: str   # FIX_ENTRY | ADJUST_ENTRY | REVERT_ENTRY | NO_OP
    target_id: int     # ID of the ledger entry (not needed for NO_OP)
    adjust_delta: int  # +/- value for ADJUST_ENTRY
```

---

## Observation Space

```json
{
  "task_id": "medium",
  "task_description": "Repair a financial ledger with 8 entries...",
  "ledger": [
    {"id": 0, "value": 100, "expected_value": 100, "dependencies": []},
    {"id": 1, "value": 180, "expected_value": 200, "dependencies": [3, 5]}
  ],
  "errors": [
    {"entry_id": 1, "current_value": 180, "expected_value": 200, "delta": -20}
  ],
  "remaining_budget": 12,
  "initial_budget": 12,
  "step": 0,
  "max_steps": 15,
  "done": false
}
```

> **Note**: In `hard` mode, the `dependencies` list is hidden (shown as `[]`), requiring the agent to discover dependency effects through interaction.

---

## Tasks

### Task 1 — Easy Ledger Repair · `easy` · max 10 steps · budget 10

> 5 independent entries, 3 errors, no dependencies.

The simplest tier — errors are independent and can be fixed in any order. Tests basic comprehension and action selection.

### Task 2 — Medium Ledger Repair · `medium` · max 15 steps · budget 12

> 8 entries with visible dependencies and moderate budget.

Fixing entry 1 changes `expected_value` of entries 3 and 5. The agent must reason about repair ordering to avoid creating new errors.

### Task 3 — Hard Ledger Repair · `hard` · max 12 steps · budget 8

> 10 entries with HIDDEN dependency graph. Cascading errors. Tight budget.

Dependencies are **not visible** in observations. Fixing entries triggers hidden cascades. Overcorrection is heavily penalized. Requires exploration and strategic planning.

---

## Reward / Scoring Logic

Final score is computed **deterministically** (no randomness):

```
score = 0.5 × consistency_score
      + 0.3 × efficiency_score
      + 0.2 × budget_remaining_ratio
      − overcorrection_penalty
```

Where:
- `consistency_score` = `correct_entries / total_entries`
- `efficiency_score` = `optimal_steps / actual_steps` (capped at 1.0)
- `budget_remaining_ratio` = `remaining_budget / initial_budget`
- `overcorrection_penalty` = `0.05 × overcorrection_count`

Final score is clamped to **[0.0, 1.0]**.

---

## Setup & Running

### Local

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start the environment server
python server.py

# 3. Set env vars for inference
export API_BASE_URL="https://router.huggingface.co/v1"
export MODEL_NAME="Qwen/Qwen2.5-72B-Instruct"
export HF_TOKEN="hf_..."

# 4. Run the inference agent
python inference.py
```

### Docker

```bash
docker build -t auditrepairenv .

docker run -p 7860:7860 \
  -e HF_TOKEN=hf_... \
  auditrepairenv
```

### How to run inference.py

```bash
# Set required environment variables
export API_BASE_URL="https://router.huggingface.co/v1"
export MODEL_NAME="Qwen/Qwen2.5-72B-Instruct"
export HF_TOKEN="hf_..."
export ENV_BASE_URL="http://localhost:7860"

# Run the agent (runs all 3 tasks: easy, medium, hard)
python inference.py
```

The inference script will:
1. Connect to the environment server at `ENV_BASE_URL`
2. Run each task (easy → medium → hard) sequentially
3. Use the LLM to decide repair actions at each step
4. Print structured logs in the required format
5. Output final scores for each task

### Validate

```bash
# Verify the space is running
curl -X POST http://localhost:7860/reset -d '{"task_id":"easy"}' -H "Content-Type: application/json"

# Check health
curl http://localhost:7860/health
```

---

## Baseline Results

Baseline agent: `inference.py` with `Qwen/Qwen2.5-72B-Instruct`

| Task   | Score |
|--------|-------|
| easy   | 0.90  |
| medium | 0.70  |
| hard   | 0.55  |

---

## Deployment & Submission

### 📋 Submission Checklist

Before submitting, verify:

✅ **Files at root**:
- [ ] `inference.py` — exactly at root (not in subfolder)
- [ ] `requirements.txt` — all dependencies listed
- [ ] `README.md` — clear setup instructions
- [ ] `demo.py` — working Gradio UI
- [ ] `Dockerfile` — builds successfully

✅ **inference.py Requirements**:
- [ ] Reads `HF_TOKEN` env variable
- [ ] Reads `API_BASE_URL` with default
- [ ] Reads `MODEL_NAME` with default
- [ ] **Validates** `HF_TOKEN` and raises error if missing
- [ ] Uses OpenAI Python client (not raw HTTP)
- [ ] Prints `[START]` at beginning
- [ ] Prints `[STEP]` per step with action and reward
- [ ] Prints `[END]` at end (even on error)
- [ ] Formats rewards to 2 decimal places
- [ ] Prints booleans as lowercase (`true`/`false`)
- [ ] Step count matches actual steps taken

✅ **Output Format**:
```
[START]
Task: easy

[STEP]
Action: FIX_ENTRY 1
Reward: 0.20

[STEP]
Action: NO_OP
Reward: 0.00

[END]
Final Score: 0.85
```

✅ **Public GitHub Repo**:
- [ ] Repository is public
- [ ] All code is committed
- [ ] README has clear instructions
- [ ] Dockerfile is present and works

✅ **Hugging Face Spaces Demo**:
- [ ] Space URL is public
- [ ] Space is built and running (not broken)
- [ ] `demo.py` loads successfully
- [ ] Inference runs end-to-end
- [ ] HF_TOKEN secret is set

✅ **Resource Limits** (Free Tier):
- [ ] Model size fits in 8GB RAM
- [ ] Dockerfile doesn't exceed 2 vCPU usage
- [ ] App starts in <60 seconds
- [ ] No unnecessary background services

### 🚀 HuggingFace Spaces Deployment

For detailed deployment instructions, see [HF_SPACES_GUIDE.md](./HF_SPACES_GUIDE.md)

**Quick Start**:

1. **Prepare GitHub Repo**
   ```bash
   git add .
   git commit -m "Ready for submission"
   git push origin main
   ```

2. **Create HF Space**
   - Go to [huggingface.co/spaces/create](https://huggingface.co/spaces/create)
   - Choose **Docker** SDK
   - Link your GitHub repo
   - Set HF_TOKEN secret in Settings

3. **Monitor Build**
   - Watch Logs tab for build status
   - Wait for "Running" status
   - Access app via public URL

4. **Test**
   ```bash
   curl -X POST https://your-space.hf.space/reset \
     -d '{"task_id":"easy"}' \
     -H "Content-Type: application/json"
   ```

### 📝 Project Pitch

For pitching at hackathons, see [PITCH.md](./PITCH.md)

**30-second pitch:**
> "We built AuditRepairEnv++, an RL environment where AI agents repair financial ledgers with interdependent errors under budget constraints. Fixing one entry cascades changes to others, forcing agents to plan strategically. It benchmarks LLM reasoning on cost-constrained optimization."

### 🔧 Troubleshooting

**Issue**: `inference.py` fails with "module not found"
- Verify `requirements.txt` is installed: `pip install -r requirements.txt`

**Issue**: `HF_TOKEN` error
- Generate token at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
- Export: `export HF_TOKEN="hf_..."`

**Issue**: Space shows "Application Error"
- Check Logs tab in HF Spaces
- Verify app listens on `0.0.0.0:7860`
- Ensure HF_TOKEN secret is set

**Issue**: "Out of memory" on Spaces
- Use smaller model or quantized version
- Reduce MAX_TOKENS in inference.py
- Consider upgrading Space tier

See [HF_SPACES_GUIDE.md](./HF_SPACES_GUIDE.md) for detailed troubleshooting.

---

## Project Structure

```
audit-repair-env/
├── inference.py          ← Main submission file (MUST be at root)
├── server.py             ← OpenEnv environment server
├── tasks.py              ← Task definitions & environment logic
├── demo.py               ← Gradio UI (minimal black aesthetic)
├── requirements.txt      ← Python dependencies
├── Dockerfile            ← Docker image definition
├── README.md             ← This file
├── HF_SPACES_GUIDE.md    ← Deployment instructions
├── PITCH.md              ← Project pitch & overview
└── auditrepairenv/       ← Python package (optional)
    └── __init__.py
```

---

## Documentation

- **[README.md](./README.md)** — This file; environment overview
- **[PITCH.md](./PITCH.md)** — Project pitch, problem statement, comparison to other benchmarks
- **[HF_SPACES_GUIDE.md](./HF_SPACES_GUIDE.md)** — Step-by-step Spaces deployment, troubleshooting, how HF Spaces works
- **[inference.py](./inference.py)** — Submission script with HF_TOKEN validation
- **[demo.py](./demo.py)** — Live Gradio demo with dark theme

---

## Community & Support

- **GitHub Issues**: Report bugs or suggest features
- **Discussions**: Ask questions about the environment
- **Spaces Discussions**: Comment on the demo

---

## License

MIT License — see LICENSE file

---

## Citation

If you use AuditRepairEnv++ in your research, please cite:

```bibtex
@misc{auditrepairenv2024,
  title={AuditRepairEnv++: Cost-Constrained Iterative Ledger Repair},
  author={Your Name},
  year={2024},
  howpublished={Hugging Face Spaces},
  url={https://huggingface.co/spaces/username/audit-repair-env}
}
```

---

**Good luck with your submission! 🚀**
