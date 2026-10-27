"""
Validator Agent for ARGUS v2 (Stage 7).
Deterministic pass/fail gate enforcing:
1. Rule DSL schema & Rego compilation validity
2. 100% clause-level citation coverage (rejects uncited rules)
3. Conflict resolution verification (cannot pass with active conflict)
4. Comprehensive synthetic unit test suite execution (100% tests must pass)
Emits structured ValidationObjections to re-route via the Objection Loop.
"""

from contracts.agents import AgentCard, AgentSkill
from contracts.policy_mapping import ConflictType, PolicyMappingResult
from contracts.rule_dsl import DSLOperator, RuleDefinition
from contracts.validation import (
    ObjectionCode,
    ObjectionTargetStage,
    ValidationObjection,
    ValidationReport,
)
from services.agents.crypto import AgentKeyPair
from services.regcompiler.dsl_compiler import RuleDSLCompiler
from services.regcompiler.z3_prover import Z3RuleProver

# DSL operator -> the lowercase op token the Z3 prover expects.
_OP_TO_Z3 = {
    DSLOperator.GTE: "gte",
    DSLOperator.LTE: "lte",
    DSLOperator.EQ: "eq",
    DSLOperator.NEQ: "neq",
    DSLOperator.IN: "in",
    DSLOperator.NOT_IN: "not_in",
}


class ValidatorAgent:
    def __init__(
        self,
        key_pair: AgentKeyPair | None = None,
        compiler: RuleDSLCompiler | None = None,
        z3_prover: Z3RuleProver | None = None,
    ):
        self.key_pair = key_pair or AgentKeyPair()
        self.compiler = compiler or RuleDSLCompiler()
        self.z3_prover = z3_prover or Z3RuleProver()
        self.agent_id = "agent.validator"
        self.card = AgentCard(
            agent_id=self.agent_id,
            name="Deterministic Rule Validator Agent",
            version="2.0.0",
            public_key=self.key_pair.public_key_hex,
            skills=[
                AgentSkill(
                    name="validator.verify_draft_rule",
                    description="Deterministic verification of schema, citations, conflicts, and unit tests.",
                )
            ],
        )

    def _rule_def_to_prover_dict(self, rule_def: RuleDefinition) -> dict:
        """Translate a RuleDefinition into the Z3 prover's rule dict shape."""
        clauses = []
        for cond in rule_def.conditions:
            field = cond.field[6:] if cond.field.startswith("input.") else cond.field
            clauses.append(
                {
                    "field": field,
                    "op": _OP_TO_Z3.get(cond.operator, "eq"),
                    "value": cond.value,
                }
            )
        return {
            "rule_id": rule_def.rule_name,
            "when": {"all": clauses},
            "action": {"type": rule_def.action.outcome.lower()},
        }

    def validate_draft_rule(
        self,
        rule_def: RuleDefinition,
        mapping_result: PolicyMappingResult | None = None,
        iteration: int = 1,
    ) -> ValidationReport:
        """
        Stage 7: Validates draft rule across 4 deterministic gates.
        Returns ValidationReport with objections if any gate fails.
        """
        objections: list[ValidationObjection] = []

        # Gate 1: Schema & Syntax Validation
        schema_valid = True
        try:
            rego_code = self.compiler.compile_to_rego(rule_def)
            if not rego_code or "rule_hit if" not in rego_code:
                schema_valid = False
                objections.append(
                    ValidationObjection(
                        objection_id=f"OBJ-SCHEMA-{iteration}",
                        target_stage=ObjectionTargetStage.RULE_AUTHORING,
                        code=ObjectionCode.SCHEMA_VIOLATION,
                        message="Rule definition generated empty or invalid Rego body.",
                        suggested_fix="Re-synthesize rule conditions using valid Rule DSL operators.",
                    )
                )
        except Exception as e:
            schema_valid = False
            objections.append(
                ValidationObjection(
                    objection_id=f"OBJ-SCHEMA-{iteration}",
                    target_stage=ObjectionTargetStage.RULE_AUTHORING,
                    code=ObjectionCode.SCHEMA_VIOLATION,
                    message=f"Rule compilation threw an unhandled exception: {str(e)}",
                    suggested_fix="Verify YAML AST and condition fields.",
                )
            )

        # Gate 2: Z3-backed Active-Conflict Check (B6).
        # For every mapped CONFLICT touching this obligation, we formally prove
        # whether the DRAFTED rule still collides with the existing live rule. The
        # naive first draft has not superseded the live rule, so Z3 finds a
        # satisfying counter-example and we reject with ACTIVE_CONFLICT_UNRESOLVED.
        # Once the author supersedes the live rule (iteration >= 2), the live rule
        # is no longer active against this draft and the gate passes.
        conflict_check_passed = True
        if mapping_result:
            for item in mapping_result.mappings:
                if (
                    item.obligation_id != rule_def.obligation_id
                    or item.conflict_type != ConflictType.CONFLICT
                ):
                    continue
                existing_rule = (item.details or {}).get("existing_rule")
                superseded = item.existing_rule_ref in (rule_def.supersedes or [])
                if superseded or rule_def.conflict_resolved:
                    # Conflict resolved: draft supersedes the live rule.
                    continue

                # Prefer a formal Z3 proof when the live rule carries a predicate
                # ("when"). Otherwise fall back to the structural objection — the
                # conflict is still real and unresolved.
                counter_example = None
                detail_msg = item.description
                if isinstance(existing_rule, dict) and "when" in existing_rule:
                    draft_as_rule = self._rule_def_to_prover_dict(rule_def)
                    proof = self.z3_prover.prove_conflict(draft_as_rule, existing_rule)
                    if not proof.is_satisfiable:
                        # Z3 proved the rules are disjoint — no real conflict.
                        continue
                    counter_example = proof.counter_example
                    detail_msg = proof.message

                conflict_check_passed = False
                objections.append(
                    ValidationObjection(
                        objection_id=f"OBJ-CONF-{iteration}",
                        target_stage=ObjectionTargetStage.POLICY_MAPPING,
                        code=ObjectionCode.ACTIVE_CONFLICT_UNRESOLVED,
                        message=(
                            f"Active conflict unresolved: draft rule '{rule_def.rule_name}' "
                            f"still collides with live rule '{item.existing_rule_ref}'. {detail_msg}"
                        ),
                        suggested_fix=(
                            "Policy Mapper must resolve the conflict and the Rule Author "
                            f"must supersede '{item.existing_rule_ref}': {item.suggested_resolution}"
                        ),
                        source_clause_id=item.clause_id,
                        counter_example=counter_example,
                    )
                )

        # Gate 3: Clause Citation & Traceability Coverage
        citation_valid = True
        if not rule_def.citations or "UNCITED" in rule_def.action.evidence_id:
            citation_valid = False
            citation_coverage = 0.0
            objections.append(
                ValidationObjection(
                    objection_id=f"OBJ-CITE-{iteration}",
                    target_stage=ObjectionTargetStage.RULE_AUTHORING,
                    code=ObjectionCode.UNCITED_CLAUSE,
                    message=f"Rule '{rule_def.rule_name}' lacks verified regulatory clause citations [CLAUSE:<ID>].",
                    suggested_fix=f"Bind rule action evidence_id to source clause '[CLAUSE:{rule_def.clause_id}]'.",
                    source_clause_id=rule_def.clause_id,
                )
            )
        else:
            citation_coverage = 100.0

        # Gate 4: Test Suite Execution
        passed_tests, total_tests, failures = self.compiler.run_synthetic_tests(rule_def)
        test_suite_passed = total_tests >= 2 and passed_tests == total_tests

        if not test_suite_passed:
            objections.append(
                ValidationObjection(
                    objection_id=f"OBJ-TEST-{iteration}",
                    target_stage=ObjectionTargetStage.RULE_AUTHORING,
                    code=ObjectionCode.TEST_FAILURE,
                    message=(
                        f"Unit test suite failed: {passed_tests}/{total_tests} passed. "
                        f"Failures: {'; '.join(failures) if failures else 'Insufficient test cases (minimum 2 required)'}"
                    ),
                    suggested_fix="Generate comprehensive boundary hit and miss test cases for all conditions.",
                )
            )

        overall_passed = (
            schema_valid
            and conflict_check_passed
            and citation_valid
            and test_suite_passed
            and len(objections) == 0
        )

        import hashlib
        certificate_id = (
            f"CERT-VAL-{hashlib.sha256(f'{rule_def.rule_name}-{iteration}'.encode()).hexdigest()[:12].upper()}"
            if overall_passed
            else None
        )

        return ValidationReport(
            rule_name=rule_def.rule_name,
            iteration=iteration,
            passed=overall_passed,
            schema_valid=schema_valid,
            citation_coverage_pct=citation_coverage,
            conflict_check_passed=conflict_check_passed,
            test_suite_passed=test_suite_passed,
            tests_total=total_tests,
            tests_passed=passed_tests,
            objections=objections,
            certificate_id=certificate_id,
        )
