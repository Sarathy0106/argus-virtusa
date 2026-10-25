package argus.main

import data.argus.aml
import data.argus.fraud
import data.argus.kyc
import data.argus.privacy

bundle_version := "1.0.0"

# Collect all triggered evidence IDs
evidence[id] if {
    aml.structuring_hit
    id := "aml_structuring_window"
}

evidence[id] if {
    aml.velocity_hit
    id := "velocity_burst"
}

evidence[id] if {
    aml.rapid_pass_through_hit
    id := "rapid_pass_through"
}

evidence[id] if {
    aml.round_amount_hit
    id := "round_amount_smurfing"
}

evidence[id] if {
    aml.dormant_spike_hit
    id := "dormant_account_spike"
}

evidence[id] if {
    fraud.device_hopping_hit
    id := "device_hopping"
}

evidence[id] if {
    fraud.off_hours_hit
    id := "off_hours_high_value"
}

evidence[id] if {
    fraud.impossible_geo_hit
    id := "geo_velocity_impossible"
}

evidence[id] if {
    kyc.sanctions_hit
    id := "sanctions_exact_match"
}

evidence[id] if {
    kyc.high_risk_jurisdiction_hit
    id := "high_risk_jurisdiction"
}

evidence[id] if {
    kyc.kyc_expired_hit
    id := "kyc_validity_expired"
}

evidence[id] if {
    privacy.unauthorized_pii_hit
    id := "privacy_unauthorized_pii_query"
}

# Determine Highest-Priority Outcome and Tier
default outcome := "ALLOW"
default tier := "T0"

# T3 Blocks (Sanctions, Hostile Jurisdictions)
outcome := "BLOCK" if {
    evidence["sanctions_exact_match"]
} else := "BLOCK" if {
    evidence["high_risk_jurisdiction"]
} else := "BLOCK" if {
    evidence["geo_velocity_impossible"]
} else := "BLOCK" if {
    evidence["privacy_unauthorized_pii_query"]
} else := "HOLD" if {
    count(evidence) > 0
}

tier := "T3" if {
    evidence["sanctions_exact_match"]
} else := "T3" if {
    evidence["high_risk_jurisdiction"]
} else := "T2" if {
    evidence["rapid_pass_through"]
} else := "T2" if {
    evidence["geo_velocity_impossible"]
} else := "T2" if {
    evidence["privacy_unauthorized_pii_query"]
} else := "T1" if {
    count(evidence) > 0
}

# Unified decision payload
decision := {
    "outcome": outcome,
    "tier": tier,
    "evidence_ids": [id | evidence[id]],
    "bundle_version": bundle_version
}
