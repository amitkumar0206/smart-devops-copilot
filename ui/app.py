import streamlit as st
import requests
from dotenv import load_dotenv
from loadConfig import read_config
from typing import Any, Dict

# Load environment variables from .env file
load_dotenv()
# Read configuration file if needed
config_data = read_config()

# Streamlit app configuration
st.set_page_config(page_title="Smart DevOps Copilot", layout="wide")

# Initialize session state for listener
if 'listener_initialized' not in st.session_state:
    st.session_state.listener_initialized = False
if 'listener_thread' not in st.session_state:
    st.session_state.listener_thread = None

# App title and description
st.title("🧠 Smart DevOps Copilot — Enhanced AI Remediation")
st.caption(
    "Paste a CloudWatch/log snippet → AI-powered analysis → intelligent recommendations"
)

# Backend URL configuration, if missing then use localhost
backend_url = config_data.get("General", {}).get(
    "COPILOT_BACKEND_URL", "http://localhost:8000"
)

# Add system status in sidebar
with st.sidebar:
    st.header("🔧 System Status")
    try:
        status_resp = requests.get(f"{backend_url}/status", timeout=5)
        if status_resp.ok:
            status_data = status_resp.json()
            st.success("✅ Backend Connected")
            st.info(f"🤖 Model: {status_data.get('model', 'N/A')}")
            st.info(f"🔄 Remediator: {status_data.get('remediator_type', 'N/A')}")
        else:
            st.error("❌ Backend Unavailable")
    except:
        st.error("❌ Backend Unavailable")

    st.header("📖 About")
    st.markdown(
        """
    This enhanced version uses:
    - **LangGraph** for multi-stage analysis
    - **LLM-powered** recommendations
    - **Intelligent prioritization**
    - **Rich context analysis**
    """
    )

    # Slack Listener Initialization Button
    st.header("🎧 Slack Integration")
    button_text = "Listener initialized" if st.session_state.listener_initialized else "Initialize listener"
    if st.button(button_text, key="listener_button"):
        if not st.session_state.listener_initialized:
            with st.spinner("Initializing listener..."):
                try:
                    resp = requests.post(f"{backend_url}/initialize-listener", timeout=10)
                    if resp.ok:
                        data = resp.json()
                        if data.get("success"):
                            st.session_state.listener_initialized = True
                            st.success("✅ Listener initialized successfully!")
                            st.rerun()  # Refresh to update button text
                        else:
                            st.error(f"❌ Failed to initialize listener: {data.get('error', 'Unknown error')}")
                    else:
                        st.error(f"❌ API error: {resp.status_code}")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

# Form for user input
with st.form("analyze_form"):
    text = st.text_area(
        "Paste a log/error snippet",
        height=200,
        placeholder="Paste CloudWatch log lines here...",
    )
    uploaded = st.file_uploader("...or upload a small .txt/.log or a cookbook .json file", type=["txt", "log", "json"])
    submitted = st.form_submit_button("Analyze")

    # Handle form submission
    if submitted:
        # Validate input - check if we have either text or file
        if not text.strip() and uploaded is None:
            st.error("Please provide either text input or upload a file.")
        else:
            # Show processing indicator
            with st.spinner(
                "🤖 AI is analyzing your log... This may take up to 2 minutes for LLM processing."
            ):
                try:
                    if uploaded is not None:
                        files = {"file": uploaded.getvalue()}
                        resp = requests.post(
                            f"{backend_url}/analyze_file",
                            files={"file": ("log.txt", uploaded.getvalue())},
                            timeout=120,  # Increased timeout for LLM processing
                        )
                    else:
                        resp = requests.post(
                            f"{backend_url}/analyze",
                            json={"text": text},
                            timeout=120,  # Increased timeout for LLM processing
                        )
                except requests.exceptions.Timeout:
                    st.error(
                        "⏰ Request timed out. The AI analysis is taking longer than expected. This could be due to:"
                    )
                    st.error("• High load on the LLM service")
                    st.error("• Complex log analysis requiring more processing time")
                    st.error("• Network connectivity issues")
                    st.info(
                        "💡 Try again with a shorter log snippet or check your API key configuration."
                    )
                    resp = None
                except requests.exceptions.ConnectionError:
                    st.error("🔌 Cannot connect to backend server. Please ensure:")
                    st.error("• Backend server is running")
                    st.error("• Backend URL is correct in configuration")
                    st.error("• No firewall blocking the connection")
                    resp = None
                except Exception as e:
                    st.error(f"❌ Unexpected error: {str(e)}")
                    resp = None

        # Display results
        if resp and resp.ok:
            data = resp.json()

            # Show processing info
            processing_info = data.get("processing_info", {})
            if processing_info.get("success", False):
                st.success(
                    f"✅ Analysis completed successfully (Stage: {processing_info.get('stage', 'unknown')})"
                )
            else:
                st.warning(
                    f"⚠️ Analysis completed (Stage: {processing_info.get('stage', 'unknown')})"
                )

            # Create columns for better layout
            col1, col2 = st.columns([1, 1])

            with col1:
                st.subheader("🔍 Detected Issue")
                signal = data.get("log", {})

                # Display key signal information in a more readable format
                # Handle case where signal might be a string instead of a dict
                if signal:
                    if isinstance(signal, dict):
                        st.metric("Category", signal.get("category", "Unknown"))
                        st.metric("Severity", signal.get("severity", "Unknown"))
                        st.metric("Component", signal.get("component", "Unknown"))

                        if signal.get("error_message"):
                            st.text_area(
                                "Error Message",
                                signal.get("error_message"),
                                height=100,
                                disabled=True,
                            )

                        # Show additional context if available
                        additional_context = signal.get("additional_context", {})
                        if additional_context:
                            with st.expander("📋 Additional Context"):
                                st.json(additional_context)
                    else:
                        # If signal is a string or other type, display it as raw text
                        st.text_area(
                            "Log Content",
                            str(signal),
                            height=200,
                            disabled=True,
                        )
                        st.info("Note: Received log data as text instead of structured format")
                else:
                    st.error("No signal data received")

            with col2:
                st.subheader("🧠 Analysis Context")
                analysis_context = data.get("analysis_context", {})

                if analysis_context and isinstance(analysis_context, dict):
                    issue_analysis = analysis_context.get("issue_analysis", {})
                    if issue_analysis and isinstance(issue_analysis, dict):
                        st.write(
                            "**Root Cause:**",
                            issue_analysis.get("root_cause", "Unknown"),
                        )
                        st.write(
                            "**Business Impact:**",
                            issue_analysis.get("business_impact", "Unknown"),
                        )
                        st.write(
                            "**Urgency:**",
                            issue_analysis.get("urgency", "medium").upper(),
                        )

                    technical_context = analysis_context.get("technical_context", {})
                    if technical_context and isinstance(technical_context, dict):
                        with st.expander("🔧 Technical Details"):
                            aws_services = technical_context.get(
                                "aws_services_involved", []
                            )
                            if aws_services and isinstance(aws_services, list):
                                st.write("**AWS Services:**", ", ".join(str(s) for s in aws_services))

                            error_patterns = technical_context.get("error_patterns", [])
                            if error_patterns and isinstance(error_patterns, list):
                                st.write(
                                    "**Error Patterns:**", ", ".join(str(p) for p in error_patterns)
                                )

                            triggers = technical_context.get("likely_triggers", [])
                            if triggers and isinstance(triggers, list):
                                st.write("**Likely Triggers:**", ", ".join(str(t) for t in triggers))
                else:
                    st.info("No detailed analysis context available")

            # Display recommendations in full width
            st.subheader("💡 Intelligent Recommendations")
            recommendations = data.get("recommendations", [])

            if recommendations:
                for i, rec in enumerate(recommendations, 1):
                    if isinstance(rec, dict):
                        title = rec.get('title', 'Untitled')
                    else:
                        title = str(rec) if rec else 'Untitled'
                    with st.expander(f"🔧 Solution {i}: {title}", expanded=(i == 1)):
                        rec_col1, rec_col2 = st.columns([2, 1])

                        with rec_col1:
                            if isinstance(rec, dict):
                                rationale = rec.get("rationale", [])
                                steps = rec.get("implementation_steps", [])
                            else:
                                rationale = []
                                steps = []
                            if rationale:
                                st.write("**Why this helps:**")
                                for reason in rationale:
                                    st.write(reason)
                            if steps:
                                st.write("**Implementation steps:**")
                                for step in steps:
                                    st.write(step)

                        with rec_col2:
                            # Metadata
                            rec_dict: Dict[str, Any] = {}
                            if isinstance(rec, dict):
                                rec_dict = rec
                                priority = rec_dict.get("priority", "N/A")
                                priority = rec_dict.get("priority", "N/A")

                            st.metric("Priority", str(priority))
                            st.metric("Priority", rec_dict.get("priority", "N/A"))
                            st.metric("Risk Level", rec_dict.get("risk_level", "Unknown"))
                            st.metric(
                                "Estimated Time", rec_dict.get("estimated_time", "Unknown")
                            )

                            # Action type
                            action = rec.get("action", "N/A")
                            if hasattr(action, "value"):
                                action = action.value
                            st.code(action, language="text")

                            # AWS Services
                            aws_services = rec.get("aws_services", [])
                            if aws_services:
                                st.write("**AWS Services:**")
                                for service in aws_services:
                                    st.badge(service)

                        # Trade-offs
                        trade_offs = rec.get("trade_offs", {})
                        if trade_offs:
                            trade_col1, trade_col2 = st.columns(2)
                            with trade_col1:
                                st.success(f"**Pros:** {trade_offs.get('pros', 'N/A')}")
                            with trade_col2:
                                st.warning(f"**Cons:** {trade_offs.get('cons', 'N/A')}")

                # Show implementation sequence if available
                impl_sequence = analysis_context.get("implementation_sequence")
                if impl_sequence:
                    with st.expander("🎯 Implementation Order"):
                        st.info(impl_sequence)
            else:
                st.error("No recommendations generated")

            # Display Runbook Steps
            st.markdown("---")
            st.subheader("📋 AI-Generated Runbook")
            st.caption("Step-by-step execution guide generated by AI based on your log analysis")
            runbook = data.get("runbook")
            if runbook:
                # Convert Pydantic model to dict if needed
                if hasattr(runbook, 'dict'):
                    runbook = runbook.dict()
                
                st.write(f"**Runbook ID:** `{runbook.get('runbook_id', 'N/A')}`")
                st.write(f"**Summary:** {runbook.get('summary', 'N/A')}")
                st.write(f"**Generated:** {runbook.get('generated_at', 'N/A')}")
                
                # Display each step in an expandable container
                checklist = runbook.get("checklist", [])
                if checklist:
                    for i, step in enumerate(checklist, 1):
                        # Risk color coding
                        risk = step.get("risk", "medium").lower()
                        risk_colors = {
                            "low": "🟢",
                            "medium": "🟡", 
                            "high": "🔴"
                        }
                        risk_icon = risk_colors.get(risk, "🟡")
                        
                        with st.expander(f"{risk_icon} Step {i}: {step.get('title', 'Untitled Step')}"):
                            col1, col2 = st.columns([2, 1])
                            
                            with col1:
                                st.write("**Description:**")
                                st.write(step.get("description", "No description provided"))
                                
                                if step.get("commands"):
                                    st.write("**Commands:**")
                                    for cmd in step.get("commands", []):
                                        st.code(cmd, language="bash")
                                
                                if step.get("safety_checks"):
                                    st.write("**Safety Checks:**")
                                    for check in step.get("safety_checks", []):
                                        st.write(f"✅ {check}")
                                
                                if step.get("verification"):
                                    st.write("**Verification:**")
                                    for verify in step.get("verification", []):
                                        st.write(f"🔍 {verify}")
                                
                                if step.get("rollback"):
                                    st.write("**Rollback:**")
                                    st.code(step.get("rollback"), language="bash")
                            
                            with col2:
                                st.write("**Details:**")
                                st.write(f"**Risk:** {risk.title()}")
                                if step.get("responsible"):
                                    st.write(f"**Responsible:** {step.get('responsible')}")
                                if step.get("estimated_time_min"):
                                    st.write(f"**Time:** {step.get('estimated_time_min')} min")
                    
                    # Display chain of custody information
                    if "chain_of_custody" in runbook:
                        coc = runbook.get("chain_of_custody", {})
                        with st.expander("🔒 Chain of Custody"):
                            st.write(f"**Generated by:** {coc.get('generated_by', 'N/A')}")
                            st.write(f"**Tool version:** {coc.get('generator_tool_version', 'N/A')}")
                            st.write(f"**Approvals required:** {coc.get('approvals_required', 'N/A')}")
                            if coc.get("audit_log_cmd"):
                                st.write("**Audit command:**")
                                st.code(coc.get("audit_log_cmd"), language="bash")
                    
                    # Display recommendations
                    if runbook.get("recommendations"):
                        st.write("**Additional Recommendations:**")
                        for rec in runbook.get("recommendations", []):
                            st.write(f"💡 {rec}")
                else:
                    st.info("No runbook steps generated for this analysis.")
            else:
                st.info("No runbook generated for this analysis.")

            # Code generation section (commented out since Agent C is disabled)
            # st.subheader("Generated Code")
            # tabs = st.tabs(["Terraform", "AWS CLI"])
            # with tabs[0]:
            #     st.code(data.get("code", {}).get("terraform", "# Agent C disabled"), language="hcl")
            # with tabs[1]:
            #     st.code(data.get("code", {}).get("cli", "# Agent C disabled"), language="bash")

            st.info(
                "💡 **Note:** Code generation (Agent C) is currently disabled. Focus is on intelligent analysis and recommendations."
            )

        elif resp:
            st.error(f"Backend error: {resp.status_code}")
            try:
                error_data = resp.json()
                st.json(error_data)
            except:
                st.text(resp.text)
        # If resp is None, error messages were already shown in the exception handlers above
st.info("Tip: Try files from the `fixtures/` folder in the repo.")
