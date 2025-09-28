
"""
Agent A — AWS Log Reader & Classifier
-------------------------------------
Reads logs (from CloudWatch or files) and classifies entries into normalization + categories
so that Agent B can recommend remediation.
"""
import json
import re
import time
import math
import datetime as dt
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any, Iterable, Tuple

# -------- Data Models --------

@dataclass
class LogRecord:
    ts: float                    # epoch seconds
    message: str
    source: str                  # e.g., "cloudwatch:/aws/lambda/foo" or "file:sample.jsonl"
    service_hint: Optional[str]  # e.g., "lambda", "apigw", "alb", "ecs", "eks", "s3", "dynamodb", "rds"
    raw: Dict[str, Any]          # original parsed object if available

@dataclass
class Finding:
    ts: float
    category: str                # e.g., "iam_access_denied", "throttling", "http_5xx", ...
    severity: str                # "low" | "medium" | "high" | "critical"
    probable_cause: str          # short text
    remediation_hint: str        # short action label for Agent B routing
    confidence: float            # 0..1
    source: str
    service: Optional[str]
    message_excerpt: str
    meta: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["ts_iso"] = dt.datetime.utcfromtimestamp(self.ts).isoformat() + "Z"
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


# -------- Rule Engine --------

@dataclass
class Rule:
    name: str
    pattern: re.Pattern
    category: str
    severity: str
    probable_cause: str
    remediation_hint: str
    confidence: float
    service_bias: Optional[str] = None

DEFAULT_RULES: List[Rule] = [
    # IAM / AuthZ
    Rule("iam_access_denied", re.compile(r"\b(AccessDenied|NotAuthorized|Unauthorized|User is not authorized|AuthorizationError)\b", re.I),
         "iam_access_denied", "high",
         "Request blocked by IAM/authorization policy.",
         "fix_iam_policy", 0.95, None),

    # Throttling / Rate / Capacity
    Rule("throttling", re.compile(r"\b(ThrottlingException|Rate exceeded|Too Many Requests|429\b|ProvisionedThroughputExceededException)\b", re.I),
         "throttling", "medium",
         "Service is throttling due to rate/capacity limits.",
         "retry_with_backoff_or_scale", 0.9, None),

    # HTTP 5xx
    Rule("http_5xx", re.compile(r"\b(5\d{2})\b.*\b(error|server error|bad gateway|gateway timeout|internal server error)\b", re.I),
         "http_5xx", "high",
         "Backend error surfaced as HTTP 5xx.",
         "check_dependency_and_scale", 0.85, None),
    Rule("http_5xx_compact", re.compile(r"\"status\"\s*:\s*5\d{2}|\bHTTP\/1\.\d\" 5\d{2}\b", re.I),
         "http_5xx", "high",
         "Backend error surfaced as HTTP 5xx.",
         "check_dependency_and_scale", 0.8, None),

    # Lambda
    Rule("lambda_timeout", re.compile(r"Task timed out after \d+.\d+ seconds|timed out", re.I),
         "lambda_timeout", "high",
         "Lambda exceeded configured timeout.",
         "increase_timeout_or_optimize", 0.9, "lambda"),
    Rule("lambda_oom", re.compile(r"\b(OutOfMemory|MemoryError)\b", re.I),
         "lambda_oom", "high",
         "Lambda ran out of memory.",
         "increase_memory_or_optimize", 0.9, "lambda"),
    Rule("lambda_init_error", re.compile(r"Init(?:ialization)? error|Unhandled exception", re.I),
         "lambda_init_error", "medium",
         "Lambda init/unhandled exception.",
         "fix_code_or_dependencies", 0.7, "lambda"),

    # Container / K8s / ECS
    Rule("container_crashloop", re.compile(r"CrashLoopBackOff|Back-off restarting failed container", re.I),
         "container_crashloop", "high",
         "Container restarting repeatedly.",
         "inspect_pod_logs_fix_crash", 0.95, "eks"),
    Rule("image_pull_error", re.compile(r"ImagePullBackOff|ErrImagePull|CannotPullContainerError", re.I),
         "image_pull_error", "high",
         "Image pull failed (auth/tag/network).",
         "fix_image_or_registry_access", 0.95, None),
    Rule("oom_killed", re.compile(r"\bOOMKilled\b", re.I),
         "oom_killed", "high",
         "Container killed due to OOM.",
         "increase_memory_or_optimize", 0.9, None),

    # Data Stores
    Rule("dynamodb_conditional", re.compile(r"ConditionalCheckFailedException", re.I),
         "dynamodb_conditional", "low",
         "DynamoDB conditional write failed (app logic).",
         "handle_expected_failure_or_retry", 0.8, "dynamodb"),
    Rule("rds_lock_wait", re.compile(r"deadlock found|lock wait timeout", re.I),
         "rds_lock_contention", "medium",
         "RDS lock contention or deadlock.",
         "optimize_queries_or_isolation", 0.7, "rds"),
    Rule("rds_connections", re.compile(r"too many connections", re.I),
         "rds_too_many_connections", "high",
         "RDS connection limit exceeded.",
         "use_pooling_or_increase_limit", 0.85, "rds"),

    # S3
    Rule("s3_access_denied", re.compile(r"S3.*AccessDenied|NoSuchBucket|SignatureDoesNotMatch", re.I),
         "s3_access_error", "high",
         "S3 access/signature/bucket error.",
         "verify_bucket_policy_and_credentials", 0.9, "s3"),
    Rule("s3_slowdown", re.compile(r"\bSlowDown\b", re.I),
         "s3_slowdown", "low",
         "S3 throttling/slowdown response.",
         "retry_with_backoff", 0.7, "s3"),

    # API Gateway
    Rule("apigw_timeout", re.compile(r"Endpoint request timed out|Execution failed due to configuration error", re.I),
         "apigw_timeout", "medium",
         "API Gateway integration timeout/config error.",
         "increase_timeout_or_fix_integration", 0.8, "apigw"),

    # Networking / VPC
    Rule("dns_or_network", re.compile(r"(NameResolutionFailure|ENETUNREACH|ECONNRESET|connection reset by peer|connection refused|i/o timeout)", re.I),
         "network_error", "medium",
         "Network/DNS connectivity problem.",
         "repair_networking_or_retries", 0.75, None),
]

SERVICE_HINTS = [
    ("lambda", re.compile(r"/aws/lambda/|REPORT RequestId|Init Duration", re.I)),
    ("apigw", re.compile(r"/aws/apigateway/|Method request|Integration request", re.I)),
    ("alb", re.compile(r"ELB-HealthChecker|http 5\d{2}|request_processing_time", re.I)),
    ("ecs", re.compile(r"/aws/ecs/|ecs", re.I)),
    ("eks", re.compile(r"kubelet|pod|container|CrashLoopBackOff|ImagePullBackOff|OOMKilled", re.I)),
    ("s3", re.compile(r"s3", re.I)),
    ("dynamodb", re.compile(r"dynamodb", re.I)),
    ("rds", re.compile(r"rds|mysql|postgres", re.I)),
]

def _infer_service_hint(source: str, message: str) -> Optional[str]:
    hay = f"{source} {message}".lower()
    for service, rx in SERVICE_HINTS:
        if rx.search(hay):
            return service
    return None

def _coerce_ts(ts_like: Any) -> Optional[float]:
    if ts_like is None:
        return None
    if isinstance(ts_like, (int, float)):
        if ts_like > 1e12 or ts_like > 1e10:
            return ts_like / 1000.0
        return float(ts_like)
    if isinstance(ts_like, str):
        try:
            return dt.datetime.fromisoformat(ts_like.replace("Z", "+00:00")).timestamp()
        except Exception:
            pass
        try:
            return float(ts_like)
        except Exception:
            return None
    return None

def _now() -> float:
    return time.time()

def parse_log_line(line: str) -> Tuple[Optional[float], str, Dict[str, Any]]:
    raw: Dict[str, Any] = {}
    msg: str = line.strip("\n")
    ts: Optional[float] = None
    if msg.startswith("{") and msg.endswith("}"):
        try:
            obj = json.loads(msg)
            raw = obj if isinstance(obj, dict) else {"_": obj}
            for key in ["timestamp", "ts", "time", "@timestamp", "eventTime"]:
                if key in raw:
                    ts = _coerce_ts(raw[key])
                    if ts:
                        break
            for key in ["message", "msg", "log", "@message"]:
                if key in raw and isinstance(raw[key], str):
                    msg = raw[key]
                    break
        except Exception:
            raw = {"raw": msg}
    if ts is None:
        ts = _now()
    return ts, msg, raw

class agent_a_reader:
    def __init__(self, rules: Optional[List[Rule]] = None):
        self.rules = rules or DEFAULT_RULES

    def process_file(self, path: str, source_name: Optional[str] = None) -> List[Finding]:
        findings: List[Finding] = []
        src = source_name or f"file:{path}"
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                ts, msg, raw = parse_log_line(line)
                rec = LogRecord(ts=ts, message=msg, source=src, service_hint=_infer_service_hint(src, msg), raw=raw)
                findings.extend(self._classify(rec))
        return findings

    def process_iterable(self, lines: Iterable[str], source_name: str = "iterable") -> List[Finding]:
        findings: List[Finding] = []
        for line in lines:
            ts, msg, raw = parse_log_line(line)
            rec = LogRecord(ts=ts, message=msg, source=source_name, service_hint=_infer_service_hint(source_name, msg), raw=raw)
            findings.extend(self._classify(rec))
        return findings

    def process_cloudwatch(self,
                           log_group: str,
                           start_time_ms: Optional[int] = None,
                           end_time_ms: Optional[int] = None,
                           filter_pattern: Optional[str] = None,
                           region: Optional[str] = None,
                           limit: int = 1000) -> List[Finding]:
        try:
            import boto3  # type: ignore
        except Exception as e:
            raise RuntimeError("boto3 is required for process_cloudwatch but is not installed or unavailable") from e

        client_args = {}
        if region:
            client_args["region_name"] = region
        logs = boto3.client("logs", **client_args)

        kwargs = {"logGroupName": log_group, "limit": min(limit, 10000)}
        if start_time_ms:
            kwargs["startTime"] = start_time_ms
        if end_time_ms:
            kwargs["endTime"] = end_time_ms
        if filter_pattern:
            kwargs["filterPattern"] = filter_pattern

        next_token = None
        findings: List[Finding] = []
        while True:
            if next_token:
                kwargs["nextToken"] = next_token
            resp = logs.filter_log_events(**kwargs)
            events = resp.get("events", [])
            for ev in events:
                msg = ev.get("message", "")
                ts = _coerce_ts(ev.get("timestamp"))
                raw = ev
                src = f"cloudwatch:{log_group}"
                rec = LogRecord(ts=ts or _now(), message=msg, source=src, service_hint=_infer_service_hint(src, msg), raw=raw)
                findings.extend(self._classify(rec))
            next_token = resp.get("nextToken")
            if not next_token:
                break
        return findings

    def _classify(self, rec: LogRecord) -> List[Finding]:
        matched: List[Finding] = []
        for rule in self.rules:
            if rule.pattern.search(rec.message):
                conf = rule.confidence
                if rule.service_bias and rec.service_hint == rule.service_bias:
                    conf = min(1.0, conf + 0.05)
                finding = Finding(
                    ts=rec.ts,
                    category=rule.category,
                    severity=rule.severity,
                    probable_cause=rule.probable_cause,
                    remediation_hint=rule.remediation_hint,
                    confidence=conf,
                    source=rec.source,
                    service=rec.service_hint or rule.service_bias,
                    message_excerpt=rec.message[:500],
                    meta={"rule": rule.name}
                )
                matched.append(finding)
        if not matched:
            matched.append(Finding(
                ts=rec.ts,
                category="runbook",
                severity="low",
                probable_cause="Unclassified log event.",
                remediation_hint="manual_triage",
                confidence=0.3,
                source=rec.source,
                service=rec.service_hint,
                message_excerpt=rec.message[:500],
                meta={"rule": "none"}
            ))
        return matched

    @staticmethod
    def dump_findings_jsonl(findings: List[Finding], path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            for fi in findings:
                f.write(json.dumps(fi.to_dict(), ensure_ascii=False) + "\\n")

    @staticmethod
    def to_agent_b_payload(findings: List[Finding]) -> Dict[str, Any]:
        return {
            "schema": "agent_a.v1",
            "summary_counts": _summarize(findings),
            "findings": [fi.to_dict() for fi in findings],
        }

def _summarize(findings: List[Finding]) -> Dict[str, Any]:
    counts: Dict[str, int] = {}
    severities: Dict[str, int] = {}
    for fi in findings:
        counts[fi.category] = counts.get(fi.category, 0) + 1
        severities[fi.severity] = severities.get(fi.severity, 0) + 1
    return {"by_category": counts, "by_severity": severities}

def categorize_log(log: str) -> str:
    reader = agent_a_reader()
    findings = reader.process_iterable([log], source_name="single_log")
    if findings:
        return findings[0].category
    return "runbook"
