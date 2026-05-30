#!/usr/bin/env bash
# Deploy the monthly FAA-data refresher: a Lambda that rebuilds airports_faa.json from
# FAA AIS and uploads it to S3, on a 28-day EventBridge schedule. The app Lambda reads
# that S3 object (planner/data.py), so data stays current with no app redeploy.
#
# Prereq: active SSO session (aws sso login). Idempotent — safe to re-run.
set -euo pipefail

REGION=us-west-2
KEY=airports_faa.json
FUNC=n9082p-data-refresh
ROLE=n9082p-data-refresh-role
RULE=n9082p-data-refresh-28d
RUNTIME=python3.13
HERE="$(cd "$(dirname "$0")/.." && pwd)"          # Flight-Planning-Tool/
BUILD="$HERE/build-refresh"
ZIP="$HERE/n9082p-data-refresh.zip"

aws sts get-caller-identity >/dev/null 2>&1 || { echo "AWS creds inactive. Run: aws sso login"; exit 1; }
ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
BUCKET="n9082p-planner-data-${ACCOUNT}"

echo "==> packaging refresher (refresh_handler + build_faa_airports; stdlib + boto3 runtime)"
rm -rf "$BUILD" "$ZIP"; mkdir -p "$BUILD"
cp "$HERE/refresh/refresh_handler.py" "$BUILD/"
cp "$HERE/tools/build_faa_airports.py" "$BUILD/"
( cd "$BUILD" && zip -qr "$ZIP" . )

echo "==> execution role (basic logs + S3 PutObject on the data bucket)"
if ! aws iam get-role --role-name "$ROLE" >/dev/null 2>&1; then
  aws iam create-role --role-name "$ROLE" \
    --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}' >/dev/null
  aws iam attach-role-policy --role-name "$ROLE" \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
  echo "    created $ROLE; waiting for IAM propagation..."; sleep 12
fi
aws iam put-role-policy --role-name "$ROLE" --policy-name s3-write \
  --policy-document "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"s3:PutObject\"],\"Resource\":\"arn:aws:s3:::${BUCKET}/*\"}]}" >/dev/null
ROLE_ARN="arn:aws:iam::${ACCOUNT}:role/${ROLE}"

echo "==> function (5 min timeout for the FAA AIS pull)"
if aws lambda get-function --function-name "$FUNC" --region "$REGION" >/dev/null 2>&1; then
  aws lambda update-function-code --function-name "$FUNC" --zip-file "fileb://$ZIP" --region "$REGION" >/dev/null
  aws lambda wait function-updated --function-name "$FUNC" --region "$REGION"
  aws lambda update-function-configuration --function-name "$FUNC" --region "$REGION" \
    --runtime "$RUNTIME" --handler refresh_handler.lambda_handler --timeout 300 --memory-size 512 \
    --environment "Variables={DATA_BUCKET=$BUCKET,DATA_KEY=$KEY}" >/dev/null
  aws lambda wait function-updated --function-name "$FUNC" --region "$REGION"
else
  aws lambda create-function --function-name "$FUNC" --region "$REGION" \
    --runtime "$RUNTIME" --handler refresh_handler.lambda_handler --role "$ROLE_ARN" \
    --zip-file "fileb://$ZIP" --timeout 300 --memory-size 512 \
    --environment "Variables={DATA_BUCKET=$BUCKET,DATA_KEY=$KEY}" >/dev/null
  aws lambda wait function-active --function-name "$FUNC" --region "$REGION"
fi

echo "==> 28-day EventBridge schedule"
aws events put-rule --name "$RULE" --region "$REGION" \
  --schedule-expression "rate(28 days)" --description "Rebuild N9082P FAA airport data (FAA 28-day cycle)" >/dev/null
FN_ARN="arn:aws:lambda:${REGION}:${ACCOUNT}:function:${FUNC}"
RULE_ARN="arn:aws:events:${REGION}:${ACCOUNT}:rule/${RULE}"
aws lambda add-permission --function-name "$FUNC" --region "$REGION" \
  --statement-id events-invoke --action lambda:InvokeFunction \
  --principal events.amazonaws.com --source-arn "$RULE_ARN" >/dev/null 2>&1 || true
aws events put-targets --rule "$RULE" --region "$REGION" --targets "Id=1,Arn=$FN_ARN" >/dev/null

echo "✅ refresher deployed: $FUNC runs rate(28 days) -> s3://$BUCKET/$KEY"
echo "   test now with: aws lambda invoke --function-name $FUNC --region $REGION /tmp/refresh.json && cat /tmp/refresh.json"
