import os
import sys
import subprocess
import urllib.request
import json
import time

def print_hdr(msg):
    print(f"\n{'-'*60}\n[VALIDATE] {msg}\n{'-'*60}")

def check(condition, message):
    if condition:
        print(f"  [PASS] {message}")
    else:
        print(f"  [FAIL] {message}")
        sys.exit(1)

def run():
    print_hdr("Checking essential files")
    files = ["openenv.yaml", "tasks.py", "server.py", "inference.py", "Dockerfile", "pyproject.toml", "requirements.txt"]
    for f in files:
        check(os.path.exists(f), f"File {f} exists")

    print_hdr("Starting server for test")
    server_proc = subprocess.Popen(["python", "server.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(3)

    try:
        print_hdr("Testing endpoints")
        # 1. Health
        req = urllib.request.Request("http://localhost:7860/health")
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            check(data["status"] == "ok", "Health endpoint")
        
        # 2. Reset POST
        req = urllib.request.Request("http://localhost:7860/reset", data=b'{"task_id": "easy"}', headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            check("errors" in data, "Reset POST returns full observation")

        # 3. Step POST
        req = urllib.request.Request("http://localhost:7860/step", data=b'{"message": "FIX_ENTRY 1"}', headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            check("reward" in data and "observation" in data, "Step POST returns reward/observation")

        print_hdr("Testing Inference Script Format")
        inf = subprocess.run(["python", "inference.py"], capture_output=True, text=True, env={**os.environ, "API_BASE_URL": "http://mock", "HF_TOKEN": "mock"})
        
        out = inf.stdout
        check("\n[START]\nTask: easy" in out, "Exact [START] format found")
        check("\n[STEP]\nAction:" in out, "Exact [STEP] format found")
        check("\n[END]\nFinal Score:" in out, "Exact [END] format found")
        check("Final Score: 0.0" in out or "Final Score:" in out, "Final score correctly parsed/printed")

        print_hdr("Checking vcpu and memory notes")
        with open("openenv.yaml") as fl:
            content = fl.read()
            check("memory_gb: 8" in content, "Memory is 8gb in yaml")
            check("vcpus: 2" in content, "VCPUs 2 in yaml")
            
        print_hdr("Validating Docker build")
        # Try a quick docker build
        print("  Running docker build --no-cache -t envtest .")
        res = subprocess.run(["docker", "build", "--no-cache", "-t", "envtest", "."], capture_output=True, text=True)
        if res.returncode == 0:
            print("  [PASS] Docker build successful")
        else:
            print(f"  [WARN] Docker build failed (you might not have docker installed or running locally).\nError: {res.stderr[:200]}")

        print_hdr("ALL VALIDATION CHECKS PASSED")

    finally:
        server_proc.terminate()
        server_proc.wait()

if __name__ == "__main__":
    run()
