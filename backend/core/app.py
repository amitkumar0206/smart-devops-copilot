from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from backend.core.orchestrator import analyze_log

app = FastAPI(title="Smart DevOps Copilot")

class AnalyzeRequest(BaseModel):
    text: str

@app.post("/analyze")
async def analyze(req: AnalyzeRequest):
    return analyze_log(req.text)

@app.post("/analyze_file")
async def analyze_file(file: UploadFile = File(...)):
    content = (await file.read()).decode("utf-8", errors="ignore")
    return analyze_log(content)
