package argus.fraud

version := "1.0.0"

# 1. Device Hopping: More than 3 distinct devices within 24 hours
device_hopping_hit if {
    input.distinct_devices_24h > 3
}

# 2. Off-Hours High Value: Between 01:00 and 05:00 UTC with amount > INR 100,000
off_hours_hit if {
    input.hour_of_day >= 1
    input.hour_of_day <= 5
    input.amount > 100000.0
}

# 3. Impossible Geo-Velocity: Distance > 1000km in under 1 hour
impossible_geo_hit if {
    input.geo_distance_km > 1000.0
    input.geo_time_delta_minutes < 60
}
