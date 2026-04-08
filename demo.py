"""
demo.py -- AuditRepairEnv++ Gradio Demo
========================================
Minimal black aesthetic interface for Hugging Face Spaces
Run: python demo.py
"""

import asyncio
import os
import json
from typing import Optional
import gradio as gr
from inference import OpenAI, run_task, build_prompt, get_model_message

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
HF_TOKEN = os.getenv("HF_TOKEN")

# Track session state
session_state = {
    "client": None,
    "task_running": False,
    "logs": []
}

def initialize_client():
    """Initialize OpenAI client."""
    if not HF_TOKEN:
        return None, "❌ Error: HF_TOKEN not set. Set environment variable HF_TOKEN"
    
    try:
        session_state["client"] = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)
        return session_state["client"], "✅ Client initialized successfully"
    except Exception as e:
        return None, f"❌ Error initializing client: {str(e)}"

def run_inference(task_type: str, model_text: str = "") -> str:
    """
    Run inference on selected task.
    
    Args:
        task_type: "easy", "medium", or "hard"
        model_text: Custom model name (optional)
    
    Returns:
        Formatted output logs
    """
    if not HF_TOKEN:
        return "❌ Error: HF_TOKEN environment variable not set.\n\nSet it before running:"
    
    if not session_state["client"]:
        client, msg = initialize_client()
        if not client:
            return msg
    
    if session_state["task_running"]:
        return "⏳ Task already running..."
    
    session_state["task_running"] = True
    session_state["logs"] = []
    
    try:
        client = session_state["client"]
        
        # Run the task
        output_log = f"""
╔════════════════════════════════════════╗
║     AuditRepairEnv++ Inference         ║
╚════════════════════════════════════════╝

📋 Task: {task_type.upper()}
🤖 Model: {model_text or MODEL_NAME}
🔗 API: {API_BASE_URL}

"""
        
        # Capture stdout for the actual inference
        import io
        import sys
        
        old_stdout = sys.stdout
        sys.stdout = buffer = io.StringIO()
        
        try:
            score = run_task(client, task_type)
            inference_output = buffer.getvalue()
        finally:
            sys.stdout = old_stdout
        
        output_log += inference_output
        output_log += f"""
════════════════════════════════════════
✨ Task completed with score: {score:.2f}
════════════════════════════════════════
"""
        
        return output_log
        
    except Exception as e:
        error_msg = f"""
╔════════════════════════════════════════╗
║              ERROR                     ║
╚════════════════════════════════════════╝

❌ {str(e)}

Troubleshooting:
- Verify HF_TOKEN is set correctly
- Check API_BASE_URL connectivity
- Ensure MODEL_NAME is valid
"""
        return error_msg
    
    finally:
        session_state["task_running"] = False

def get_info() -> str:
    """Return project information."""
    return """
╔════════════════════════════════════════╗
║    🔧 AuditRepairEnv++ • OpenEnv      ║
╚════════════════════════════════════════╝

**What is this?**
An RL environment where AI agents repair 
financial ledgers with interdependent errors.

**Key Challenge:**
Fixing one entry can cascade changes to 
dependent entries, creating new errors.

**Goals:**
✓ Maximize ledger consistency
✓ Minimize repair actions (budget-limited)
✓ Avoid overcorrection penalties

**Task Difficulty:**
• **easy**: 5-8 entries, simple dependencies
• **medium**: 15-20 entries, moderate complexity  
• **hard**: 30+ entries, complex dependency graph

**Action Space:**
- FIX_ENTRY <id>: Set value = expected_value
- ADJUST_ENTRY <id> <delta>: Increment/decrement
- REVERT_ENTRY <id>: Undo last change
- NO_OP: Do nothing (skip step)

**Rewards:**
- Composite scoring based on:
  • Errors fixed
  • Budget efficiency  
  • Overcorrection penalties

---
**Repository:** [GitHub](https://github.com/your-repo)
**Paper:** [ArXiv](https://arxiv.org)
"""

# ════════════════════════════════════════
# GRADIO INTERFACE (Minimal Black Aesthetic)
# ════════════════════════════════════════

CSS = """
body {
    background: linear-gradient(135deg, #0f0f0f 0%, #1a1a1a 100%);
    color: #ffffff;
    font-family: 'Courier New', monospace;
}

.container {
    background: #1a1a1a;
    border: 1px solid #333333;
}

.panel {
    background: #0f0f0f;
    border-left: 3px solid #00ff00;
    padding: 20px;
    border-radius: 0px;
}

.button-primary {
    background: #00ff00 !important;
    color: #000000 !important;
    border: none !important;
    font-weight: bold;
    border-radius: 2px !important;
}

.button-primary:hover {
    background: #00cc00 !important;
}

textarea, input {
    background: #1a1a1a !important;
    color: #00ff00 !important;
    border: 1px solid #333333 !important;
    font-family: 'Courier New', monospace !important;
}

h1, h2, h3 {
    color: #00ff00;
    text-shadow: 0 0 10px rgba(0, 255, 0, 0.3);
}

.info-box {
    background: linear-gradient(90deg, rgba(0,255,0,0.05) 0%, rgba(0,255,0,0.01) 100%);
    border: 1px solid #00ff00;
    color: #00ff00;
    padding: 15px;
    border-radius: 2px;
}
"""

with gr.Blocks(title="AuditRepairEnv++", css=CSS, theme=gr.themes.Base()) as demo:
    gr.HTML("<h1 style='text-align: center; color: #00ff00;'>⚙️ AuditRepairEnv++ • OpenEnv</h1>")
    gr.HTML("<p style='text-align: center; color: #888888;'>Cost-Constrained Ledger Repair via RL</p>")
    
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 📋 Configuration")
            
            task_dropdown = gr.Radio(
                choices=["easy", "medium", "hard"],
                value="easy",
                label="Task Difficulty",
                interactive=True
            )
            
            model_input = gr.Textbox(
                label="Model (optional, uses default)",
                placeholder=MODEL_NAME,
                interactive=True,
                lines=1
            )
            
            run_button = gr.Button("▶️ Run Inference", scale=2, variant="primary")
            
            gr.Markdown("### 📖 About")
            info_btn = gr.Button("ℹ️ Show Info", scale=2)
        
        with gr.Column(scale=2):
            gr.Markdown("### 📺 Output Logs")
            output_textbox = gr.Textbox(
                label="Inference Output",
                placeholder="Output will appear here...",
                interactive=False,
                lines=20,
                max_lines=30
            )
    
    with gr.Row():
        info_output = gr.Markdown("", visible=False)
    
    # Event handlers
    def on_run_click(task, model_name):
        model_name = model_name or MODEL_NAME
        result = run_inference(task, model_name)
        return result
    
    def on_info_click():
        return gr.Markdown(get_info(), visible=True)
    
    run_button.click(
        fn=on_run_click,
        inputs=[task_dropdown, model_input],
        outputs=output_textbox
    )
    
    info_btn.click(
        fn=on_info_click,
        inputs=[],
        outputs=info_output
    )
    
    gr.Markdown(
        """
        ---
        **How to use:**
        1. Select task difficulty (easy/medium/hard)
        2. Optionally change model name
        3. Click "Run Inference" to start
        
        **Requirements:**
        - Set `HF_TOKEN` environment variable
        - Server running on `localhost:7860`
        
        **Deploy to Hugging Face Spaces:**
        - Push to GitHub repo with Dockerfile
        - Link Spaces to GitHub
        - Set `HF_TOKEN` secret in Spaces settings
        """
    )

if __name__ == "__main__":
    # Initialize client on startup
    initialize_client()
    
    # Launch Gradio app
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )
