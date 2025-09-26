from backend.core.orchestrator import analyze_log

def test_dynamodb_throttling():
    text = "WARN ThrottlingException on DynamoDB PutItem Rate exceeded"
    out = analyze_log(text)
    assert out["signal"]["category"] in ("THROTTLING", "CONFIG")
    assert "code" in out and "terraform" in out["code"]
