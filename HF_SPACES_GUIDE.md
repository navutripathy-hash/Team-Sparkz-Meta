# Hugging Face Spaces Deployment Guide

## What is Hugging Face Spaces?

**Hugging Face Spaces** is a free hosting platform for machine learning demos and applications. It allows you to:

- ✅ Deploy web apps for free (with resource limits)
- ✅ Set environment variables and secrets securely
- ✅ Use Docker for full customization
- ✅ Get a public URL accessible worldwide
- ✅ Integrate with GitHub for continuous deployment

### Key Features
- **Free tier**: 2 vCPU, 8GB RAM per Space
- **Public/Private**: Choose visibility level
- **Auto-builds**: Redeploy on GitHub push (with GitHub integration)
- **Secrets management**: Store API tokens securely
- **Multiple SDK support**: Gradio, Streamlit, Docker, Python

---

## How Does Hugging Face Spaces Work?

### 1. **Creation Phase**
You create a new Space and choose an SDK (Gradio, Streamlit, Docker, etc.)

```
┌─────────────────────────────────────────┐
│  Hugging Face Spaces Dashboard          │
│  ├─ Create New Space                    │
│  ├─ Choose SDK: Docker ← [We use this] │
│  ├─ Set Name: audit-repair-env          │
│  ├─ Set License: MIT                    │
│  └─ Create                              │
└─────────────────────────────────────────┘
```

### 2. **Build Phase**
HF Spaces pulls your code (from GitHub) and builds a Docker image

```
GitHub Repo              Hugging Face Spaces
    │                           │
    ├─ Dockerfile     ────→    Build Server
    ├─ requirements.txt        │
    ├─ inference.py      Builds Docker Image
    ├─ server.py         Creates Container
    └─ demo.py           Allocates Resources
                         │
                      Pushes to Registry
```

### 3. **Runtime Phase**
The container runs on HF's infrastructure with:
- Assigned vCPU/RAM
- Public HTTP endpoint
- Environment variables & secrets

```
Public URL
    │
    ├─ https://huggingface.co/spaces/username/audit-repair-env
    │
    ├─ Routes to Container
    │     ├─ :7860 (Gradio Demo)
    │     └─ :8000 (FastAPI Server - optional)
    │
    └─ Processes Requests
        ├─ Receives HTTP request
        ├─ Runs inference.py / demo.py
        └─ Returns response
```

### 4. **Lifecycle**
- **Sleeping**: Space goes to sleep after 48 hours of inactivity
- **Paused**: You can manually pause spaces
- **Running**: Active and processing requests
- **Error**: Logs visible in Space page

---

## Step-by-Step Deployment

### Step 1: Prepare Your GitHub Repository

**Requirement**: Public GitHub repo with your code

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/audit-repair-env.git
git branch -M main
git push -u origin main
```

**File checklist**:
- ✅ `inference.py` (root directory)
- ✅ `server.py`
- ✅ `tasks.py`
- ✅ `requirements.txt`
- ✅ `demo.py`
- ✅ `Dockerfile`
- ✅ `README.md`

### Step 2: Create Hugging Face Spaces

1. Go to [huggingface.co/spaces](https://huggingface.co/spaces)
2. Click **"Create new Space"**
3. Fill in:
   - **Owner**: Your HF username
   - **Space name**: `audit-repair-env` (or your choice)
   - **License**: MIT
   - **SDK**: Docker ← **IMPORTANT**
4. Click **"Create Space"**

### Step 3: Connect to GitHub (Auto-Deployment)

In your **Space Settings**:

1. Go to **Space** → **Settings** (gear icon)
2. Scroll to **"Linked Repository"**
3. Click **"Link a repository"**
4. Select your GitHub repo: `username/audit-repair-env`
5. Choose **"Simple"** or **"Sync"** mode
   - **Simple**: Manual redeploy via button
   - **Sync**: Auto-redeploy on GitHub push (recommended)

### Step 4: Set Environment Variables & Secrets

In **Space Settings**:

1. Scroll to **"Repository secrets"**
2. Click **"Add secret"**
3. Add:
   ```
   Name: HF_TOKEN
   Value: hf_your_actual_token_here
   ```

4. Add:
   ```
   Name: API_BASE_URL
   Value: https://router.huggingface.co/v1
   ```

5. Add:
   ```
   Name: MODEL_NAME
   Value: Qwen/Qwen2.5-72B-Instruct
   ```

**⚠️ NOTE**: These secrets are only passed to Docker at build-time. If they need to be runtime-only, use the `.dockerfile` method.

### Step 5: Check Logs & Verify Deployment

1. Go to your Space URL: `https://huggingface.co/spaces/username/audit-repair-env`
2. Click **"Logs"** tab to see build output
3. Wait for status: **"Running"**
4. Click the **"App"** link to access your demo

---

## Dockerfile Setup for Spaces

Your `Dockerfile` should be:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Copy everything
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port for Gradio (or FastAPI)
EXPOSE 7860

# Run Gradio demo by default
CMD ["python", "demo.py"]
```

**Alternative** (run both server + demo):
```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 7860 8000

# Create startup script
RUN echo '#!/bin/bash\npython server.py &\npython demo.py' > /app/start.sh
RUN chmod +x /app/start.sh

CMD ["/app/start.sh"]
```

---

## Troubleshooting Common Issues

### Issue: "Build Failed"
```
❌ Docker build failed
```

**Fixes**:
1. Check Logs tab for error messages
2. Verify `requirements.txt` syntax
3. Ensure `Dockerfile` references correct files
4. Check for permission issues

### Issue: "Application Error" on Load
```
❌ Application Error: Connection refused
```

**Fixes**:
1. Verify app runs on `0.0.0.0:7860`
2. Check environment variables are set
3. Look at Space Logs for exceptions
4. Ensure HF_TOKEN is valid

### Issue: "HF_TOKEN not valid"
```
❌ Error initializing client: Invalid token
```

**Fixes**:
1. Generate new token at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
2. Make sure it has API access
3. Update secret in Space Settings
4. Rebuild Space

### Issue: "Model not found"
```
❌ Error: MODEL_NAME 'Qwen/Qwen2.5-72B-Instruct' not found
```

**Fixes**:
1. Verify model exists on Hugging Face Hub
2. Check if you have access (private models need approval)
3. Use inference API endpoint instead:
   ```
   API_BASE_URL=https://api-inference.huggingface.co/v1
   ```
4. Ensure HF_TOKEN is set

### Issue: "Out of Memory"
```
❌ Killed due to resource limit
```

**Fixes**:
- Free tier is 2 vCPU / 8GB RAM
- Reduce model size
- Use a smaller LLM (e.g., `mistral-7b`)
- Consider upgrading to upgrade (usually not needed)
- Optimize inference batch size

### Issue: Space Falls Asleep
```
⚠️ This space has been sleeping for 48 hours
```

**Explanation**: HF Spaces sleep after inactivity to save resources

**Solutions**:
1. Upgrade to paid tier (stays warm)
2. Add uptime monitoring (pings Space regularly)
3. Use HF Pro subscription

---

## Performance Optimization

### For Spaces with Free Tier (2 vCPU, 8GB RAM)

**1. Use Quantized Models**
```python
# Instead of full precision 72B
MODEL_NAME = "Qwen/Qwen2.5-32B-Instruct-GGUF"  # Smaller, quantized
```

**2. Cache Client**
```python
@cache
def get_openai_client():
    return OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)
```

**3. Limit Request Size**
```python
MAX_TOKENS = 150  # Reduce from 300
TEMPERATURE = 0.1  # Lower temp = faster convergence
```

**4. Async Requests** (if multiple concurrent users)
```python
import asyncio
# Use async/await for non-blocking I/O
```

---

## Real-World Example: Workflow

```
1. Developer makes changes locally
   ├─ git commit -am "Fix HF_TOKEN validation"
   └─ git push origin main

2. GitHub notifies HF Spaces
   ├─ HF detects push to linked repo
   └─ Triggers automatic build

3. HF Spaces builds Docker image
   ├─ Pulls latest code from main branch
   ├─ Runs: pip install -r requirements.txt
   ├─ Loads secrets (HF_TOKEN, API_BASE_URL, etc.)
   └─ Runs: python demo.py

4. Container starts running
   ├─ Gradio interface initializes on :7860
   ├─ FastAPI server (optional) on :8000
   └─ Public URL becomes active

5. User accesses Space URL
   ├─ Browser loads Gradio interface
   ├─ User selects task (easy/medium/hard)
   ├─ Clicks "Run Inference"
   └─ inference.py executes with LLM calls

6. LLM calls routed via:
   API_BASE_URL (huggingface.co/v1)
       ↓
   HF Token used for authentication
       ↓
   Model (Qwen/Qwen2.5-72B-Instruct) queried
       ↓
   Response returned to inference.py
       ↓
   Results shown in Gradio UI
```

---

## Security Best Practices

### ✅ DO

- Set HF_TOKEN as a **secret** in Space settings
- Use `.gitignore` to prevent token from being committed:
  ```
  .env
  .env.local
  *.key
  secrets/
  ```
- Validate all user inputs
- Use HTTPS (handled by HF automatically)

### ❌ DON'T

- Commit API keys to GitHub
- Expose secrets in logs
- Store sensitive data in code
- Leave Space public if handling private data

---

## Next Steps

1. **Verify locally first**:
   ```bash
   export HF_TOKEN="your_token"
   export API_BASE_URL="https://router.huggingface.co/v1"
   python inference.py  # Run submission tests
   python demo.py       # Test Gradio UI
   ```

2. **Push to GitHub**:
   ```bash
   git add -A
   git commit -m "Ready for HF Spaces deployment"
   git push origin main
   ```

3. **Create & Link Space**:
   - Create Space on HF
   - Link GitHub repo
   - Set secrets in Settings
   - Wait for build

4. **Test on Spaces**:
   - Access public URL
   - Run test inference
   - Share link with community

---

## Additional Resources

- [Hugging Face Spaces Docs](https://huggingface.co/docs/hub/spaces)
- [Docker Spaces Guide](https://huggingface.co/docs/hub/spaces-config-reference#docker)
- [Gradio Documentation](https://www.gradio.app/)
- [OpenAI Python Client](https://github.com/openai/openai-python)
- [HF Inference API Docs](https://huggingface.co/docs/api-inference)

---

**Good luck with your submission! 🚀**
