"""Tests for swarmmind.services.risk_policy."""

from swarmmind.services.risk_policy import CAPABILITY_RISK, RiskTier, classify


class TestClassify:
    def test_known_high_risk(self):
        assert classify("shell") == RiskTier.HIGH
        assert classify("bash") == RiskTier.HIGH
        assert classify("tools.shell") == RiskTier.HIGH
        assert classify("delete_file") == RiskTier.HIGH
        assert classify("http_delete") == RiskTier.HIGH

    def test_known_medium_risk(self):
        assert classify("write_file") == RiskTier.MEDIUM
        assert classify("http_post") == RiskTier.MEDIUM
        assert classify("tools.write_file") == RiskTier.MEDIUM

    def test_known_low_risk(self):
        assert classify("http_get") == RiskTier.LOW
        assert classify("read_file") == RiskTier.LOW
        assert classify("web_search") == RiskTier.LOW
        assert classify("search") == RiskTier.LOW

    def test_unknown_capability_defaults_to_low(self):
        assert classify("some_random_tool") == RiskTier.LOW
        assert classify("") == RiskTier.LOW
        assert classify("ask_clarification") == RiskTier.LOW

    def test_case_normalisation(self):
        # Uppercased version should still match via normalisation
        assert classify("SHELL") == RiskTier.HIGH
        assert classify("WRITE_FILE") == RiskTier.MEDIUM

    def test_all_table_keys_resolve(self):
        for key, expected in CAPABILITY_RISK.items():
            assert classify(key) == expected, f"classify({key!r}) should be {expected}"


class TestRiskTier:
    def test_enum_values(self):
        assert RiskTier.LOW.value == "low"
        assert RiskTier.MEDIUM.value == "medium"
        assert RiskTier.HIGH.value == "high"

    def test_string_comparison(self):
        assert RiskTier.HIGH == "high"
        assert RiskTier.LOW == "low"
