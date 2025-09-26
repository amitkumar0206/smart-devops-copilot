# Orchestrator wiring A -> B -> C
from typing import Dict, Any
from backend.agents import agent_a_reader as A
from backend.agents import agent_b_remediator as B
from backend.agents import agent_c_codegen as C

def analyze_log(text: str) -> Dict[str, Any]:
    a = A.run(text)
    recs = B.recommendations(a)
    top = recs[0] if recs else {"action": "CONFIG_FIX", "title": "No-op"}
    code = C.generate(a, chosen_action=top.get("action"))
    return {"signal": a, "recommendations": recs, "code": code}
