package argus.kyc

import rego.v1

version := "1.0.0"

# High-risk sanctioned countries (ISO-3)
sanctioned_countries := {"PRK", "IRN", "SYR", "CUB", "RUS"}

# 1. Sanctions Hit (Counterparty or customer exact hit)
sanctions_hit if {
    input.sanctions_match == true
}

# 2. High-Risk Jurisdiction Corridor
high_risk_jurisdiction_hit if {
    sanctioned_countries[input.location_country]
}

# 3. KYC Validity Expired
kyc_expired_hit if {
    input.kyc_status == "EXPIRED"
}

kyc_expired_hit if {
    input.days_since_kyc_verification > 365
}
