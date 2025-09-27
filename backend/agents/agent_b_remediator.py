# Agent B: Enhanced Recommendation Engine with LangChain/LangGraph
import json
import openai
import os
from typing import Dict, Any, List, Optional, TypedDict
from dataclasses import dataclass, asdict
from enum import Enum
from langgraph.graph import StateGraph, END
import re
from datetime import datetime
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Severity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ActionType(Enum):
    IAM_POLICY_UPDATE = "IAM_POLICY_UPDATE"
    RESOURCE_POLICY_UPDATE = "RESOURCE_POLICY_UPDATE"
    CAPACITY_SCALE = "CAPACITY_SCALE"
    RETRY_POLICY = "RETRY_POLICY"
    TIMEOUT_TUNE = "TIMEOUT_TUNE"
    QUOTA_INCREASE = "QUOTA_INCREASE"
    SCALING_POLICY_TUNE = "SCALING_POLICY_TUNE"
    CONFIG_FIX = "CONFIG_FIX"
    CIRCUIT_BREAKER = "CIRCUIT_BREAKER"
    MONITORING_SETUP = "MONITORING_SETUP"


@dataclass
class Recommendation:
    title: str
    rationale: List[str]
    action: ActionType
    risk_level: Severity
    trade_offs: Dict[str, str]
    estimated_time: str
    priority: int  # 1 = highest priority
    aws_services: List[str]  # Services that need modification
    implementation_steps: List[str]


# LangGraph State Definition
class RemediationState(TypedDict):
    signal: Dict[str, Any]  # Input from Agent A
    category: str
    severity: str
    component: str
    context: Dict[str, Any]
    recommendations: List[Dict[str, Any]]
    analysis_complete: bool
    error_message: Optional[str]
    processing_stage: str


class LangGraphRemediator:
    """
    Agent B: LangGraph-powered DevOps Remediator
    Uses LLM to generate intelligent recommendations for CloudWatch issues
    """

    def __init__(
        self,
        api_key: str = None,
        base_url: str = "https://openrouter.ai/api/v1",
        model: str = "openai/gpt-4o",
    ):
        """Initialize with OpenRouter API credentials"""
        # Use environment variable if api_key not provided
        if api_key is None:
            api_key = os.getenv("OPENROUTER_API_KEY")

        if not api_key:
            raise ValueError(
                "API key must be provided either as parameter or OPENROUTER_API_KEY environment variable"
            )

        self.api_key = api_key
        self.base_url = base_url
        self.model = model

        # Validate configuration
        self._validate_config()

        self.client = openai.OpenAI(api_key=api_key, base_url=base_url)
        self.graph = self._build_remediation_graph()

        logger.info(f"LangGraphRemediator initialized with model: {model}")

    def _validate_config(self):
        """Validate the configuration parameters"""
        if not self.api_key or len(self.api_key.strip()) == 0:
            raise ValueError("API key cannot be empty")

        if not self.base_url or not self.base_url.startswith(("http://", "https://")):
            raise ValueError("Base URL must be a valid HTTP/HTTPS URL")

        if not self.model or len(self.model.strip()) == 0:
            raise ValueError("Model name cannot be empty")

        logger.info("Configuration validation passed")

    def _build_remediation_graph(self) -> StateGraph:
        """Build the LangGraph workflow for remediation analysis"""
        workflow = StateGraph(RemediationState)

        # Add nodes for different analysis phases
        workflow.add_node("analyze_signal", self._analyze_signal)
        workflow.add_node("generate_recommendations", self._generate_recommendations)
        workflow.add_node("prioritize_solutions", self._prioritize_solutions)
        workflow.add_node("format_output", self._format_output)

        # Define the remediation flow
        workflow.set_entry_point("analyze_signal")
        workflow.add_edge("analyze_signal", "generate_recommendations")
        workflow.add_edge("generate_recommendations", "prioritize_solutions")
        workflow.add_edge("prioritize_solutions", "format_output")
        workflow.add_edge("format_output", END)

        return workflow.compile()

    def _call_llm(self, prompt: str, system_prompt: str = None) -> str:
        """Make API call to LLM via OpenRouter"""
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,  # Lower temperature for more consistent technical recommendations
                max_tokens=2000,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error calling LLM: {str(e)}"

    def _extract_json_from_response(self, response: str) -> dict:
        """Extract JSON from LLM response, handling various formats"""
        try:
            # First try to parse the entire response as JSON
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to find JSON within the response using regex
            json_pattern = r"\{.*\}"
            matches = re.findall(json_pattern, response, re.DOTALL)

            for match in matches:
                try:
                    return json.loads(match)
                except json.JSONDecodeError:
                    continue

            # If no valid JSON found, return empty dict
            return {}

    def _analyze_signal(self, state: RemediationState) -> RemediationState:
        """Analyze the incoming signal to understand the issue context"""
        signal = state["signal"]

        system_prompt = """You are a senior DevOps engineer analyzing AWS CloudWatch errors and system issues.
        
Your task is to analyze the provided error signal and extract key context for remediation planning.

IMPORTANT: Your response must be valid JSON in this exact format:
{
    "issue_analysis": {
        "root_cause": "Primary cause of the issue",
        "severity_assessment": "LOW/MEDIUM/HIGH/CRITICAL with reasoning",
        "affected_components": ["component1", "component2"],
        "business_impact": "Description of business impact",
        "urgency": "immediate/high/medium/low"
    },
    "technical_context": {
        "aws_services_involved": ["service1", "service2"],
        "error_patterns": ["pattern1", "pattern2"],
        "likely_triggers": ["trigger1", "trigger2"],
        "dependencies": ["dependency1", "dependency2"]
    },
    "remediation_scope": {
        "quick_wins": ["immediate action1", "immediate action2"],
        "medium_term": ["action1", "action2"],
        "preventive_measures": ["prevention1", "prevention2"]
    }
}

Analyze thoroughly but be concise. Focus on actionable insights."""

        prompt = f"""Analyze this CloudWatch/DevOps issue:

SIGNAL DATA:
- Category: {signal.get('category', 'Unknown')}
- Severity: {signal.get('severity', 'Unknown')}
- Component: {signal.get('component', 'Unknown')}
- Error Message: {signal.get('error_message', 'No error message provided')}
- HTTP Code: {signal.get('http_code', 'N/A')}
- Region: {signal.get('region', 'N/A')}
- Resource ID: {signal.get('resource_id', 'N/A')}
- Additional Context: {json.dumps(signal.get('additional_context', {}), indent=2)}

Provide a comprehensive analysis focusing on root cause, impact, and remediation scope."""

        response = self._call_llm(prompt, system_prompt)
        analysis_data = self._extract_json_from_response(response)

        if analysis_data:
            state["context"] = analysis_data
            state["processing_stage"] = "analysis_complete"
        else:
            # Fallback analysis
            state["context"] = {
                "issue_analysis": {
                    "root_cause": f"Issue in {signal.get('category', 'system')} component",
                    "severity_assessment": signal.get("severity", "MEDIUM"),
                    "affected_components": [signal.get("component", "unknown")],
                    "business_impact": "Service disruption detected",
                    "urgency": (
                        "high"
                        if signal.get("severity") in ["HIGH", "CRITICAL"]
                        else "medium"
                    ),
                },
                "technical_context": {
                    "aws_services_involved": [signal.get("component", "unknown")],
                    "error_patterns": ["configuration_issue"],
                    "likely_triggers": ["recent_deployment", "traffic_spike"],
                    "dependencies": [],
                },
                "remediation_scope": {
                    "quick_wins": ["investigate_logs", "check_configuration"],
                    "medium_term": ["capacity_review", "monitoring_enhancement"],
                    "preventive_measures": ["automated_testing", "monitoring_alerts"],
                },
            }
            state["processing_stage"] = "analysis_fallback"

        return state

    def _generate_recommendations(self, state: RemediationState) -> RemediationState:
        """Generate specific remediation recommendations using LLM"""
        signal = state["signal"]
        context = state["context"]

        system_prompt = f"""You are an expert DevOps consultant providing specific, actionable remediation recommendations.

Based on the analysis provided, generate 2-3 prioritized recommendations that are:
1. Specific and actionable
2. Include clear implementation steps
3. Consider trade-offs and risks
4. Provide time estimates
5. Specify required AWS services

IMPORTANT: Your response must be valid JSON in this exact format:
{{
    "recommendations": [
        {{
            "title": "Clear, actionable title",
            "rationale": ["reason1", "reason2", "reason3"],
            "action_type": "IAM_POLICY_UPDATE|CAPACITY_SCALE|CONFIG_FIX|etc",
            "risk_level": "LOW|MEDIUM|HIGH|CRITICAL",
            "trade_offs": {{
                "pros": "Benefits of this approach",
                "cons": "Potential drawbacks or risks"
            }},
            "estimated_time": "15 minutes|2 hours|1 day|etc",
            "priority": 1,
            "aws_services": ["service1", "service2"],
            "implementation_steps": [
                "1. Specific step with actions",
                "2. Next step with details",
                "3. Validation step"
            ]
        }}
    ]
}}

Generate practical solutions that address the root cause while considering business impact."""

        # Build comprehensive prompt with all available context
        issue_summary = context.get("issue_analysis", {})
        technical_context = context.get("technical_context", {})

        prompt = f"""Generate remediation recommendations for this issue:

ISSUE ANALYSIS:
- Root Cause: {issue_summary.get('root_cause', 'Unknown')}
- Severity: {issue_summary.get('severity_assessment', 'Unknown')}
- Business Impact: {issue_summary.get('business_impact', 'Unknown')}
- Urgency: {issue_summary.get('urgency', 'medium')}

TECHNICAL CONTEXT:
- AWS Services: {', '.join(technical_context.get('aws_services_involved', []))}
- Error Patterns: {', '.join(technical_context.get('error_patterns', []))}
- Likely Triggers: {', '.join(technical_context.get('likely_triggers', []))}

ORIGINAL SIGNAL:
- Category: {signal.get('category')}
- Component: {signal.get('component')}
- Error: {signal.get('error_message', 'No specific error message')}

Generate 2-3 specific, actionable recommendations prioritized by impact and feasibility."""

        response = self._call_llm(prompt, system_prompt)
        recommendations_data = self._extract_json_from_response(response)

        if recommendations_data and "recommendations" in recommendations_data:
            state["recommendations"] = recommendations_data["recommendations"]
        else:
            # Generate fallback recommendations based on category
            state["recommendations"] = self._generate_fallback_recommendations(signal)

        state["processing_stage"] = "recommendations_generated"
        return state

    def _generate_fallback_recommendations(
        self, signal: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate fallback recommendations when LLM fails"""
        category = signal.get("category", "CONFIG")

        fallback_recs = {
            "IAM": [
                {
                    "title": "Review and update IAM permissions",
                    "rationale": [
                        "Access denied errors indicate missing permissions",
                        "Verify role policies and resource access",
                    ],
                    "action_type": "IAM_POLICY_UPDATE",
                    "risk_level": "LOW",
                    "trade_offs": {
                        "pros": "Immediate access resolution",
                        "cons": "Requires security review",
                    },
                    "estimated_time": "30 minutes",
                    "priority": 1,
                    "aws_services": ["IAM", "CloudTrail"],
                    "implementation_steps": [
                        "1. Check CloudTrail for denied actions",
                        "2. Update IAM policy",
                        "3. Test access",
                    ],
                }
            ],
            "THROTTLING": [
                {
                    "title": "Implement retry logic and scale capacity",
                    "rationale": [
                        "Throttling indicates capacity limits",
                        "Client retries reduce user impact",
                    ],
                    "action_type": "RETRY_POLICY",
                    "risk_level": "LOW",
                    "trade_offs": {
                        "pros": "Immediate improvement",
                        "cons": "Doesn't address root cause",
                    },
                    "estimated_time": "1 hour",
                    "priority": 1,
                    "aws_services": ["Application", "Auto Scaling"],
                    "implementation_steps": [
                        "1. Add exponential backoff",
                        "2. Enable autoscaling",
                        "3. Monitor metrics",
                    ],
                }
            ],
            "TIMEOUT": [
                {
                    "title": "Optimize timeout configurations and performance",
                    "rationale": [
                        "Timeouts suggest processing delays",
                        "Configuration tuning often resolves issues",
                    ],
                    "action_type": "TIMEOUT_TUNE",
                    "risk_level": "MEDIUM",
                    "trade_offs": {
                        "pros": "Quick configuration fix",
                        "cons": "May mask performance issues",
                    },
                    "estimated_time": "45 minutes",
                    "priority": 1,
                    "aws_services": ["Lambda", "ALB", "API Gateway"],
                    "implementation_steps": [
                        "1. Analyze processing times",
                        "2. Increase timeouts",
                        "3. Monitor performance",
                    ],
                }
            ],
        }

        return fallback_recs.get(
            category,
            [
                {
                    "title": "Investigate and fix configuration issues",
                    "rationale": [
                        "Configuration problems are common causes",
                        "Systematic review often identifies root cause",
                    ],
                    "action_type": "CONFIG_FIX",
                    "risk_level": "LOW",
                    "trade_offs": {
                        "pros": "Addresses common issues",
                        "cons": "May require deeper investigation",
                    },
                    "estimated_time": "1 hour",
                    "priority": 1,
                    "aws_services": ["CloudWatch", "Config"],
                    "implementation_steps": [
                        "1. Review configurations",
                        "2. Compare with working state",
                        "3. Apply corrections",
                    ],
                }
            ],
        )

    def _prioritize_solutions(self, state: RemediationState) -> RemediationState:
        """Use LLM to refine and prioritize the recommendations"""
        recommendations = state["recommendations"]
        signal = state["signal"]
        context = state["context"]

        if not recommendations:
            state["processing_stage"] = "prioritization_skipped"
            return state

        system_prompt = """You are prioritizing DevOps remediation recommendations based on business impact, risk, and implementation complexity.

Review the provided recommendations and optimize them for:
1. Business impact (higher impact = higher priority)
2. Implementation complexity (simpler = higher priority when impact is equal)
3. Risk level (lower risk = higher priority when other factors are equal)
4. Dependencies between recommendations

IMPORTANT: Your response must be valid JSON in this exact format:
{
    "optimized_recommendations": [
        {
            "title": "Updated title if needed",
            "rationale": ["updated rationale"],
            "action_type": "ACTION_TYPE",
            "risk_level": "LEVEL",
            "trade_offs": {"pros": "pros", "cons": "cons"},
            "estimated_time": "time",
            "priority": 1,
            "aws_services": ["services"],
            "implementation_steps": ["steps"],
            "dependency_notes": "Any dependencies or sequencing requirements"
        }
    ],
    "implementation_sequence": "Recommended order of execution with reasoning"
}

Return maximum 3 recommendations, ordered by priority."""

        prompt = f"""Prioritize and optimize these recommendations:

BUSINESS CONTEXT:
- Severity: {signal.get('severity', 'MEDIUM')}
- Urgency: {context.get('issue_analysis', {}).get('urgency', 'medium')}
- Business Impact: {context.get('issue_analysis', {}).get('business_impact', 'Unknown')}

CURRENT RECOMMENDATIONS:
{json.dumps(recommendations, indent=2)}

Optimize for maximum business value with minimal risk. Consider implementation dependencies."""

        response = self._call_llm(prompt, system_prompt)
        prioritized_data = self._extract_json_from_response(response)

        if prioritized_data and "optimized_recommendations" in prioritized_data:
            state["recommendations"] = prioritized_data["optimized_recommendations"]
            if "implementation_sequence" in prioritized_data:
                state["context"]["implementation_sequence"] = prioritized_data[
                    "implementation_sequence"
                ]

        # Ensure we have max 3 recommendations
        state["recommendations"] = state["recommendations"][:3]
        state["processing_stage"] = "prioritization_complete"
        return state

    def _format_output(self, state: RemediationState) -> RemediationState:
        """Format the final output for consumption by other agents"""
        recommendations = state["recommendations"]

        # Convert to Recommendation objects for consistency
        formatted_recs = []
        for i, rec in enumerate(recommendations):
            try:
                # Map string action types to enum
                action_type_str = rec.get("action_type", "CONFIG_FIX")
                action_type = (
                    ActionType(action_type_str)
                    if hasattr(ActionType, action_type_str)
                    else ActionType.CONFIG_FIX
                )

                # Map string risk levels to enum
                risk_str = rec.get("risk_level", "MEDIUM")
                risk_level = (
                    Severity(risk_str.lower())
                    if hasattr(Severity, risk_str.upper())
                    else Severity.MEDIUM
                )

                recommendation = Recommendation(
                    title=rec.get("title", f"Recommendation {i+1}"),
                    rationale=rec.get("rationale", ["No rationale provided"]),
                    action=action_type,
                    risk_level=risk_level,
                    trade_offs=rec.get(
                        "trade_offs", {"pros": "Benefits", "cons": "Considerations"}
                    ),
                    estimated_time=rec.get("estimated_time", "Unknown"),
                    priority=rec.get("priority", i + 1),
                    aws_services=rec.get("aws_services", []),
                    implementation_steps=rec.get(
                        "implementation_steps", ["Review and implement"]
                    ),
                )
                formatted_recs.append(asdict(recommendation))
            except Exception as e:
                # Fallback for malformed recommendations
                fallback_rec = Recommendation(
                    title=f"Recommendation {i+1}",
                    rationale=["Recommendation needs review"],
                    action=ActionType.CONFIG_FIX,
                    risk_level=Severity.MEDIUM,
                    trade_offs={
                        "pros": "Potential resolution",
                        "cons": "Needs investigation",
                    },
                    estimated_time="1 hour",
                    priority=i + 1,
                    aws_services=["CloudWatch"],
                    implementation_steps=[
                        "1. Investigate issue",
                        "2. Apply fix",
                        "3. Monitor results",
                    ],
                )
                formatted_recs.append(asdict(fallback_rec))

        state["recommendations"] = formatted_recs
        state["analysis_complete"] = True
        state["processing_stage"] = "formatting_complete"
        return state

    def get_recommendations(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point: takes classified signal and returns remediation recommendations

        Args:
            signal: Dict containing classified error information from Agent A

        Returns:
            Dict containing recommendations and analysis context
        """
        # Check if we have minimal structured data or need to analyze raw text
        has_structured_data = (
            signal.get("category")
            and signal.get("category") != "UNKNOWN"
            and signal.get("severity")
            and signal.get("component")
        )

        # If we don't have good structured data, enhance the signal with raw text analysis
        if not has_structured_data:
            logger.info(
                "Insufficient structured data detected, enhancing signal with raw text analysis"
            )
            signal = self._enhance_signal_from_raw_text(signal)

        initial_state = RemediationState(
            signal=signal,
            category=signal.get("category", "CONFIG"),
            severity=signal.get("severity", "MEDIUM"),
            component=signal.get("component", "unknown"),
            context={},
            recommendations=[],
            analysis_complete=False,
            error_message=None,
            processing_stage="initialized",
        )

        try:
            # Execute the remediation graph
            final_state = self.graph.invoke(initial_state)

            return {
                "recommendations": final_state.get("recommendations", []),
                "analysis_context": final_state.get("context", {}),
                "processing_info": {
                    "stage": final_state.get("processing_stage", "unknown"),
                    "success": final_state.get("analysis_complete", False),
                    "timestamp": datetime.now().isoformat(),
                    "enhanced_from_raw_text": not has_structured_data,
                },
            }
        except Exception as e:
            return {
                "recommendations": self._generate_fallback_recommendations(signal),
                "analysis_context": {"error": f"Processing failed: {str(e)}"},
                "processing_info": {
                    "stage": "error_fallback",
                    "success": False,
                    "timestamp": datetime.now().isoformat(),
                    "enhanced_from_raw_text": not has_structured_data,
                },
            }

    def _enhance_signal_from_raw_text(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance signal data by analyzing raw text when structured data is insufficient

        Args:
            signal: Original signal with potentially incomplete structured data

        Returns:
            Enhanced signal with better categorization and extracted information
        """
        # Get the raw text - could be from 'text', 'error_message', or other fields
        raw_text = (
            signal.get("text", "")
            or signal.get("error_message", "")
            or signal.get("message", "")
            or str(signal)
        )
        logger.info(f"Raw text for enhancement: {raw_text}")

        if not raw_text or len(raw_text.strip()) < 10:
            logger.warning("No sufficient raw text found for enhancement")
            return signal

        system_prompt = """You are an expert DevOps engineer analyzing raw log data to extract structured information.

Your task is to analyze the provided raw log/error text and extract key information for DevOps remediation.

IMPORTANT: Your response must be valid JSON in this exact format:
{
    "category": "IAM|THROTTLING|TIMEOUT|CONFIG|CAPACITY|NETWORK|STORAGE|COMPUTE",
    "severity": "LOW|MEDIUM|HIGH|CRITICAL",
    "component": "specific AWS service or component name",
    "error_message": "clean, concise error description",
    "region": "AWS region if mentioned",
    "resource_id": "resource identifier if available",
    "http_code": "HTTP status code if present",
    "service_type": "AWS service type",
    "additional_context": {
        "timestamp": "extracted timestamp if available",
        "request_id": "request ID if present",
        "other_relevant_info": "any other important details"
    }
}

Focus on extracting actionable information for DevOps troubleshooting."""

        prompt = f"""Analyze this raw log/error data and extract structured information:

RAW LOG DATA:
{raw_text}

Extract and categorize the key information needed for DevOps analysis and remediation."""

        try:
            response = self._call_llm(prompt, system_prompt)
            enhanced_data = self._extract_json_from_response(response)

            if enhanced_data:
                # Merge enhanced data with original signal, preserving any existing good data
                enhanced_signal = {**signal}  # Start with original

                # Update with enhanced data, but don't overwrite good existing data
                for key, value in enhanced_data.items():
                    if key == "additional_context":
                        # Merge additional context
                        existing_context = enhanced_signal.get("additional_context", {})
                        enhanced_signal["additional_context"] = {
                            **existing_context,
                            **value,
                        }
                    elif not enhanced_signal.get(key) or enhanced_signal.get(key) in [
                        "UNKNOWN",
                        "unknown",
                        "",
                    ]:
                        # Only update if we don't have good existing data
                        enhanced_signal[key] = value

                # Ensure we preserve the original raw text
                enhanced_signal["original_raw_text"] = raw_text

                logger.info(
                    f"Enhanced signal: category={enhanced_signal.get('category')}, "
                    f"severity={enhanced_signal.get('severity')}, "
                    f"component={enhanced_signal.get('component')}"
                )

                return enhanced_signal
            else:
                logger.warning("Failed to extract structured data from raw text")
                return signal

        except Exception as e:
            logger.error(f"Error enhancing signal from raw text: {e}")
            return signal


# Utility functions for integration with other agents
def format_recommendations_for_slack(result: Dict[str, Any]) -> str:
    """Format recommendations for Slack posting (Agent C integration)"""
    recommendations = result.get("recommendations", [])

    if not recommendations:
        return "🚨 *DevOps Issue Detected* 🚨\n\nNo specific recommendations available. Manual investigation required."

    slack_message = "🚨 *DevOps Issue Analysis Complete* 🚨\n\n"

    # Add analysis summary if available
    analysis_context = result.get("analysis_context", {})
    issue_analysis = analysis_context.get("issue_analysis", {})

    if issue_analysis:
        slack_message += f"**Root Cause:** {issue_analysis.get('root_cause', 'Under investigation')}\n"
        slack_message += f"**Business Impact:** {issue_analysis.get('business_impact', 'Assessment pending')}\n"
        slack_message += (
            f"**Urgency:** {issue_analysis.get('urgency', 'medium').upper()}\n\n"
        )

    for i, rec in enumerate(recommendations, 1):
        slack_message += f"*🔧 Solution {i}: {rec.get('title', 'Recommendation')}*\n"
        slack_message += f"⏱️ **Time:** {rec.get('estimated_time', 'Unknown')}\n"
        slack_message += f"⚠️ **Risk:** {rec.get('risk_level', 'MEDIUM')}\n"
        slack_message += f"🏷️ **Action:** {rec.get('action', 'REVIEW')}\n"

        # Add rationale
        rationale = rec.get("rationale", [])
        if rationale:
            slack_message += "\n**Why this helps:**\n"
            for reason in rationale[:3]:  # Limit to 3 reasons for brevity
                slack_message += f"• {reason}\n"

        # Add trade-offs
        trade_offs = rec.get("trade_offs", {})
        if trade_offs:
            slack_message += (
                f"\n**Pros:** {trade_offs.get('pros', 'Benefits assessment needed')}\n"
            )
            slack_message += (
                f"**Cons:** {trade_offs.get('cons', 'Risks assessment needed')}\n"
            )

        # Add implementation preview
        steps = rec.get("implementation_steps", [])
        if steps and len(steps) > 0:
            slack_message += f"\n**First Step:** {steps[0]}\n"

        if i < len(recommendations):
            slack_message += "\n" + "─" * 50 + "\n\n"

    # Add implementation sequence if available
    impl_sequence = analysis_context.get("implementation_sequence")
    if impl_sequence:
        slack_message += f"\n**🎯 Implementation Order:**\n{impl_sequence}\n"

    return slack_message


def format_recommendations_for_jira(
    result: Dict[str, Any], original_signal: Dict[str, Any]
) -> Dict[str, Any]:
    """Format recommendations for Jira ticket creation"""
    recommendations = result.get("recommendations", [])
    analysis_context = result.get("analysis_context", {})

    if not recommendations:
        return {
            "summary": "DevOps Issue Requires Investigation",
            "description": "Automated analysis was unable to generate specific recommendations. Manual investigation required.",
            "priority": "High",
            "labels": ["devops", "investigation-needed"],
            "components": ["monitoring"],
        }

    primary_rec = recommendations[0]
    issue_analysis = analysis_context.get("issue_analysis", {})

    description = f"""
**Issue Classification:**
• Category: {original_signal.get('category', 'Unknown')}
• Severity: {original_signal.get('severity', 'Unknown')}
• Component: {original_signal.get('component', 'Unknown')}
• Root Cause: {issue_analysis.get('root_cause', 'Under investigation')}

**Business Impact:**
{issue_analysis.get('business_impact', 'Impact assessment needed')}

**Recommended Solution:**
{primary_rec.get('title', 'Primary recommendation')}

**Implementation Steps:**
"""

    steps = primary_rec.get("implementation_steps", [])
    for step in steps:
        description += f"- {step}\n"

    description += f"""
**Estimates:**
• Time Required: {primary_rec.get('estimated_time', 'TBD')}
• Risk Level: {primary_rec.get('risk_level', 'MEDIUM')}
• AWS Services: {', '.join(primary_rec.get('aws_services', ['Multiple']))}

**Trade-offs:**
• Pros: {primary_rec.get('trade_offs', {}).get('pros', 'Benefits TBD')}
• Cons: {primary_rec.get('trade_offs', {}).get('cons', 'Considerations TBD')}
"""

    if len(recommendations) > 1:
        description += "\n**Alternative Solutions:**\n"
        for i, rec in enumerate(recommendations[1:], 2):
            description += f"{i}. {rec.get('title', 'Alternative solution')} "
            description += f"(Risk: {rec.get('risk_level', 'MEDIUM')}, Time: {rec.get('estimated_time', 'TBD')})\n"

    # Determine priority based on severity and urgency
    severity = original_signal.get("severity", "MEDIUM")
    urgency = issue_analysis.get("urgency", "medium")

    if severity in ["CRITICAL", "HIGH"] or urgency == "immediate":
        priority = "Highest"
    elif severity == "HIGH" or urgency == "high":
        priority = "High"
    else:
        priority = "Medium"

    return {
        "summary": f"DevOps: {primary_rec.get('title', 'Issue Resolution Required')}",
        "description": description,
        "priority": priority,
        "labels": [
            "devops",
            "automated-analysis",
            str(primary_rec.get("action", "review")).lower(),
        ],
        "components": primary_rec.get("aws_services", ["cloudwatch"]),
    }


def create_remediator_from_env() -> LangGraphRemediator:
    """Create a LangGraphRemediator instance using environment variables"""
    api_key = os.getenv("OPENROUTER_API_KEY")
    base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    model = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o")

    return LangGraphRemediator(api_key=api_key, base_url=base_url, model=model)


def run_example_analysis():
    """Run an example analysis with sample data"""
    try:
        # Initialize the LangGraph remediation system
        remediator = create_remediator_from_env()

        # Example signal from Agent A
        sample_signal = {
            "category": "IAM",
            "severity": "HIGH",
            "component": "lambda-function",
            "region": "us-east-1",
            "resource_id": "my-critical-function",
            "http_code": 403,
            "error_message": "User: arn:aws:sts::123456789012:assumed-role/lambda-execution-role/my-critical-function is not authorized to perform: s3:GetObject on resource: arn:aws:s3:::critical-data-bucket/config.json",
            "additional_context": {
                "timestamp": "2024-01-15T10:30:00Z",
                "frequency": "increasing",
                "affected_users": "production_workload",
            },
        }

        print("🔍 Processing DevOps issue with LangGraph...")
        logger.info("Starting remediation analysis")

        result = remediator.get_recommendations(sample_signal)

        print("\n📊 Analysis Results:")
        print(f"Success: {result['processing_info']['success']}")
        print(f"Stage: {result['processing_info']['stage']}")
        print(f"Timestamp: {result['processing_info']['timestamp']}")

        recommendations = result.get("recommendations", [])
        print(f"\n📋 Generated {len(recommendations)} recommendations:")

        for i, rec in enumerate(recommendations, 1):
            print(f"\n{i}. {rec.get('title', 'Untitled Recommendation')}")
            print(
                f"   Priority: {rec.get('priority', 'N/A')}, Risk: {rec.get('risk_level', 'N/A')}"
            )
            print(f"   Time: {rec.get('estimated_time', 'N/A')}")
            print(f"   Action: {rec.get('action', 'N/A')}")

            # Show implementation steps
            steps = rec.get("implementation_steps", [])
            if steps:
                print(
                    f"   Steps: {steps[0][:50]}..."
                    if len(steps[0]) > 50
                    else f"   Steps: {steps[0]}"
                )

        print("\n📱 Slack Format Preview:")
        print("=" * 50)
        print(format_recommendations_for_slack(result))

        print("\n🎫 Jira Format Preview:")
        print("=" * 50)
        jira_data = format_recommendations_for_jira(result, sample_signal)
        print(f"Summary: {jira_data['summary']}")
        print(f"Priority: {jira_data['priority']}")
        print(f"Labels: {', '.join(jira_data['labels'])}")

        logger.info("Example analysis completed successfully")

    except ValueError as e:
        print(f"❌ Configuration Error: {e}")
        print("\n💡 To fix this:")
        print("1. Set OPENROUTER_API_KEY environment variable")
        print("2. Or create a .env file with: OPENROUTER_API_KEY=your_key_here")
        logger.error(f"Configuration error: {e}")

    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        logger.error(f"Unexpected error during analysis: {e}")


# Example usage and testing
if __name__ == "__main__":
    print("🚀 Agent B: Enhanced Recommendation Engine")
    print("=" * 50)

    # Check if API key is available
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("⚠️  No API key found in environment variables")
        print("\n💡 Setup Instructions:")
        print("1. Get an API key from OpenRouter (https://openrouter.ai)")
        print("2. Set environment variable: export OPENROUTER_API_KEY=your_key_here")
        print("3. Or create a .env file with: OPENROUTER_API_KEY=your_key_here")
        print("\n🔧 Optional environment variables:")
        print("- OPENROUTER_BASE_URL (default: https://openrouter.ai/api/v1)")
        print("- OPENROUTER_MODEL (default: openai/gpt-4o)")
    else:
        print("✅ API key found, running example analysis...")
        run_example_analysis()
