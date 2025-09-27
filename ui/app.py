import streamlit as st
import requests
import os
from dotenv import load_dotenv
from loadConfig import read_config

# Load environment variables from .env file
load_dotenv()
# Read configuration file if needed
config_data = read_config()

# Streamlit app configuration
st.set_page_config(page_title="Smart DevOps Copilot", layout="wide")

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

# Form for user input
with st.form("analyze_form"):
    text = st.text_area(
        "Paste a log/error snippet",
        height=200,
        placeholder="Paste CloudWatch log lines here...",
    )
    uploaded = st.file_uploader("...or upload a small .txt log", type=["txt", "log"])
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
                    f"⚠️ Analysis completed with fallbacks (Stage: {processing_info.get('stage', 'unknown')})"
                )

            # Create columns for better layout
            col1, col2 = st.columns([1, 1])

            with col1:
                st.subheader("🔍 Detected Issue")
                signal = data.get("signal", {})

                # Display key signal information in a more readable format
                if signal:
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
                    st.error("No signal data received")

            with col2:
                st.subheader("🧠 Analysis Context")
                analysis_context = data.get("analysis_context", {})

                if analysis_context:
                    issue_analysis = analysis_context.get("issue_analysis", {})
                    if issue_analysis:
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
                    if technical_context:
                        with st.expander("🔧 Technical Details"):
                            aws_services = technical_context.get(
                                "aws_services_involved", []
                            )
                            if aws_services:
                                st.write("**AWS Services:**", ", ".join(aws_services))

                            error_patterns = technical_context.get("error_patterns", [])
                            if error_patterns:
                                st.write(
                                    "**Error Patterns:**", ", ".join(error_patterns)
                                )

                            triggers = technical_context.get("likely_triggers", [])
                            if triggers:
                                st.write("**Likely Triggers:**", ", ".join(triggers))
                else:
                    st.info("No detailed analysis context available")

            # Display recommendations in full width
            st.subheader("💡 Intelligent Recommendations")
            recommendations = data.get("recommendations", [])

            if recommendations:
                for i, rec in enumerate(recommendations, 1):
                    # Create a more detailed recommendation display
                    with st.expander(
                        f"🔧 Solution {i}: {rec.get('title', 'Untitled')}",
                        expanded=(i == 1),
                    ):
                        rec_col1, rec_col2 = st.columns([2, 1])

                        with rec_col1:
                            # Rationale
                            rationale = rec.get("rationale", [])
                            if rationale:
                                st.write("**Why this helps:**")
                                for reason in rationale:
                                    st.write(f"• {reason}")

                            # Implementation steps
                            steps = rec.get("implementation_steps", [])
                            if steps:
                                st.write("**Implementation Steps:**")
                                for step in steps:
                                    st.write(f"{step}")

                        with rec_col2:
                            # Metadata
                            st.metric("Priority", rec.get("priority", "N/A"))
                            st.metric("Risk Level", rec.get("risk_level", "Unknown"))
                            st.metric(
                                "Estimated Time", rec.get("estimated_time", "Unknown")
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
