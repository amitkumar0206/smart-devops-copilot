"""
LangGraph Orchestrator: A -> B -> D
-----------------------------------
- Agent A (Reader): classifies/categorizes the incoming log.
- Agent B (Remediator): proposes remediations + recommendations.
- Agent D (Runbook Synthesizer): turns the remediation into a concise runbook.

This module is defensive: if your local agent imports are unavailable,
it falls back to simple stub implementations so the graph still compiles.
Replace the stubbed parts with your real agent logic when running in your repo.
"""

from __future__ import annotations

from typing import Any, Dict, List, TypedDict, Optional
import logging
import os

from backend.agents import agent_a_reader
from backend.agents.agent_b_remediator import Recommendation

# -----------------------------
# Imports (defensive fallbacks)
# -----------------------------
A = None
D = None
create_remediator_from_env = None

try:
    # Prefer relative imports (when this file is inside a package).
    from ..agents import agent_a_reader as A  # type: ignore
    from ..agents.agent_b_remediator import create_remediator_from_env  # type: ignore
    from ..agents import agent_d_runbooksynthesizer as D  # type: ignore
except Exception:
    # Try absolute imports (if used as a top-level module)
    try:
        from agents import agent_a_reader as A  # type: ignore
        from agents.agent_b_remediator import create_remediator_from_env  # type: ignore
        from agents import agent_d_runbooksynthesizer as D  # type: ignore
    except Exception:
        # Fall back to stubs so the graph compiles even without real agents.
        A = None
        D = None
        create_remediator_from_env = None

# LangGraph / validation
try:
    from langgraph.graph import StateGraph
except Exception as e:  # pragma: no cover
    raise RuntimeError(
        "langgraph is required. Install with `pip install langgraph`."
    ) from e


# ---------------
# Logging config
# ---------------
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(levelname)s] %(name)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)


# -------------------
# State / Type model
# -------------------
class OrchestratorState(TypedDict, total=False):
    log: str
    category: str
    remediation: str
    recommendations: List[str]
    runbook: Optional[str]

    # meta/debug
    analysis_context: Dict[str, Any]
    processing_info: Dict[str, Any]


# ------------------
# Agent wrappers
# ------------------
def _agent_a_categorize(log: str) -> str:
    return A.categorize_log(log)


class Remediator:
    def __init__(self, model: str):
        self.model = model
        
    def remediate(self, log: str, category: str) -> Optional[Dict[str, Any]]:
        if create_remediator_from_env:
            remediator = create_remediator_from_env()
            dummy_signal = {"text": log}
            enhanced_signal = remediator._enhance_signal_from_raw_text(dummy_signal)
            recommendation = remediator.get_recommendations(enhanced_signal)
            return recommendation
        return _stub_remediate(log, category)

# Singleton remediator instance
_remediator_singleton = Remediator(
    model=os.environ.get("LLM_MODEL", "stub")
)

def _agent_d_runbook(remediation: str, recommendations: List[str]) -> str:
    if D and hasattr(D, "synthesize_runbook"):
        return D.synthesize_runbook(runbook_text=remediation)  # type: ignore[attr-defined]
    return _stub_runbook(remediation, recommendations)


# ------------------
# LangGraph nodes
# ------------------
def _node_classify(state: OrchestratorState) -> OrchestratorState:
    log = state.get("log", "") or ""
    category = _agent_a_categorize(log)
    return {
        **state,
        "category": category,
        "processing_info": {
            **state.get("processing_info", {}),
            "stage": "classified",
        },
    }


def _node_remediate(state: OrchestratorState) -> OrchestratorState:
    log = state.get("log", "") or ""
    category = state.get("category", "General/Error")
    logger.info("Signal to Agent B: log = %s", log)
    result = _remediator_singleton.remediate(log=log, category=category)
    remediation = result.get("remediation", "")
    recommendations = result.get("recommendations", []) or []
    logger.info("Remediation generated; %d recommendations", len(recommendations))
    return {
        **state,
        "remediation": remediation,
        "recommendations": recommendations,
        "processing_info": {
            **state.get("processing_info", {}),
            "stage": "remediated",
        },
    }


def _node_runbook(state: OrchestratorState) -> OrchestratorState:
    remediation = state.get("remediation", "") or ""
    recommendations = state.get("recommendations", []) or []
    runbook = _agent_d_runbook(remediation, recommendations)
    logger.info("Runbook synthesized (%d chars)", len(runbook or ""))
    return {
        **state,
        "runbook": runbook,
        "processing_info": {
            **state.get("processing_info", {}),
            "stage": "runbook_synthesized",
        },
    }


# ------------------
# Graph builder API
# ------------------
def build_orchestrator() -> "CompiledGraph":
    """
    Returns a compiled LangGraph graph that wires:
    START -> classify -> (conditional) remediate/runbook -> END
    """
    graph = StateGraph(OrchestratorState)  # type: ignore[arg-type]
    graph.add_node("classify", _node_classify)
    graph.add_node("remediate", _node_remediate)
    graph.add_node("runbook", _node_runbook)

    # Conditional edge from classify
    graph.add_conditional_edges("classify", tools_condition)

    graph.set_entry_point("classify")
    graph.set_finish_point("runbook")

    # Remediate always goes to slack
    #graph.add_edge("remediate", "slack")

    return graph.compile()


# ------------------
# Public helpers
# ------------------
def tools_condition(state: OrchestratorState) -> str:
    """
    Determines which node to call next based on Agent A's output.
    """
    # If category is runbook, 
    if state.get("category") == "runbook":
        logger.info("category is runbook, calling remediate next")
        return "remediate"
    # Otherwise, go to remediate
    logger.info(f"category is {state.get('category')}, calling remediate next")
    return "remediate"

def analyze_log(log: str) -> OrchestratorState:
    """
    Convenience function to run the full pipeline on a single log string.
    """
    try:
        compiled = build_orchestrator()
        initial: OrchestratorState = {
            "log": log,
            "analysis_context": {},
            "processing_info": {"stage": "start"},
        }
        # run the compiled graph
        result: OrchestratorState = compiled.invoke(initial)  # type: ignore[assignment]
        return result
    except Exception as e:  # pragma: no cover
        logger.exception("Orchestrator error: %s", e)
        return {
            "log": log,
            "category": "Unknown",
            "remediation": "",
            "recommendations": [],
            "runbook": None,
            "analysis_context": {"error": str(e)},
            "processing_info": {"stage": "orchestration_error", "success": False},
        }


def get_remediation_status() -> Dict[str, Any]:
    """Introspect remediator availability & model."""
    return {
        "remediator_available": _remediator_singleton is not None and _remediator_singleton.model != "stub",
        "remediator_type": type(_remediator_singleton).__name__,
        "model": getattr(_remediator_singleton, "model", "stub"),
    }
