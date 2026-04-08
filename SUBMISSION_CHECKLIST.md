# Submission Checklist — AuditRepairEnv++

**Deadline**: [Your hackathon date]  
**Status**: Pre-submission validation

---

## Pre-Submission Technical Validation

### Phase 1: Local Validation ✅

Before pushing to GitHub, verify locally:

```bash
# 1. Test inference script
export HF_TOKEN="hf_your_test_token"
export API_BASE_URL="https://router.huggingface.co/v1"
export MODEL_NAME="Qwen/Qwen2.5-72B-Instruct"
export ENV_BASE_URL="http://localhost:7860"

# Start server in one terminal
python server.py

# In another terminal, test inference
python inference.py
```

**Check**:
- ✅ No import errors
- ✅ `[START]` printed
- ✅ `[STEP]` printed per step
- ✅ `[END]` printed at end
- ✅ Rewards formatted to 2 decimals
- ✅ Correct step count

### Phase 2: Docker Validation ✅

```bash
# Build Docker image
docker build -t audit-repair-env:latest .

# Run container
docker run -p 7860:7860 \
  -e HF_TOKEN="hf_your_token" \
  -e API_BASE_URL="https://router.huggingface.co/v1" \
  -e MODEL_NAME="Qwen/Qwen2.5-72B-Instruct" \
  audit-repair-env:latest

# Test in new terminal
curl -X POST http://localhost:7860/reset \
  -d '{"task_id":"easy"}' \
  -H "Content-Type: application/json"
```

**Check**:
- ✅ Docker builds without errors
- ✅ Container starts
- ✅ `/reset` endpoint responds
- ✅ Logs visible in container output

### Phase 3: File Structure ✅

```
project-root/
├── inference.py           ← MUST be at root (not subfolder)
├── requirements.txt       ← All dependencies listed
├── README.md              ← Clear setup + usage
├── demo.py                ← Gradio interface
├── Dockerfile             ← Present & valid
├── server.py              ← Environment server
├── tasks.py               ← Task definitions
├── HF_SPACES_GUIDE.md     ← Deployment guide
├── PITCH.md               ← Project pitch
└── [other supporting files]
```

**Check**:
- ✅ `inference.py` is at project root (not `src/` or `app/`)
- ✅ No `.py` files in subfolders are named `inference.py`
- ✅ All files committed to git
- ✅ `.gitignore` excludes secrets/tokens

### Phase 4: inference.py Validation ✅

```python
# Checklist for inference.py
```

**Environment variables**:
- ✅ Reads `HF_TOKEN` from `os.getenv("HF_TOKEN")`
- ✅ **Validates** HF_TOKEN and raises error if missing
- ✅ Reads `API_BASE_URL` with default `"https://router.huggingface.co/v1"`
- ✅ Reads `MODEL_NAME` with default `"Qwen/Qwen2.5-72B-Instruct"`
- ✅ Raises `ValueError` if API_KEY/HF_TOKEN is empty

**OpenAI client**:
- ✅ Uses `from openai import OpenAI`
- ✅ Creates client: `OpenAI(base_url=API_BASE_URL, api_key=API_KEY)`
- ✅ No raw `urllib` calls for LLM
- ✅ No alternate SDKs (not requests, httpx, etc.)

**Output format**:
- ✅ Prints `[START]` at beginning
- ✅ Prints `[START]\nTask: <task>`
- ✅ Prints `[STEP]` after each action
- ✅ Prints `[STEP]\nAction: <action>\nReward: <value>`
- ✅ Rewards formatted to 2 decimals: `{reward:.2f}`
- ✅ Booleans as lowercase: `true` / `false` (not `True` / `False`)
- ✅ Prints `[END]` after `env.close()` or on exception
- ✅ Prints `[END]\nFinal Score: <score>`
- ✅ Step count matches actual steps executed

**Example valid output**:
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

### Phase 5: requirements.txt ✅

```bash
pip install -r requirements.txt
```

**Check**:
- ✅ No syntax errors
- ✅ Contains: `openai>=1.30.0` (for OpenAI client)
- ✅ Contains: `fastapi>=0.111.0` (for server)
- ✅ Contains: `pydantic>=2.7.0` (for models)
- ✅ Contains: `uvicorn[standard]>=0.29.0` (for serving)
- ✅ Contains: `gradio>=4.0.0` (for demo)
- ✅ No unnecessary packages (keep lean)

### Phase 6: README.md ✅

**Required sections**:
- ✅ Title: "AuditRepairEnv++"
- ✅ Problem description (what problem does it solve?)
- ✅ Solution overview (how does it work?)
- ✅ Task explanation (easy/medium/hard)
- ✅ Setup instructions (local, Docker)
- ✅ How to run `inference.py`
- ✅ Baseline results / example output
- ✅ HF Spaces deployment steps
- ✅ Troubleshooting section
- ✅ License (MIT)

**Writing checklist**:
- ✅ Clear and concise
- ✅ Code examples work
- ✅ Commands are tested
- ✅ No broken links

### Phase 7: demo.py Validation ✅

```bash
export HF_TOKEN="hf_your_token"
python demo.py
```

**Check**:
- ✅ Gradio interface loads
- ✅ Accessible at `http://localhost:7860`
- ✅ Task dropdown selects (easy/medium/hard)
- ✅ "Run Inference" button works
- ✅ Output displays in textbox
- ✅ Dark/minimal aesthetic visible
- ✅ No JavaScript errors in browser console

### Phase 8: Dockerfile ✅

**Valid Dockerfile structure**:
```dockerfile
FROM python:3.10-slim          # ✅ Specified base image
WORKDIR /app                   # ✅ Set working directory
COPY . .                       # ✅ Copy code
RUN pip install -r requirements.txt  # ✅ Install deps
EXPOSE 7860                    # ✅ Expose Gradio port
CMD ["python", "demo.py"]      # ✅ Entry point
```

**Check**:
- ✅ Base image specified (e.g., `python:3.10-slim`)
- ✅ Working directory set
- ✅ Dependencies installed with `pip install`
- ✅ Port exposed (7860)
- ✅ Entry CMD specified
- ✅ No hardcoded tokens/secrets
- ✅ `.dockerignore` excludes unnecessary files

---

## GitHub Repository

### Phase 1: Repository Setup ✅

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/audit-repair-env.git
git push -u origin main
```

**Check**:
- ✅ Repository is **PUBLIC**
- ✅ All code is committed
- ✅ `.gitignore` includes `.env`, `*.key`, `secrets/`
- ✅ No API keys in git history
- ✅ README visible on repo homepage
- ✅ Dockerfile present

### Phase 2: Repository Contents ✅

```
✅ inference.py
✅ server.py
✅ tasks.py
✅ demo.py
✅ requirements.txt
✅ Dockerfile
✅ README.md
✅ HF_SPACES_GUIDE.md
✅ PITCH.md
✅ .gitignore
✅ LICENSE (MIT)
```

**Check**:
- ✅ 10+ commits (show development history)
- ✅ No personal info in commits
- ✅ Meaningful commit messages

---

## Hugging Face Spaces Deployment

### Phase 1: Spaces Creation ✅

1. Go to [huggingface.co/spaces/create](https://huggingface.co/spaces/create)
2. Fill:
   - **Owner**: Your HF username
   - **Space name**: `audit-repair-env`
   - **License**: MIT
   - **SDK**: Docker ← **IMPORTANT**

3. Click **"Create Space"**

**Check**:
- ✅ Space is created
- ✅ Space is PUBLIC
- ✅ URL format: `https://huggingface.co/spaces/your-username/audit-repair-env`

### Phase 2: GitHub Integration ✅

In **Space Settings**:

1. Scroll to **"Linked Repository"**
2. Click **"Link a repository"**
3. Select: `your-username/audit-repair-env`
4. Choose **"Sync"** mode (auto-rebuild on push)

**Check**:
- ✅ GitHub repo linked
- ✅ Sync enabled
- ✅ Branch: `main`

### Phase 3: Environment Secrets ✅

In **Space Settings → Repository secrets**:

```
HF_TOKEN = hf_actual_valid_token_here
API_BASE_URL = https://router.huggingface.co/v1
MODEL_NAME = Qwen/Qwen2.5-72B-Instruct
```

**Check**:
- ✅ HF_TOKEN is valid and has API permissions
- ✅ Secrets are NOT visible in logs
- ✅ Each secret on separate line

### Phase 4: Build & Deploy ✅

1. Go to Space
2. Click **"Logs"** tab
3. Wait 5-10 minutes for build
4. Status changes from **"Building"** → **"Running"**

**Check**:
- ✅ Build succeeds (no errors in logs)
- ✅ Status is **"Running"**
- ✅ No warning signs:
  - ❌ `ImportError`
  - ❌ `ModuleNotFoundError`
  - ❌ `HF_TOKEN not set`
  - ❌ `Connection refused`

### Phase 5: Test Spaces ✅

1. Click **"App"** link in Space
2. You should see Gradio interface
3. Try:
   - Select "easy" task
   - Click "Run Inference"
   - Wait for results

**Check**:
- ✅ Gradio interface loads
- ✅ No 502/504 errors
- ✅ Inference completes (5-30 sec depending on model)
- ✅ Output displays correctly
- ✅ Dark aesthetic visible

### Phase 6: Share Link ✅

Your Space public URL:
```
https://huggingface.co/spaces/your-username/audit-repair-env
```

**Check**:
- ✅ URL is accessible
- ✅ Anyone can view (no login required)
- ✅ App runs without errors

---

## Submission Content

### README Content Checklist

✅ **Title & Description**
```markdown
# AuditRepairEnv++
Budget-constrained RL for financial ledger repair
```

✅ **Problem Statement**
- Why does this matter?
- What real-world problem does it solve?

✅ **Solution Overview**
- What is AuditRepairEnv++?
- How does it work?

✅ **Technical Details**
- Observation space (JSON format)
- Action space (FIX_ENTRY, ADJUST_ENTRY, etc.)
- Reward function (how scoring works)

✅ **Tasks**
- Easy (5-8 entries)
- Medium (15-20 entries)
- Hard (30+ entries, hidden dependencies)

✅ **Setup Instructions**
```bash
pip install -r requirements.txt
export HF_TOKEN="hf_..."
python inference.py
```

✅ **Results / Baseline**
| Task | Score |
|------|-------|
| easy | 0.90 |
| medium | 0.70 |
| hard | 0.55 |

✅ **Deployment**
- Local: `python inference.py`
- Docker: `docker build . && docker run ...`
- HF Spaces: [link to Space]

✅ **License**
MIT License

### Pitch Content Checklist

✅ **30-second pitch** (problem + solution + impact)

✅ **2-minute pitch** (structured narrative)

✅ **Technical pitch** (for engineers/judges)

✅ **Key metrics** (success rate, efficiency, etc.)

✅ **Real-world application** (why it matters)

✅ **Comparison** (vs. other benchmarks/solutions)

✅ **Demo script** (how to show it off)

---

## Final Quality Checks

### Code Quality
- ✅ No syntax errors
- ✅ Follows PEP 8 (somewhat)
- ✅ Comments explain non-obvious logic
- ✅ Error handling (try/except for network calls)
- ✅ No hardcoded secrets/tokens
- ✅ All imports are used

### Documentation Quality
- ✅ Clear and concise
- ✅ Code examples are tested
- ✅ Instructions are step-by-step
- ✅ Troubleshooting section included
- ✅ No typos or grammar errors
- ✅ Links are not broken

### User Experience
- ✅ Gradio interface is intuitive
- ✅ Dark theme is applied
- ✅ Output is readable
- ✅ Error messages are helpful
- ✅ Demo runs quickly (<30 sec)

### Submission Completeness
- ✅ All required files present
- ✅ GitHub repo is public
- ✅ HF Spaces is running
- ✅ README is comprehensive
- ✅ Pitch is compelling
- ✅ No sensitive data exposed

---

## Submission Checklist (Final)

Before you submit to the hackathon:

### Day Before Deadline

- [ ] **Code**: All local tests pass
- [ ] **GitHub**: All code pushed and repo is public
- [ ] **HF Spaces**: Build is complete and Space is running
- [ ] **README**: Updated with all required sections
- [ ] **PITCH**: Prepared and tested
- [ ] **Demo**: Works end-to-end without errors

### Day Of Deadline

- [ ] **Verify Links**
  - [ ] GitHub URL works: https://github.com/your-username/audit-repair-env
  - [ ] HF Spaces URL works: https://huggingface.co/spaces/your-username/audit-repair-env
  - [ ] Both are public/accessible

- [ ] **Test One More Time**
  - [ ] Inference script runs: `python inference.py`
  - [ ] Docker builds: `docker build .`
  - [ ] Demo loads in browser
  - [ ] Output format is correct

- [ ] **Prepare Presentation**
  - [ ] Pitch slides ready
  - [ ] Demo script prepared (which tasks to show)
  - [ ] Metrics/results visible
  - [ ] Story arc is clear

- [ ] **Submit**
  - [ ] GitHub URL submitted
  - [ ] HF Spaces URL submitted
  - [ ] README linked
  - [ ] Team members credited
  - [ ] All deadlines met

---

## Red Flags (🚩 Don't Do These)

❌ **File Structure**
- `src/inference.py` — Must be at root!
- `app/inference.py` — Must be at root!
- Multiple `inference.py` files — Keep only one at root

❌ **Missing Validation**
- HF_TOKEN not validated
- Missing default values
- Using `openai` but not installed in requirements.txt

❌ **Output Format**
- Missing `[START]`, `[STEP]`, or `[END]`
- Rewards not to 2 decimals
- Booleans as `True`/`False` instead of `true`/`false`
- Step count doesn't match

❌ **Deployment**
- HF Spaces build fails (broken logs tab)
- Space is private
- HF_TOKEN is hardcoded in Dockerfile
- Port is not 7860

❌ **Documentation**
- No README
- Pitch is unclear
- No setup instructions
- Broken links

---

## Success Criteria

✅ **Technical**
- [ ] `inference.py` at root validates and runs
- [ ] Output format is exactly correct
- [ ] HF_TOKEN validation works
- [ ] Docker builds successfully

✅ **Documentation**
- [ ] README explains problem & solution
- [ ] Setup instructions are clear
- [ ] Pitch is compelling

✅ **Deployment**
- [ ] GitHub repo is public
- [ ] HF Spaces is running and accessible
- [ ] Demo works end-to-end

✅ **Quality**
- [ ] Code has no obvious bugs
- [ ] Output is readable
- [ ] Instructions work (tested by someone else ideally)

---

## Resources

- [README.md](./README.md) — Environment documentation
- [PITCH.md](./PITCH.md) — How to pitch the project
- [HF_SPACES_GUIDE.md](./HF_SPACES_GUIDE.md) — Detailed deployment guide
- [inference.py](./inference.py) — Submission script
- [GitHub](https://github.com) — Where to host code
- [Hugging Face Spaces](https://huggingface.co/spaces) — Where to deploy

---

## Contact / Support

- **Questions**: Check HF_SPACES_GUIDE.md for troubleshooting
- **Issues**: File bug reports on GitHub
- **Feedback**: Help improve the environment!

---

**Last updated**: April 2025  
**Status**: Ready for submission ✅

---

**📋 Print this checklist and check off as you go!**
