package argus.main

import rego.v1

import data.argus.aml
import data.argus.fraud
import data.argus.kyc
import data.argus.privacy

bundle_version := "1.0.0"

# Collect all triggered evidence IDs
evidence contains "aml_structuring_window" if aml.structuring_hit
evidence contains "velocity_burst" if aml.velocity_hit
evidence contains "rapid_pass_through" if aml.rapid_pass_through_hit
evidence contains "round_amount_smurfing" if aml.round_amount_hit
evidence contains "dormant_account_spike" if aml.dormant_spike_hit

evidence contains "device_hopping" if fraud.device_hopping_hit
evidence contains "off_hours_high_value" if fraud.off_hours_hit
evidence contains "geo_velocity_impossible" if fraud.impossible_geo_hit

evidence contains "sanctions_exact_match" if kyc.sanctions_hit
evidence contains "high_risk_jurisdiction" if kyc.high_risk_jurisdiction_hit
evidence contains "kyc_validity_expired" if kyc.kyc_expired_hit

evidence contains "privacy_unauthorized_pii_query" if privacy.unauthorized_pii_hit

# Determine Highest-Priority Outcome and Tier
default outcome := "ALLOW"
default tier := "T0"

# T3 Blocks (Sanctions, Hostile Jurisdictions)
outcome := "BLOCK" if {
    "sanctions_exact_match" in evidence
} else := "BLOCK" if {
    "high_risk_jurisdiction" in evidence
} else := "BLOCK" if {
    "geo_velocity_impossible" in evidence
} else := "BLOCK" if {
    "privacy_unauthorized_pii_query" in evidence
} else := "HOLD" if {
    count(evidence) > 0
}

tier := "T3" if {
    "sanctions_exact_match" in evidence
} else := "T3" if {
    "high_risk_jurisdiction" in evidence
} else := "T2" if {
    "rapid_pass_through" in evidence
} else := "T2" if {
    "geo_velocity_impossible" in evidence
} else := "T2" if {
    "privacy_unauthorized_pii_query" in evidence
} else := "T1" if {
    count(evidence) > 0
}

# Unified decision payload
decision := {
    "outcome": outcome,
    "tier": tier,
    "evidence_ids": [x | some x in evidence],
    "bundle_version": bundle_version
}
