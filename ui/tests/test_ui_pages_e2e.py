"""
ARGUS End-to-End Automated UI Test Suite
Uses streamlit.testing.v1.AppTest to execute, simulate user interactions,
and verify state, widgets, calculations, and error-free rendering on every page.
"""
from pathlib import Path
from datetime import date
import pytest
from streamlit.testing.v1 import AppTest

UI_DIR = Path(__file__).resolve().parent.parent


class TestArgusUIAutomated:
    """Automated UI verification test suite for all ARGUS multi-page views."""

    def test_global_shell_dashboard(self):
        """Verify ui/app.py loads cleanly, renders navigation, KPIs, and overview."""
        at = AppTest.from_file(str(UI_DIR / "app.py")).run(timeout=15)
        assert not at.exception, f"App.py had unexpected exceptions: {at.exception}"
        # Markdown cards and banners must be present
        assert len(at.markdown) > 10

    def test_analyst_console_page(self):
        """Verify Analyst Console renders cases, queue tabs, and case controls."""
        at = AppTest.from_file(str(UI_DIR / "pages" / "1_analyst_console.py")).run(timeout=20)
        assert not at.exception, f"Page 1 had unexpected exceptions: {at.exception}"
        # Verify selectbox for case selection exists
        assert len(at.selectbox) >= 1
        # Check tabs exist
        assert len(at.tabs) >= 3

    def test_compliance_copilot_page(self):
        """Verify Compliance Copilot renders search, suggested questions, and executes query."""
        at = AppTest.from_file(str(UI_DIR / "pages" / "2_compliance_copilot.py")).run(timeout=20)
        assert not at.exception, f"Page 2 had unexpected exceptions: {at.exception}"
        # Set a query in the text input and rerun
        if at.text_input:
            at.text_input[0].input("UPI fraud transaction monitoring threshold").run(timeout=15)
            assert not at.exception

    def test_rule_studio_page(self):
        """Verify Rule Studio renders rules, tabs, simulator controls."""
        at = AppTest.from_file(str(UI_DIR / "pages" / "3_rule_studio.py")).run(timeout=20)
        assert not at.exception, f"Page 3 had unexpected exceptions: {at.exception}"
        assert len(at.tabs) >= 3

    def test_audit_explorer_page(self):
        """Verify Audit Explorer renders Merkle ledger, verification banner, and logs."""
        at = AppTest.from_file(str(UI_DIR / "pages" / "4_audit_explorer.py")).run(timeout=20)
        assert not at.exception, f"Page 4 had unexpected exceptions: {at.exception}"
        # Ensure buttons (e.g. Verify Chain) exist
        assert len(at.button) >= 1

    def test_cost_telemetry_page(self):
        """Verify Cost & Telemetry dashboard renders without errors."""
        at = AppTest.from_file(str(UI_DIR / "pages" / "5_cost_telemetry.py")).run(timeout=20)
        assert not at.exception, f"Page 5 had unexpected exceptions: {at.exception}"
