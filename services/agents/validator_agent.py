"""
Validator Agent for ARGUS v2 (Stage 7).
Deterministic pass/fail gate enforcing:
1. Rule DSL schema & Rego compilation validity
2. 100% clause-level citation coverage (rejects uncited rules)
3. Conflict resolution verification (cannot pass with active conflict)
4. Comprehensive synthetic unit test suite execution (100% tests must pass)
Emits structured ValidationObjections to re-route via the Objection Loop.
"""

import uuid
from contracts.agents import AgentCard, AgentSkill
from contracts.policy_mapping import ConflictStatus, PolicyMappingResult
from contracts.rule_dsl import RuleDefinition
from contracts.validation import (
    ObjectionCode,
    ObjectionTargetStage,
    ValidationObjection,
    ValidationReport,
)
from services.agents.crypto import AgentKeyPair
from services.regcompiler.dsl_compiler import RuleDSLCompiler


class ValidatorAgent:
    def __init__(
        self,
        key_pair: AgentKeyPair | None = None,
        compiler: RuleDSLCompiler | None = None,
    ):
        self.key_pair = key_pair or AgentKeyPair()
        self.compiler = compiler or RuleDSLCompiler()
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

        # Gate 2: Conflict Resolution Check
        conflict_check_passed = True
        if mapping_result:
            for item in mapping_result.mappings:
                if item.obligation_id == rule_def.obligation_id and item.conflict_type.value == "CONFLICT" and item.status == ConflictStatus.DETECTED:
                    conflict_check_passed = False
                    objections.append(
                        ValidationObjection(
                            objection_id=f"OBJ-CONF-{iteration}",
                            target_stage=ObjectionTargetStage.POLICY_MAPPING,
                            code=ObjectionCode.UNRESOLVED_CONFLICT,
                            message=(
                                f"Active conflict detected between obligation '{item.obligation_id}' "
                                f"and existing system rule '{item.existing_rule_ref}'. "
                                f"{item.description}"
                            ),
                            suggested_fix=(
                                f"Policy Mapper and Rule Author must resolve conflict: "
                                f"{item.suggested_resolution}"
                            ),
                            source_clause_id=item.clause_id,
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
