package argus.aml

import rego.v1

# Rule Bundle Version
version := "1.0.0"

# 1. Structuring Window: Deposits just under INR 50,000 threshold within 24h
structuring_hit if {
    input.amount >= 45000.0
    input.amount < 50000.0
    input.structuring_window_count_24h >= 3
}

# 2. Velocity Burst: Abnormal frequency
velocity_hit if {
    input.velocity_count_1h >= 5
}

velocity_hit if {
    input.velocity_count_24h >= 15
}

# 3. Rapid Pass-Through (Mule Ring)
rapid_pass_through_hit if {
    input.mule_inflow_amount >= 200000.0
    input.mule_outflow_delta_minutes <= 15
}

# 4. Round Amount Smurfing
round_amount_hit if {
    input.amount >= 10000.0
    rem := input.amount - (floor(input.amount / 10000.0) * 10000.0)
    rem == 0.0
    input.repeated_round_count >= 3
}

# 5. Dormant Account Spike
dormant_spike_hit if {
    input.days_since_last_activity >= 180
    input.amount >= 50000.0
}
