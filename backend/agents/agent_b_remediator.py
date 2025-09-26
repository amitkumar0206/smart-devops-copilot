# Agent B: Recommendation engine (rule-based demo)
from typing import Dict, Any, List

def recommendations(signal: Dict[str, Any]) -> List[Dict[str, Any]]:
    cat = signal.get("category", "CONFIG")
    recs = []
    if cat == "IAM":
        recs.append({
            "title": "Add missing IAM permission (e.g., s3:GetObject or kms:Decrypt)",
            "why": [
                "AccessDenied indicates the caller lacks required actions.",
                "Grant least-privilege to the principal used by your workload (OAC/Role)."
            ],
            "action": "IAM_POLICY_UPDATE",
            "risk": "low",
        })
        recs.append({
            "title": "Validate resource policy (bucket policy / KMS key policy)",
            "why": [
                "Even with IAM allow, a deny in the resource policy blocks access.",
                "Ensure principal (role or OAC) is permitted."
            ],
            "action": "RESOURCE_POLICY_UPDATE",
            "risk": "medium",
        })
    elif cat == "THROTTLING":
        recs.append({
            "title": "Enable autoscaling / increase provisioned capacity",
            "why": [
                "Throttling means capacity is lower than traffic.",
                "Autoscaling adapts to spikes while controlling cost."
            ],
            "action": "CAPACITY_SCALE",
            "risk": "low",
        })
        recs.append({
            "title": "Add client-side retry with backoff",
            "why": ["Reduces user-visible failures during brief spikes."],
            "action": "RETRY_POLICY",
            "risk": "low",
        })
    elif cat == "TIMEOUT":
        recs.append({
            "title": "Increase timeout & memory (Lambda) or target timeouts (ALB/API GW)",
            "why": ["Long-running workloads need tuned timeouts.", "Memory increase speeds Lambda CPU."],
            "action": "TIMEOUT_TUNE",
            "risk": "medium",
        })
        recs.append({
            "title": "Scale underlying service (ASG/ECS/RDS)",
            "why": ["If saturation causes slow responses, scaling helps restore SLOs."],
            "action": "CAPACITY_SCALE",
            "risk": "medium",
        })
    elif cat == "QUOTA":
        recs.append({
            "title": "Request service quota increase or redesign to reduce usage",
            "why": ["LimitExceeded suggests quota walls; request raise via Service Quotas."],
            "action": "QUOTA_INCREASE",
            "risk": "low",
        })
    elif cat == "SCALING":
        recs.append({
            "title": "Increase desired capacity (ASG/ECS) temporarily",
            "why": ["Insufficient capacity/events indicate underprovisioning."],
            "action": "CAPACITY_SCALE",
            "risk": "low",
        })
        recs.append({
            "title": "Tune scaling policies (CPU/Request-based)",
            "why": ["Right triggers avoid flapping and reduce cost."],
            "action": "SCALING_POLICY_TUNE",
            "risk": "low",
        })
    else:
        recs.append({
            "title": "Fix configuration (region/ARN/parameter mismatch)",
            "why": ["Misconfigurations are common when resources drift."],
            "action": "CONFIG_FIX",
            "risk": "low",
        })
    return recs
