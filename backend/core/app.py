from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from backend.core.orchestrator import analyze_log, get_remediation_status

app = FastAPI(title="Smart DevOps Copilot")


class AnalyzeRequest(BaseModel):
    text: str


@app.get("/status")
async def get_status():
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
