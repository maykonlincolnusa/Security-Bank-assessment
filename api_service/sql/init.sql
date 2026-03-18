CREATE SCHEMA IF NOT EXISTS curated;

CREATE TABLE IF NOT EXISTS curated.trust_features (
  institution_id VARCHAR(128) PRIMARY KEY,
  features JSONB NOT NULL,
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

INSERT INTO curated.trust_features (institution_id, features)
VALUES
  ('001', '{"capital_ratio": 0.14, "liquidity_ratio": 1.3, "roe": 0.11, "npl_ratio": 0.03, "deposit_volatility": 0.12, "avg_sentiment": 0.2, "negative_volume": 5, "security_incidents": 1}'::jsonb),
  ('033', '{"capital_ratio": 0.12, "liquidity_ratio": 1.1, "roe": 0.09, "npl_ratio": 0.04, "deposit_volatility": 0.15, "avg_sentiment": -0.1, "negative_volume": 8, "security_incidents": 2}'::jsonb)
ON CONFLICT (institution_id) DO NOTHING;
