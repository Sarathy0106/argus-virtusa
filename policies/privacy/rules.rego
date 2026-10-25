package argus.privacy

version := "1.0.0"

# 1. Unauthorized raw PII query attempt
unauthorized_pii_hit if {
    input.contains_raw_pii == true
    not input.has_valid_vault_scope
}
