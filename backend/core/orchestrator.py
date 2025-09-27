# Orchestrator wiring A -> B -> C
from typing import Dict, Any
import logging
from backend.agents import agent_a_reader as A
from backend.agents.agent_b_remediator import (
    LangGraphRemediator,
    create_remediator_from_env,
)

# from backend.agents import agent_c_codegen as C  # Commented out as not needed currently

# Configure logging
logger = logging.getLogger(__name__)

# Initialize the enhanced Agent B remediator
try:
    remediator = create_remediator_from_env()
    logger.info("Enhanced Agent B remediator initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Agent B remediator: {e}")
    remediator = None


def analyze_log(text: str) -> Dict[str, Any]:
    """
    Main orchestration function that processes log text through the A -> B pipeline

    Args:
        text: Raw log text to analyze

    Returns:
        Dict containing signal, recommendations, and analysis context
    """
    try:
        # Step 1: Agent A - Analyze and classify the log
        logger.info("Starting Agent A analysis")
        signal = A.run(text)
        logger.info(
            f"Agent A completed: {signal.get('category', 'Unknown')} issue detected"
        )

        # Step 2: Agent B - Generate remediation recommendations
        logger.info("Starting Agent B remediation")
        if remediator:
            # Use enhanced LangGraph remediator (it handles fallbacks internally)
            remediation_result = remediator.get_recommendations(signal)
            recommendations = remediation_result.get("recommendations", [])
            analysis_context = remediation_result.get("analysis_context", {})
            processing_info = remediation_result.get("processing_info", {})

            logger.info(
                f"Agent B completed: {len(recommendations)} recommendations generated"
            )
            logger.info(f"Processing stage: {processing_info.get('stage', 'unknown')}")
        else:
            # If remediator failed to initialize, return minimal error response
            logger.error("Agent B remediator not available")
            recommendations = []
            analysis_context = {"error": "Remediator initialization failed"}
            processing_info = {"stage": "initialization_error", "success": False}

        # Step 3: Agent C - Generate implementation code (COMMENTED OUT)
        # logger.info("Starting Agent C code generation")
        # top_recommendation = recommendations[0] if recommendations else {"action": "CONFIG_FIX", "title": "No-op"}
        #
        # # Extract action from recommendation (handle both string and enum types)
        # action = top_recommendation.get("action", "CONFIG_FIX")
        # if hasattr(action, 'value'):
        #     action = action.value
        #
        # code = C.generate(signal, chosen_action=action)
        # logger.info("Agent C completed: Implementation code generated")

        return {
            "signal": signal,
            "recommendations": recommendations,
            "analysis_context": analysis_context,
            "processing_info": processing_info,
            # "code": code  # Commented out as Agent C is not needed currently
        }

    except Exception as e:
        logger.error(f"Error in orchestration pipeline: {e}")
        # Return error response - let the UI handle the error appropriately
        return {
            "signal": {"category": "ERROR", "severity": "HIGH", "error": str(e)},
            "recommendations": [],
            "analysis_context": {"error": str(e)},
            "processing_info": {"stage": "orchestration_error", "success": False},
            # "code": "# Error occurred during analysis"  # Commented out
        }


def get_remediation_status() -> Dict[str, Any]:
    """Get the status of the remediation system"""
    return {
        "remediator_available": remediator is not None,
        "remediator_type": "LangGraphRemediator" if remediator else "None",
        "model": getattr(remediator, "model", "N/A") if remediator else "N/A",
    }
