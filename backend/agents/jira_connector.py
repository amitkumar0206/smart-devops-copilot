
import sys
import os
import importlib.util
from langchain.agents import initialize_agent
from langchain.chat_models import ChatOpenAI
from langchain.tools import Tool
import requests
import json
import sys
import importlib.util
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../ui')))
spec = importlib.util.spec_from_file_location("loadConfig", os.path.join(os.path.dirname(__file__), '../../ui/loadConfig.py'))
loadConfig = importlib.util.module_from_spec(spec)
spec.loader.exec_module(loadConfig)
read_config = loadConfig.read_config
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv("OPENROUTER_API_KEY")
if not api_key:
    print("⚠️  OPENROUTER_API_KEY not found - LLM operations will be limited")
    print("   You can still complete postprocessor and retrieval exercises")
else:
    print("✅ OPENROUTER_API_KEY found - full advanced RAG functionality available")


# ============================================================
# 1. MCP Tool (wrapper around Jira API) - simple implementation
# ============================================================

def create_jira_issue(issue_data: dict) -> str:
    """
    Connects to Jira via MCP-like interface and creates a new issue.
    Input: dict with keys {project, summary, description, priority}
    """
    config = read_config()

    JIRA_BASE_URL = config["General"]["jira_base_url"]   # e.g. https://your-domain.atlassian.net
    JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN") # Atlassian API token
    JIRA_EMAIL = config["General"]["jira_email"]         # Your Jira account email

    url = f"{JIRA_BASE_URL}/rest/api/3/issue"
    headers = {
        "Content-Type": "application/json"
    }
    auth = (JIRA_EMAIL, JIRA_API_TOKEN)

    payload = {
            "fields": {
                "project": {"key": issue_data["project"]},
                "summary": issue_data["summary"],
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {"type": "text", "text": issue_data["description"]}
                            ]
                        }
                    ]
                },
                "issuetype": {"name": "Problem"}
            }
        }

    response = requests.post(url, headers=headers, auth=auth, data=json.dumps(payload))
    if response.status_code == 201:
        issue_key = response.json()["key"]
        return f"✅ Jira issue created successfully: {issue_key}"
    else:
        return f"❌ Failed to create Jira issue: {response.status_code}, {response.text}"


# ============================================================
# 2. Register MCP tool for LangChain agent
# ============================================================

jira_tool = Tool(
    name="jira.create_issue",
    func=lambda x: create_jira_issue(_extract_json(x)),
    description="Creates a Jira issue. Input must be a JSON string with keys: project, summary, description, priority."
)

# Helper to robustly extract the first JSON object from a string
import re
def _extract_json(s):
    match = re.search(r'({.*})', s, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception as e:
            return {"error": f"JSON parsing failed: {e}"}
    return {"error": "No valid JSON found in input."}

# ============================================================
# 3. Setup LangChain Agent
# ============================================================

llm = ChatOpenAI(model="gpt-4o-mini",
                openai_api_key=api_key,
                temperature=0.3,
                max_tokens=200,
                base_url="https://openrouter.ai/api/v1")  # or gpt-5 if available

agent = initialize_agent(
    tools=[jira_tool],
    llm=llm,
    verbose=True
)

# ============================================================
# 4. Example Input from Log Agent
# ============================================================

log_issue_json = {
    "fields": {
        "project": {"key": "AI"},
        "summary": "NullPoiterException timeout in Service X",
        "description": "NullPoiterException in logs at 12:35PM. Affected 23 requests.",
        "issuetype": {"name": "Problem"}   # try with "Incident" or "Service request"
    }
}

# ============================================================
# 5. Run the Agent
# ============================================================

result = agent.run(f"Create a Jira ticket with this JSON: {json.dumps(log_issue_json)}")
print(result)
