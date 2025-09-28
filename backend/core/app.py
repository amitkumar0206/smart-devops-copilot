from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from typing import Any, Dict
from .orchestrator import analyze_log, get_remediation_status
import threading
from backend.slack_integration.sdk_based.slack_file_listener import SlackFileListener

app = FastAPI(title="Smart DevOps Copilot")


class AnalyzeRequest(BaseModel):
    text: str

@app.get("/status")
async def get_status() -> Dict[str, Any]:
    """Get system status including remediator availability and configuration"""
    remediation_status = get_remediation_status()
    return {
        "status": "healthy",
        "service": "Smart DevOps Copilot",
        "version": "1.0.0",
        "remediator_available": remediation_status["remediator_available"],
        "remediator_type": remediation_status["remediator_type"],
        "model": remediation_status["model"],
    }


@app.post("/analyze")
async def analyze(req: AnalyzeRequest):
    return analyze_log(req.text)


@app.post("/analyze_file")
async def analyze_file(file: UploadFile = File(...)):
    content = (await file.read()).decode("utf-8", errors="ignore")
    return analyze_log(content)

@app.post("/initialize-listener")
async def initialize_listener():
    """Initialize the Slack file listener"""
    try:
        # Start listener in background thread
        def run_listener():
            try:
                listener = SlackFileListener()
                listener.start_listening()
            except Exception as e:
                print(f"Error in listener thread: {e}")

        thread = threading.Thread(target=run_listener, daemon=True)
        thread.start()

        return {
            "success": True,
            "message": "Listener initialized successfully",
            "status": "running"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "status": "failed"
        }
