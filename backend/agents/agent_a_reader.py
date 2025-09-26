# Agent A: Log & Signal Reader (rule-based demo)
from typing import Dict, Any, List
import re

CATEGORIES = [
    "IAM",
    "THROTTLING",
    "TIMEOUT",
    "QUOTA",
    "CONFIG",
    "SCALING",
]

def extract_fields(text: str) -> Dict[str, Any]:
    fields = {}
    m_region = re.search(r"(?i)region[:=]\s*([a-z0-9-]+)", text)
    if m_region:
        fields["region"] = m_region.group(1)
    m_res = re.search(r"arn:aws:[^\s]+", text)
    if m_res:
        fields["resource_arn"] = m_res.group(0)
    if "AccessDenied" in text or "access denied" in text.lower():
        fields["access_denied"] = True
    if "Throttling" in text or "Rate exceeded" in text or "429" in text:
        fields["throttling"] = True
    if "Timeout" in text or "timed out" in text.lower() or "504" in text:
        fields["timeout"] = True
    if "LimitExceeded" in text or "quota" in text.lower():
        fields["quota"] = True
    if "NoSuchBucket" in text or "InvalidParameter" in text or "not found" in text.lower():
        fields["config_error"] = True
    if "Insufficient capacity" in text or "cannot schedule" in text or "desiredCount" in text:
        fields["scaling"] = True
    return fields

def classify(text: str) -> str:
    f = extract_fields(text)
    if f.get("access_denied"):
        return "IAM"
    if f.get("throttling"):
        return "THROTTLING"
    if f.get("timeout"):
        return "TIMEOUT"
    if f.get("quota"):
        return "QUOTA"
    if f.get("config_error"):
        return "CONFIG"
    if f.get("scaling"):
        return "SCALING"
    return "CONFIG"

def run(text: str) -> Dict[str, Any]:
    fields = extract_fields(text)
    category = classify(text)
    return {
        "category": category,
        "fields": fields,
        "highlights": _highlights(text),
    }

def _highlights(text: str) -> List[str]:
    hints = []
    for kw in ["AccessDenied", "Throttling", "Timeout", "LimitExceeded", "InvalidParameter", "504", "429"]:
        if kw.lower() in text.lower():
            hints.append(kw)
    return hints
