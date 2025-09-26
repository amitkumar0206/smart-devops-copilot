# Smart DevOps Copilot (Hackathon Skeleton)

Multi-agent Python system to: **read logs → recommend fixes → generate Terraform/CLI**.

## Quick Start (Dev)
### 1) Create & activate a venv (optional)
```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

### 2) Install deps
```bash
pip install -r requirements.txt
```

### 3) Start the backend (FastAPI)
```bash
uvicorn backend.core.app:app --reload --port 8000
```

### 4) Start the UI (Streamlit)
```bash
streamlit run ui/app.py
```

Open the Streamlit URL it prints (usually http://localhost:8501).

## What’s inside
- **Agent A**: Log reader & classifier → extracts fields and categorizes (IAM / Throttling / Timeout / Quota / Config / Scaling).
- **Agent B**: Maps category → remediation options with rationale.
- **Agent C**: Emits **Terraform** or **AWS CLI** snippets for the chosen option.
- **Orchestrator**: Simple graph A → B → C with feedback hooks.

This skeleton uses **rule-based** logic so it works offline for the demo. You can later swap to your favorite LLM framework (LangGraph, CrewAI, AutoGen) to do true multi-agent reasoning.

## Demo flow
1. In the UI, upload a sample log from `fixtures/` (or paste).
2. Press **Analyze**.
3. See: Issue classification → ranked recommendations → Terraform/CLI.
4. Copy the snippet and validate/apply in your own environment (not part of this demo).

## Project Layout
```
backend/
  agents/
    agent_a_reader.py
    agent_b_remediator.py
    agent_c_codegen.py
  core/
    orchestrator.py
    app.py
fixtures/
  <8 sample log files>
ui/
  app.py             # Streamlit
docs/
  DESIGN.md
tests/
  test_fixtures.py
requirements.txt
```

## Notes
- **Safety**: Codegen avoids destructive actions. Review all outputs.
- **Auth**: None for hackathon.
- **Extensibility**: Add providers for Slack/Jira/Datadog in v2+. 

## License
MIT (for hackathon use).
