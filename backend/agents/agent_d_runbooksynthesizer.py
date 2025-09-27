import os
import json
import uuid
import hashlib
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# LLM client used in Agent B; adapt if you use a different client.
# from langchain_openai import ChatOpenAI
# If you use OpenAI's official client or LangChain's OpenAI class, swap imports accordingly.
try:
    from langchain_openai import ChatOpenAI  # keep consistent with Agent B style
except Exception:
    ChatOpenAI = None  # allow graceful failure if not installed

# ---------------------------------------------------------------------
# Logging and environment
# ---------------------------------------------------------------------
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("runbook-synthesizer")

# Load environment variables from project root (two levels up like Agent B)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

# ---------------------------------------------------------------------
# Pydantic models (output schema)
# ---------------------------------------------------------------------
class StepItem(BaseModel):
    id: str
    title: str
    description: str
    commands: List[str] = Field(default_factory=list)
    safety_checks: List[str] = Field(default_factory=list)
    verification: List[str] = Field(default_factory=list)
    rollback: Optional[str] = None
    responsible: Optional[str] = None
    estimated_time_min: Optional[int] = None
    risk: str = Field(..., description="low|medium|high")

class ChainOfCustody(BaseModel):
    generated_by: str
    generated_id: str
    generator_tool_version: str
    source_hash: str
    approvals_required: bool
    audit_log_cmd: str

class RunbookResult(BaseModel):
    runbook_id: str
    generated_at: str
    source_text: str
    summary: str
    checklist: List[StepItem]
    chain_of_custody: ChainOfCustody
    recommendations: List[str] = Field(default_factory=list)

# ---------------------------------------------------------------------
# Prompt template and helpers
# ---------------------------------------------------------------------
PROMPT_TEMPLATE = """
You are Runbook-Synthesizer — convert the following plain-English runbook into a safe, executable,
step-by-step checklist for operators. Output must be valid JSON following the schema (no extra text).

RUNBOOK:
\"\"\"
{runbook}
\"\"\"

REQUIREMENTS:
1. Always include dry-run forms of commands (e.g., `--dry-run`, `terraform plan`).
2. For destructive actions include at least two safety checks and require approvals.
3. Provide chain_of_custody metadata (generated_by, generated_id, generator_tool_version, source_hash, approvals_required, audit_log_cmd).
4. Each checklist step must include id (uuid), title, description, commands (list), safety_checks (list), verification (list), rollback (string|null), responsible (role), estimated_time_min (int|null), and risk (low|medium|high).
5. The output MUST be a single JSON object exactly matching the schema below. No markdown, no explanation.

SCHEMA:
{
  "runbook_id": "string",
  "generated_at": "ISO8601 string",
  "source_text": "string",
  "summary": "string",
  "checklist": [
    {
      "id": "string",
      "title": "string",
      "description": "string",
      "commands": ["string"],
      "safety_checks": ["string"],
      "verification": ["string"],
      "rollback": "string or null",
      "responsible": "string",
      "estimated_time_min": integer or null,
      "risk": "low|medium|high"
    }
  ],
  "chain_of_custody": {
    "generated_by": "string",
    "generated_id": "string",
    "generator_tool_version": "string",
    "source_hash": "string",
    "approvals_required": boolean,
    "audit_log_cmd": "string"
  },
  "recommendations": ["string"]
}

Now produce the JSON for the runbook provided. Make commands explicit (show sample AWS CLI/Terraform syntax), and ensure all commands are dry-run or plan only.
"""

def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def iso_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

# ---------------------------------------------------------------------
# LLM call wrapper (mirrors Agent B style)
# ---------------------------------------------------------------------
def _init_llm(model_name: Optional[str] = None, api_key_env: str = "OPENROUTER_API_KEY") -> Any:
    """
    Initialize and return an LLM client instance. Mirrors the pattern used in Agent B.
    Swap implementation if you use a different provider.
    """
    logger.info("Initializing LLM for Runbook-Synthesizer")
    api_key = os.getenv(api_key_env)
    if not api_key:
        logger.error("LLM API key not found in environment variable: %s", api_key_env)
        return None

    model_name = model_name or os.getenv("RUNBOOK_LLM_MODEL", "x-ai/grok-4-fast:free")
    temperature = float(os.getenv("RUNBOOK_LLM_TEMPERATURE", "0.0"))
    max_tokens = int(os.getenv("RUNBOOK_LLM_MAX_TOKENS", "8000"))
    base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

    if ChatOpenAI is None:
        logger.error("ChatOpenAI client not available. Install langchain_openai or swap client.")
        return None

    try:
        llm = ChatOpenAI(
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            base_url=base_url,
            api_key=api_key,
            default_headers={
                "HTTP-Referer": "https://localhost:8501",
                "X-Title": "Runbook-Synthesizer"
            }
        )
        logger.info("LLM initialized: %s", model_name)
        return llm
    except Exception as e:
        logger.exception("Failed to initialize LLM: %s", e)
        return None

def _call_llm(llm, prompt_text: str) -> Optional[str]:
    """
    Send prompt_text to the LLM and return raw string response similar to Agent B's invoke usage.
    """
    if llm is None:
        logger.error("LLM instance is None, cannot call LLM")
        return None

    messages = [
        {"role": "system", "content": "You are Runbook-Synthesizer — produce only the requested JSON."},
        {"role": "user", "content": prompt_text}
    ]
    try:
        logger.debug("Sending prompt to LLM (length=%d chars)", len(prompt_text))
        raw = llm.invoke(messages)
        # Agent B checks raw_result.content
        if hasattr(raw, 'content'):
            raw = raw.content
        logger.debug("Received raw LLM response (preview): %s", (raw[:400] + '...') if isinstance(raw, str) else str(type(raw)))
        return raw if isinstance(raw, str) else str(raw)
    except Exception as e:
        logger.exception("LLM call failed: %s", e)
        return None

# ---------------------------------------------------------------------
# JSON parse & validation helpers
# ---------------------------------------------------------------------
def _extract_json_object(raw: str) -> Optional[str]:
    """
    Try to extract the first JSON object from raw text robustly.
    Preference: full JSON object (starts with { and ends with }), but accept array-wrapped object.
    """
    if not raw:
        return None
    # Try strict parse first
    raw = raw.strip()
    # If the LLM returned only the object, return as-is if valid JSON
    try:
        json.loads(raw)
        return raw
    except Exception:
        pass

    # Search for first balanced JSON object { ... }
    # Simple heuristic using regex to find outermost {...}
    import re
    # Try object
    obj_match = re.search(r'\{\s*(?:[^{}]|\{[^{}]*\})*\s*\}', raw, re.DOTALL)
    if obj_match:
        candidate = obj_match.group(0)
        try:
            json.loads(candidate)
            return candidate
        except Exception:
            # fallback to more flexible approach below
            pass

    # Try to find a JSON block by looking for the schema keys (runbook_id) inside a JSON-like block
    arr_match = re.search(r'\[\s*\{', raw)
    if arr_match:
        # find first array-like block
        m = re.search(r'\[.*\]', raw, re.DOTALL)
        if m:
            candidate = m.group(0)
            try:
                json.loads(candidate)
                # if it's an array but we expect object, wrap or convert accordingly
                return candidate
            except Exception:
                pass

    logger.debug("Unable to robustly extract JSON object from LLM response")
    return None

def _parse_and_validate(raw: str, original_runbook: str) -> Optional[RunbookResult]:
    """
    Parse raw LLM output to RunbookResult and apply conservative defaults if fields missing.
    """
    json_str = _extract_json_object(raw)
    if not json_str:
        logger.error("No JSON found in LLM response")
        return None

    try:
        parsed = json.loads(json_str)
    except Exception as e:
        logger.exception("JSON parsing failed: %s", e)
        return None

    # If LLM returned an array (older variant) wrap into object if needed
    if isinstance(parsed, list):
        logger.warning("LLM returned a list; expected a single JSON object with top-level keys. Wrapping into object.")
        parsed = {
            "runbook_id": str(uuid.uuid4()),
            "generated_at": iso_now(),
            "source_text": original_runbook,
            "summary": "Generated checklist",
            "checklist": parsed,
            "chain_of_custody": {},
            "recommendations": []
        }

    # Ensure required defaults and chain_of_custody
    src_hash = sha256_hex(original_runbook)
    coc = parsed.get("chain_of_custody", {})
    coc.setdefault("generated_by", "Runbook-Synthesizer")
    coc.setdefault("generated_id", str(uuid.uuid4()))
    coc.setdefault("generator_tool_version", "1.0")
    coc.setdefault("source_hash", src_hash)
    coc.setdefault("approvals_required", True)
    coc.setdefault("audit_log_cmd", "echo 'Run audit commands here (e.g., aws describe ...)'")

    parsed.setdefault("runbook_id", str(uuid.uuid4()))
    parsed.setdefault("generated_at", iso_now())
    parsed.setdefault("source_text", original_runbook)
    parsed.setdefault("summary", parsed.get("summary", "Auto-generated runbook checklist"))
    parsed.setdefault("recommendations", parsed.get("recommendations", []))
    parsed["chain_of_custody"] = coc

    # Validate checklist items (coerce to StepItem where possible)
    checklist = parsed.get("checklist", [])
    validated_steps = []
    for idx, s in enumerate(checklist):
        try:
            # If s is already a dict with the fields, pydantic will validate / fill defaults
            si = StepItem(**s)
            validated_steps.append(si.dict())
        except Exception as e:
            logger.warning("Checklist item %d failed validation: %s. Attempting to coerce.", idx + 1, e)
            # Basic coercion: build minimal StepItem
            coerced = {
                "id": s.get("id") or str(uuid.uuid4()) if isinstance(s, dict) else str(uuid.uuid4()),
                "title": s.get("title") or ("Step %d" % (idx + 1)) if isinstance(s, dict) else ("Step %d" % (idx + 1)),
                "description": s.get("description") or "" if isinstance(s, dict) else "",
                "commands": s.get("commands") or [] if isinstance(s, dict) else [],
                "safety_checks": s.get("safety_checks") or [] if isinstance(s, dict) else [],
                "verification": s.get("verification") or [] if isinstance(s, dict) else [],
                "rollback": s.get("rollback") if isinstance(s, dict) else None,
                "responsible": s.get("responsible") or "oncall" if isinstance(s, dict) else "oncall",
                "estimated_time_min": s.get("estimated_time_min") if isinstance(s, dict) else None,
                "risk": s.get("risk") or "medium" if isinstance(s, dict) else "medium"
            }
            try:
                si = StepItem(**coerced)
                validated_steps.append(si.dict())
            except Exception as e2:
                logger.error("Coercion failed for checklist item %d: %s", idx + 1, e2)

    parsed["checklist"] = validated_steps

    # Final Pydantic model validation
    try:
        result = RunbookResult(**parsed)
        logger.info("Successfully validated RunbookResult with %d steps", len(result.checklist))
        return result
    except Exception as e:
        logger.exception("Final RunbookResult validation failed: %s", e)
        return None

# ---------------------------------------------------------------------
# Public Synthesizer function (core)
# ---------------------------------------------------------------------
def synthesize_runbook(runbook_text: str, dry_run_enforce: bool = True, llm_model: Optional[str] = None) -> Optional[RunbookResult]:
    """
    Synthesize a plain-English runbook into a structured RunbookResult object.
    - dry_run_enforce: if True, will check LLM output and insert an approval step for non-dry-run commands (best-effort).
    - llm_model: override model name used for generation.
    Returns RunbookResult on success, or None on failure.
    """
    logger.info("Synthesizing runbook (length=%d chars)", len(runbook_text))
    llm = _init_llm(model_name=llm_model)
    if llm is None:
        logger.error("LLM initialization failed. Aborting synthesis.")
        return None

    # Use string replacement instead of format to avoid issues with curly braces in template
    prompt_text = PROMPT_TEMPLATE.replace('{runbook}', runbook_text)
    raw = _call_llm(llm, prompt_text)
    if not raw:
        logger.error("No response from LLM")
        return None

    result = _parse_and_validate(raw, runbook_text)
    if result is None:
        logger.error("Failed to parse and validate LLM output")
        return None

    # Post-check: enforce dry-run in commands (best-effort check)
    if dry_run_enforce:
        problematic_commands = []
        for step in result.checklist:
            for cmd in step.commands:
                if not isinstance(cmd, str):
                    continue
                cmd_lower = cmd.lower()
                if (("terraform apply" in cmd_lower) or
                    ("--dry-run" not in cmd_lower and cmd_lower.startswith("aws ") and "delete" in cmd_lower) or
                    ("kubectl delete" in cmd_lower) or
                    ("rm -rf" in cmd_lower) or
                    ("apply -auto-approve" in cmd_lower) or
                    ("terraform apply -auto-approve" in cmd_lower)):
                    problematic_commands.append(cmd)

        if problematic_commands:
            logger.warning("Dry-run enforcement detected potentially destructive commands: %s", problematic_commands)
            # Insert a top-level manual approval step instead of failing outright
            extra_step = StepItem(
                id=str(uuid.uuid4()),
                title="Manual approval required: destructive commands detected",
                description="LLM output contains destructive/non-dry-run commands. Require human approver to convert to dry-run/plan and explicitly approve.",
                commands=[],
                safety_checks=[
                    "Require manual approval from infra-owner",
                    "Ensure MFA and SSO roles are used prior to execution"
                ],
                verification=["Review and replace destructive commands with dry-run variants (e.g., terraform plan)"],
                rollback=None,
                responsible="infra-owner",
                estimated_time_min=5,
                risk="high"
            )
            new_checklist = [extra_step.dict()] + result.checklist
            result.checklist = new_checklist

    logger.info("Synthesis complete: runbook_id=%s steps=%d", result.runbook_id, len(result.checklist))
    return result
 