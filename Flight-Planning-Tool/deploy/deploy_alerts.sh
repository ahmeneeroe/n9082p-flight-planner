#!/usr/bin/env bash
# Email alerting for the FAA-data refresher: SNS topic + email subscription + two
# CloudWatch alarms on the refresher Lambda. Idempotent.
#   - <FUNC>-errors      : the refresher ran and errored/timed out
#   - <FUNC>-not-running : no invocation in ~33 days (schedule broken / disabled)
# Prereq: active SSO session. Usage: bash deploy/deploy_alerts.sh [email]
set -euo pipefail

REGION=us-west-2
TOPIC=n9082p-alerts
FUNC=n9082p-data-refresh
EMAIL="${1:-David.ameneyro@gmail.com}"

aws sts get-caller-identity >/dev/null 2>&1 || { echo "AWS creds inactive. Run: aws sso login"; exit 1; }

TOPIC_ARN="$(aws sns create-topic --name "$TOPIC" --region "$REGION" --query TopicArn --output text)"
echo "topic: $TOPIC_ARN"

# subscribe the email only if not already present (avoids duplicate pending subs)
EXISTING="$(aws sns list-subscriptions-by-topic --topic-arn "$TOPIC_ARN" --region "$REGION" \
  --query "Subscriptions[?Endpoint=='$EMAIL'].SubscriptionArn" --output text)"
if [ -z "$EXISTING" ]; then
  aws sns subscribe --topic-arn "$TOPIC_ARN" --protocol email --notification-endpoint "$EMAIL" --region "$REGION" >/dev/null
  echo "subscription requested for $EMAIL — confirm via the email AWS sends"
else
  echo "subscription already present for $EMAIL ($EXISTING)"
fi

aws cloudwatch put-metric-alarm --region "$REGION" --alarm-name "${FUNC}-errors" \
  --alarm-description "FAA data refresher ($FUNC) errored or timed out" \
  --namespace AWS/Lambda --metric-name Errors --dimensions "Name=FunctionName,Value=${FUNC}" \
  --statistic Sum --period 86400 --evaluation-periods 1 --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold --treat-missing-data notBreaching \
  --alarm-actions "$TOPIC_ARN"

# NOTE: an active "hasn't run in ~33 days" alarm isn't possible with a standard CloudWatch
# metric alarm — for periods >= 1h, EvaluationPeriods*Period must be <= 1 week, so a 28-day
# window can't be expressed (and a 7-day one would false-alarm on the 28-day schedule).
# Staleness is surfaced passively instead by the "Airport data: <date>" stamp on every safety
# sheet. (A daily S3-object-age checker Lambda could add active staleness alerting if wanted.)

echo "✅ alerts configured -> $EMAIL (confirm the SNS subscription email to start receiving them)"
