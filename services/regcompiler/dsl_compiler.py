"""
Rule DSL Compiler and Rego Code Generator for ARGUS v2.
Parses declarative YAML Rule DSL specifications, verifies schema integrity,
compiles conditions to bit-for-bit deterministic Rego code, synthesizes
Rego test suites, and constructs the end-to-end Traceability Graph.
"""

from typing import Any
import yaml

from contracts.rule_dsl import DSLAction, DSLCondition, DSLOperator, DSLTestCase, RuleDefinition


class DSLCompilationError(Exception):
    pass


class RuleDSLCompiler:
    def __init__(self):
        pass

    def parse_yaml(self, yaml_content: str) -> RuleDefinition:
        """Parses and validates a raw YAML Rule DSL string into a RuleDefinition model."""
        try:
            raw = yaml.safe_load(yaml_content)
            if not isinstance(raw, dict):
                raise DSLCompilationError("Rule DSL must be a YAML mapping/dictionary.")
            return RuleDefinition(**raw)
        except Exception as e:
            raise DSLCompilationError(f"Failed to parse Rule DSL YAML: {str(e)}") from e

    def compile_condition_to_rego(self, cond: DSLCondition) -> str:
        """Translates a single DSLCondition into an OPA Rego expression."""
        field = cond.field
        op = cond.operator
        val = cond.value

        if op == DSLOperator.GTE:
            return f"{field} >= {val}"
        elif op == DSLOperator.LTE:
            return f"{field} <= {val}"
        elif op == DSLOperator.EQ:
            if isinstance(val, str):
                return f'{field} == "{val}"'
            return f"{field} == {val}"
        elif op == DSLOperator.NEQ:
            if isinstance(val, str):
                return f'{field} != "{val}"'
            return f"{field} != {val}"
        elif op == DSLOperator.IN:
            if isinstance(val, list):
                val_repr = "[" + ", ".join(f'"{v}"' if isinstance(v, str) else str(v) for v in val) + "]"
                return f"{val_repr}[_] == {field}"
            return f"{field} == {val}"
        elif op == DSLOperator.NOT_IN:
            if isinstance(val, list):
                val_repr = "[" + ", ".join(f'"{v}"' if isinstance(v, str) else str(v) for v in val) + "]"
                return f"not {val_repr}[_] == {field}"
            return f"{field} != {val}"
        else:
            return f"{field} == {val}"

    def compile_to_rego(self, rule_def: RuleDefinition) -> str:
        """Generates valid Open Policy Agent (OPA) Rego policy code from a RuleDefinition."""
        lines = [
            f"package {rule_def.package_path}.{rule_def.rule_name}",
            "",
            f"# Auto-compiled by ARGUS v2 Rule DSL Compiler",
            f"# Source Obligation: {rule_def.obligation_id}",
            f"# Source Clause: {rule_def.clause_id}",
            f'# Traceability Citations: {", ".join(rule_def.citations)}',
            f'version := "{rule_def.version}"',
            "",
            "default rule_hit := false",
            "",
            "rule_hit if {",
        ]

        for cond in rule_def.conditions:
            expr = self.compile_condition_to_rego(cond)
            lines.append(f"    {expr}")

        lines.extend([
            "}",
            "",
            "decision := {",
            f'    "outcome": "{rule_def.action.outcome}",',
            f'    "tier": "{rule_def.action.tier}",',
            f'    "evidence_id": "{rule_def.action.evidence_id}",',
        ])
        if rule_def.action.cooling_period_hours is not None:
            lines.append(f'    "cooling_period_hours": {rule_def.action.cooling_period_hours},')
        lines.extend([
            f'    "clause_id": "{rule_def.clause_id}",',
            f'    "rule_name": "{rule_def.rule_name}"',
            "}",
            "",
        ])

        return "\n".join(lines)

    def compile_tests_to_rego(self, rule_def: RuleDefinition) -> str:
        """Generates Rego unit tests for the rule."""
        import json

        pkg = f"{rule_def.package_path}.{rule_def.rule_name}"
        lines = [
            f"package {pkg}_test",
            "",
            f"import data.{pkg}",
            "",
        ]

        for test in rule_def.test_cases:
            test_slug = test.test_id.lower().replace("-", "_")
            input_json = json.dumps(test.input_data)
            if test.expected_hit:
                lines.append(f"test_{test_slug}_hit if {{")
                lines.append(f"    rule_hit with input as {input_json}")
                lines.append("}")
            else:
                lines.append(f"test_{test_slug}_miss if {{")
                lines.append(f"    not rule_hit with input as {input_json}")
                lines.append("}")
            lines.append("")

        return "\n".join(lines)

    def evaluate_locally(self, rule_def: RuleDefinition, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Deterministic local evaluation of RuleDefinition against an input dictionary.
        Mirrors OPA Rego evaluation logic.
        """
        all_match = True
        for cond in rule_def.conditions:
            # Resolve dotted field like "input.amount" or "amount"
            field_path = cond.field
            if field_path.startswith("input."):
                field_key = field_path[6:]
            else:
                field_key = field_path

            actual_val = input_data.get(field_key)
            if actual_val is None:
                all_match = False
                break

            op = cond.operator
            target_val = cond.value

            if op == DSLOperator.GTE and not (actual_val >= target_val):
                all_match = False
                break
            elif op == DSLOperator.LTE and not (actual_val <= target_val):
                all_match = False
                break
            elif op == DSLOperator.EQ and not (actual_val == target_val):
                all_match = False
                break
            elif op == DSLOperator.NEQ and not (actual_val != target_val):
                all_match = False
                break
            elif op == DSLOperator.IN and not (actual_val in target_val):
                all_match = False
                break
            elif op == DSLOperator.NOT_IN and not (actual_val not in target_val):
                all_match = False
                break

        if all_match:
            return {
                "rule_hit": True,
                "outcome": rule_def.action.outcome,
                "tier": rule_def.action.tier,
                "evidence_id": rule_def.action.evidence_id,
                "cooling_period_hours": rule_def.action.cooling_period_hours,
            }
        return {"rule_hit": False, "outcome": "ALLOW", "tier": "T0"}

    def run_synthetic_tests(self, rule_def: RuleDefinition) -> tuple[int, int, list[str]]:
        """
        Runs all synthetic unit tests specified in rule_def.
        Returns: (passed_count, total_count, failure_reasons)
        """
        total = len(rule_def.test_cases)
        passed = 0
        failures = []

        for test in rule_def.test_cases:
            res = self.evaluate_locally(rule_def, test.input_data)
            hit = res["rule_hit"]
            if hit == test.expected_hit:
                passed += 1
            else:
                failures.append(
                    f"Test {test.test_id} failed: expected hit={test.expected_hit}, got hit={hit} (input: {test.input_data})"
                )

        return passed, total, failures

    def build_traceability_graph(self, rule_def: RuleDefinition) -> dict[str, Any]:
        """
        Constructs the end-to-end Traceability Graph:
        Clause -> Obligation -> Internal Policy -> Rule DSL -> Rego -> Test Cases.
        """
        nodes = [
            {"id": rule_def.clause_id, "type": "CLAUSE", "label": f"Clause: {rule_def.clause_id}"},
            {"id": rule_def.obligation_id, "type": "OBLIGATION", "label": f"Obligation: {rule_def.obligation_id}"},
        ]
        if rule_def.policy_id:
            nodes.append({"id": rule_def.policy_id, "type": "POLICY", "label": f"Policy: {rule_def.policy_id}"})
        nodes.append({"id": rule_def.rule_name, "type": "RULE", "label": f"Rule: {rule_def.rule_name}"})

        edges = [
            {"from": rule_def.clause_id, "to": rule_def.obligation_id, "relation": "extracts"},
        ]
        if rule_def.policy_id:
            edges.append({"from": rule_def.obligation_id, "to": rule_def.policy_id, "relation": "maps_to"})
            edges.append({"from": rule_def.policy_id, "to": rule_def.rule_name, "relation": "implements"})
        else:
            edges.append({"from": rule_def.obligation_id, "to": rule_def.rule_name, "relation": "implements"})

        for t in rule_def.test_cases:
            nodes.append({"id": t.test_id, "type": "TEST", "label": f"Test: {t.test_id}"})
            edges.append({"from": rule_def.rule_name, "to": t.test_id, "relation": "verifies"})

        return {"nodes": nodes, "edges": edges}
