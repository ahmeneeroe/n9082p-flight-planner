#!/usr/bin/env bash
# Deploy the N9082P planner to AWS Lambda + Function URL (us-west-2).
# Idempotent: safe to re-run to push code/data updates.
#
# Prereqs: AWS CLI v2 with an active SSO session (run `aws sso login` first).
# Usage:   bash deploy/deploy.sh [password]      (prompts if omitted)
set -euo pipefail

REGION="us-west-2"
FUNC="n9082p-planner"
ROLE="n9082p-planner-role"
RUNTIME="python3.13"            # fall back to python3.12 if unavailable in your account
HERE="$(cd "$(dirname "$0")/.." && pwd)"
ZIP="$HERE/n9082p-planner.zip"

PASSWORD="${1:-${PLANNER_PASSWORD:-}}"
if [ -z "$PASSWORD" ]; then
  read -rsp "Set Basic Auth password for the planner: " PASSWORD; echo
fi
[ -z "$PASSWORD" ] && { echo "No password given. Aborting."; exit 1; }

# Confirm SSO session is live early with a clear message.
if ! aws sts get-caller-identity --region "$REGION" >/dev/null 2>&1; then
  echo "AWS credentials not active. Run:  aws sso login   then retry."; exit 1
fi
ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
ROLE_ARN="arn:aws:iam::${ACCOUNT}:role/${ROLE}"

echo "==> building zip"
bash "$HERE/deploy/build.sh"

echo "==> ensuring execution role"
if ! aws iam get-role --role-name "$ROLE" >/dev/null 2>&1; then
  aws iam create-role --role-name "$ROLE" \
    --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}' >/dev/null
  aws iam attach-role-policy --role-name "$ROLE" \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
  echo "    created $ROLE; waiting for IAM propagation..."; sleep 12
fi
# allow the app to read the live (monthly-refreshed) data bundle from S3
aws iam put-role-policy --role-name "$ROLE" --policy-name data-bucket-read \
  --policy-document "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"s3:GetObject\"],\"Resource\":\"arn:aws:s3:::n9082p-planner-data-${ACCOUNT}/*\"}]}" >/dev/null

echo "==> deploying function"
if aws lambda get-function --function-name "$FUNC" --region "$REGION" >/dev/null 2>&1; then
  aws lambda update-function-code --function-name "$FUNC" --zip-file "fileb://$ZIP" --region "$REGION" >/dev/null
  aws lambda wait function-updated --function-name "$FUNC" --region "$REGION"
  aws lambda update-function-configuration --function-name "$FUNC" --region "$REGION" \
    --runtime "$RUNTIME" --handler handler.lambda_handler --timeout 30 --memory-size 512 \
    --environment "Variables={PLANNER_PASSWORD=$PASSWORD,DATA_BUCKET=n9082p-planner-data-${ACCOUNT},DATA_KEY=airports_faa.json}" >/dev/null
  aws lambda wait function-updated --function-name "$FUNC" --region "$REGION"
else
  aws lambda create-function --function-name "$FUNC" --region "$REGION" \
    --runtime "$RUNTIME" --handler handler.lambda_handler --role "$ROLE_ARN" \
    --zip-file "fileb://$ZIP" --timeout 30 --memory-size 512 \
    --environment "Variables={PLANNER_PASSWORD=$PASSWORD,DATA_BUCKET=n9082p-planner-data-${ACCOUNT},DATA_KEY=airports_faa.json}" >/dev/null
  aws lambda wait function-active --function-name "$FUNC" --region "$REGION"
fi

echo "==> ensuring public Function URL + invoke permissions (Basic Auth gates access in-app)"
aws lambda get-function-url-config --function-name "$FUNC" --region "$REGION" >/dev/null 2>&1 \
  || aws lambda create-function-url-config --function-name "$FUNC" --region "$REGION" --auth-type NONE >/dev/null
# Public (NONE) function URLs require BOTH permissions since Oct 2025, each added as a
# separate statement, or invocations 403. Idempotent: ignore if a statement already exists.
aws lambda add-permission --function-name "$FUNC" --region "$REGION" \
  --statement-id FunctionURLAllowPublicAccess --action lambda:InvokeFunctionUrl \
  --principal '*' --function-url-auth-type NONE >/dev/null 2>&1 || true
aws lambda add-permission --function-name "$FUNC" --region "$REGION" \
  --statement-id FunctionURLInvokeFunction --action lambda:InvokeFunction \
  --principal '*' --invoked-via-function-url >/dev/null 2>&1 || true

URL="$(aws lambda get-function-url-config --function-name "$FUNC" --region "$REGION" --query FunctionUrl --output text)"
echo ""
echo "✅ Deployed.  Open on your phone:"
echo "   $URL"
echo "   Log in with ANY username + the password you set. Add to Home Screen for app-like access."
