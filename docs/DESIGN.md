# Design Notes

This hackathon skeleton uses rule-based agents to ensure quick local demos without external services.

## Agents
- A (Reader): extracts fields & chooses category via keyword patterns.
- B (Remediator): maps category → recommendations (+ rationale, risk).
- C (Codegen): emits minimal Terraform or AWS CLI for the chosen action.

## Orchestration
A → B → C via a simple Python function; you can replace with an agent framework later.

## Safety
- No destructive actions are generated.
- Always review & test in non-prod first.
