# Agent C: IaC / CLI code generator (rule-based demo)
from typing import Dict, Any

def generate(signal: Dict[str, Any], chosen_action: str = None) -> Dict[str, str]:
    # Produces minimal Terraform or AWS CLI based on the recommended action.
    # NEVER produces destructive code. Review before applying.
    cat = signal.get("category", "CONFIG")
    if not chosen_action:
        chosen_action = _default_action(cat)

    if chosen_action == "IAM_POLICY_UPDATE":
        tf = _tf_s3_getobject_policy()
        cli = _cli_put_bucket_policy_comment()
    elif chosen_action == "RESOURCE_POLICY_UPDATE":
        tf = _tf_kms_key_policy_skeleton()
        cli = "# Update your resource policy accordingly"
    elif chosen_action in ("CAPACITY_SCALE", "SCALING_POLICY_TUNE"):
        tf = _tf_asg_desired_capacity()
        cli = "aws autoscaling set-desired-capacity --auto-scaling-group-name <asg-name> --desired-capacity 4"
    elif chosen_action == "RETRY_POLICY":
        tf = "# Retry policy is an app-level change; show snippet for exponential backoff"
        cli = "# N/A (apply in application code)"
    elif chosen_action == "TIMEOUT_TUNE":
        tf = _tf_lambda_timeout_memory()
        cli = "aws lambda update-function-configuration --function-name <name> --timeout 30 --memory-size 1024"
    elif chosen_action == "QUOTA_INCREASE":
        tf = "# Use aws_servicequotas_* (Terraform) if supported for your quota"
        cli = "aws service-quotas request-service-quota-increase --service-code <svc> --quota-code <code> --desired-value <n>"
    else:
        tf = _tf_example_config_fix()
        cli = "# Validate resource exists in correct region; adjust ARNs/IDs"
    return {"terraform": tf, "cli": cli}

def _default_action(cat: str) -> str:
    return {
        "IAM": "IAM_POLICY_UPDATE",
        "THROTTLING": "CAPACITY_SCALE",
        "TIMEOUT": "TIMEOUT_TUNE",
        "QUOTA": "QUOTA_INCREASE",
        "SCALING": "CAPACITY_SCALE",
        "CONFIG": "CONFIG_FIX",
    }.get(cat, "CONFIG_FIX")

def _tf_s3_getobject_policy() -> str:
    return '''# Minimal S3 bucket policy allowing GetObject to a specific principal (e.g., CloudFront OAC)
resource "aws_s3_bucket_policy" "allow_getobject" {
  bucket = var.bucket_name
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Sid    = "AllowGetObjectFromOAC",
      Effect = "Allow",
      Principal = { AWS = var.oac_principal_arn },
      Action = ["s3:GetObject"],
      Resource = "arn:aws:s3:::${var.bucket_name}/*"
    }]
  })
}
# Variables: bucket_name, oac_principal_arn
'''

def _tf_kms_key_policy_skeleton() -> str:
    return '''# KMS key policy skeleton - ensure your role is allowed to decrypt
data "aws_caller_identity" "current" {}

resource "aws_kms_key" "example" {
  description             = "Example key"
  deletion_window_in_days = 30
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Sid: "AllowAccountUseOfKey",
      Effect: "Allow",
      Principal: { AWS: data.aws_caller_identity.current.account_id },
      Action: ["kms:Decrypt","kms:Encrypt","kms:GenerateDataKey*"],
      Resource: "*"
    }]
  })
}
'''

def _tf_asg_desired_capacity() -> str:
    return '''# Increase ASG desired capacity (example)
resource "aws_autoscaling_group" "app" {
  name              = var.asg_name
  min_size          = 2
  max_size          = 8
  desired_capacity  = 4
  launch_template {
    id      = var.lt_id
    version = "$Latest"
  }
}
# Variables: asg_name, lt_id
'''

def _tf_lambda_timeout_memory() -> str:
    return '''# Tune Lambda timeout and memory
resource "aws_lambda_function" "fn" {
  function_name = var.fn_name
  role          = var.fn_role_arn
  handler       = "app.handler"
  runtime       = "python3.11"
  timeout       = 30
  memory_size   = 1024
  filename      = "build.zip"
}
# Variables: fn_name, fn_role_arn
'''

def _tf_example_config_fix() -> str:
    return '''# Placeholder config fix - ensures correct region/provider and tags
provider "aws" {
  region = var.region
}

variable "region" {
  type = string
  default = "us-east-1"
}
'''

def _cli_put_bucket_policy_comment() -> str:
    return "# Use aws s3api put-bucket-policy with a JSON doc matching the Terraform above."
