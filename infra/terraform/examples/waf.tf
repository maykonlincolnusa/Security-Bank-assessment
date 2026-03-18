resource "aws_wafv2_web_acl" "this" {
  name  = "trust-score-waf"
  scope = "REGIONAL"

  default_action {
    allow {}
  }

  rule {
    name     = "aws-common-rules"
    priority = 1
    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
      }
    }
    override_action {
      none {}
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "aws_common_rules"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "rate-limit-ip"
    priority = 2
    action {
      block {}
    }
    statement {
      rate_based_statement {
        aggregate_key_type = "IP"
        limit              = 2000
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "rate_limit_ip"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "trust_score_waf"
    sampled_requests_enabled   = true
  }
}
