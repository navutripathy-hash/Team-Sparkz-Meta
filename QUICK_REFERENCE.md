# Quick Reference — AuditRepairEnv++

## 🚀 Quick Start (5 minutes)

```bash
# 1. Set environment variables
export HF_TOKEN="hf_your_token_here"
export API_BASE_URL="https://router.huggingface.co/v1"
export MODEL_NAME="Qwen/Qwen2.5-72B-Instruct"

# 2. Install & run locally
pip install -r requirements.txt
python server.py &              # Terminal 1
python inference.py             # Terminal 2
```

## 📋 Required Files (Root Directory)

```
✅ inference.py         ← Main submission (MUST be at root)
✅ requirements.txt     ← Dependencies
✅ README.md            ← Documentation
✅ demo.py              ← Gradio UI
✅ Dockerfile           ← Docker config
✅ server.py            ← Environment server
✅ tasks.py             ← Task definitions
```

## 🔧 Key Code Snippets

### HF_TOKEN Validation (in inference.py)
```python
import os

HF_TOKEN = os.getenv("HF_TOKEN")
if not HF_TOKEN:
    raise ValueError("HF_TOKEN environment variable is required")

API_KEY = HF_TOKEN
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
```

### OpenAI Client (in inference.py)
```python
from openai import OpenAI

client = OpenAI(
    base_url=API_BASE_URL,
    api_key=API_KEY
)

response = client.chat.completions.create(
    model=MODEL_NAME,
    messages=[
        {"role": "system", "content": "You are an audit repair agent..."},
        {"role": "user", "content": prompt}
    ],
    max_tokens=300,
    temperature=0.2
)
```

### Output Format (in inference.py)
```python
# Start
print("[START]")
print(f"Task: {task_id}")

# Each step
print("\n[STEP]")
print(f"Action: {action}")
print(f"Reward: {reward:.2f}")  # 2 decimals!

# End
print("\n[END]")
print(f"Final Score: {score:.2f}")
```

## 📊 Output Example

```
[START]
Task: easy

[STEP]
Action: FIX_ENTRY 1
Reward: 0.10

[STEP]
Action: FIX_ENTRY 3
Reward: 0.15

[STEP]
Action: NO_OP
Reward: 0.00

[END]
Final Score: 0.85
```

## 🐳 Docker Commands

```bash
# Build
docker build -t audit-repair-env:latest .

# Run with env vars
docker run -p 7860:7860 \
  -e HF_TOKEN="hf_..." \
  -e API_BASE_URL="https://router.huggingface.co/v1" \
  audit-repair-env:latest

# Check logs
docker logs <container_id>

# Stop container
docker stop <container_id>
```

## 🌐 HF Spaces in 3 Steps

1. **Create Space** (huggingface.co/spaces/create)
   - SDK: Docker
   - Name: audit-repair-env
   - License: MIT

2. **Link GitHub** (Space → Settings → "Linked Repository")
   - Choose your repo
   - Sync mode: ON

3. **Set Secrets** (Space → Settings → "Repository secrets")
   - `HF_TOKEN=hf_...`
   - `API_BASE_URL=https://router.huggingface.co/v1`
   - `MODEL_NAME=Qwen/Qwen2.5-72B-Instruct`

**Wait for build (5-10 min) → Space runs automatically**

## 🧪 Testing Commands

```bash
# Test inference script
python inference.py

# Test environment server
curl -X POST http://localhost:7860/reset \
  -d '{"task_id":"easy"}' \
  -H "Content-Type: application/json"

# Test Docker
docker run -p 7860:7860 audit-repair-env:latest

# Test HF Space
curl -X POST https://your-space.hf.space/reset \
  -d '{"task_id":"easy"}' \
  -H "Content-Type: application/json"
```

## ❌ Common Mistakes

| ❌ Wrong | ✅ Correct |
|---------|-----------|
| `src/inference.py` | `./inference.py` (root) |
| No HF_TOKEN validation | `raise ValueError(...)` if missing |
| Using `requests` library | Use OpenAI client |
| Output: `[START]` only | `[START]` + `Task: ...` |
| Reward: `0.1` | Reward: `0.10` (2 decimals!) |
| Booleans: `True` | Booleans: `true` |
| Missing `[END]` | Always print `[END]` |
| Space: private | Must be PUBLIC |
| No step count | Step count must match |

## 🗑️ .gitignore Template

```
# Environment
.env
.env.local
*.key

# Secrets
secrets/
hf_token.txt

# Python
__pycache__/
*.pyc
*.pyo
.pytest_cache/

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db
```

## 📝 Dockerfile Template

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 7860

CMD ["python", "demo.py"]
```

## 🎯 Pitch Talking Points

**30 seconds:**
> "AuditRepairEnv++ is an RL environment where agents repair financial ledgers with interdependent errors under budget constraints. It benchmarks multi-step planning."

**2 minutes:**
1. Problem: Ledger errors cascade
2. Solution: RL environment with dependencies
3. Impact: Automates auditing
4. Demo: Watch it work

**Key metrics:**
- Easy: 90% success
- Medium: 70% success
- Hard: 55% success

## 🔗 Important Links

| Resource | URL |
|----------|-----|
| GitHub Create Repo | https://github.com/new |
| HF Spaces Create | https://huggingface.co/spaces/create |
| HF Token Settings | https://huggingface.co/settings/tokens |
| OpenAI Docs | https://github.com/openai/openai-python |
| Gradio Docs | https://www.gradio.app/ |
| HF Spaces Docs | https://huggingface.co/docs/hub/spaces |

## 📖 Documentation Files

- **README.md** — Problem, solution, setup, results
- **PITCH.md** — Project pitch, comparison, narrative
- **HF_SPACES_GUIDE.md** — Detailed deployment + troubleshooting
- **SUBMISSION_CHECKLIST.md** — Pre-submission validation
- **QUICK_REFERENCE.md** — This file!

## ⚡ Environment Variables Recap

```bash
# Required
HF_TOKEN="hf_your_actual_token"

# Optional (have defaults)
API_BASE_URL="https://router.huggingface.co/v1"
MODEL_NAME="Qwen/Qwen2.5-72B-Instruct"
ENV_BASE_URL="http://localhost:7860"
```

## 🏆 Success Criteria Checklist

- [ ] `inference.py` at root
- [ ] HF_TOKEN validation present
- [ ] Output format correct (all 5 components)
- [ ] GitHub repo public
- [ ] HF Spaces running
- [ ] README complete
- [ ] Pitch prepared
- [ ] No secrets in code/Docker

## 🆘 Quick Troubleshooting

**"ModuleNotFoundError: openai"**
```bash
pip install openai>=1.30.0
```

**"HF_TOKEN not set"**
```bash
export HF_TOKEN="hf_..."
```

**"Connection refused"**
- Make sure `server.py` is running
- Check port: `python server.py`

**"Docker build fails"**
- Check `requirements.txt` syntax
- Run `pip install -r requirements.txt` locally first

**"HF Space shows error"**
- Check Logs tab
- Verify secrets are set
- Check Dockerfile syntax

**"Space sleeps after 48 hours"**
- Upgrade to HF Pro, or
- Add uptime monitoring ping

---

**Print this page and keep it handy! 📋**

**Status**: ✅ Ready to submit  
**Last updated**: April 2025
