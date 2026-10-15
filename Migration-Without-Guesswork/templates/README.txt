Original book forms A1–A11. MIT licensed with the companion. One CSV per record type; headers plus one empty row. Duplicate rows for multiple records. Keep dates/time zones explicit and artifact/decision references stable. Use an approved controlled location for sensitive project information. Do not place credentials or raw customer payloads in these forms. These are independent book resources, not copies of separately sold packs.


FORM GUIDE

A01_Service_Acceptance.csv
State a required outcome, who accepts it and the evidence that will demonstrate it.
Fields: contract_id, version, service, population, exclusions, journey, claim, invariant, required_observation, business_owner, operations_owner, decision_authority, stop_authority, interruption_limit, recovery_requirement, retirement_scope

A02_Dependency.csv
Record a service dependency, its owner, failure consequences and verification.
Fields: dependency_id, outcome, caller, callee, population, business_period, protocol, data_semantics, effect_semantics, identity_owner, schedule, observed_evidence, migration_treatment, receiving_owner, open_question

A03_Comparison_Contract.csv
Define the exact compared population, identities, boundaries and equivalence rules.
Fields: contract_id, version, run_id, source_artifact, target_artifact, key, grain, population_predicate, exclusions, boundary, applied_checkpoint, mapping_version, normalisation, currency_units, duplicate_rule, null_rule, required_fields, relationships, coverage_limits

A04_Run_Manifest.csv
Retain the inputs and versions needed to reproduce a particular run.
Fields: run_id, operator, start_utc, finish_utc, environment, script_version, configuration, input_artifacts, scope, boundary, output_artifacts, completion_state, findings, logs, qualifications, checksum_algorithm

A05_Exception.csv
Track one finding from original evidence to correction/retest or authorised exception.
Fields: exception_id, run_id, category, business_key, affected_population, original_value, observed_value, consequence, uncertainty, cause, resolver, action, authority, disposition, correction_version, retest_evidence, mitigation, operations_owner, review_trigger, closure_evidence

A06_Cutover_Step.csv
Describe one executable cutover step, prerequisites, duration and verification.
Fields: step_id, prerequisite_state, operator, verifier, artifact_version, action, expected_state, retained_evidence, planned_duration, deadline, stop_condition, recovery_action, communication, actual_start, actual_finish, actual_result, intervention

A07_Authority.csv
Record which side may accept writes and the evidence authorising a transition.
Fields: population, current_writer, enforcement_mechanism, observed_enforcement, scheduler_owner, effect_owner, next_state, prerequisites, decision_id, boundary, transition_result, interrupted_response

A08_Recovery.csv
Define recoverable state, accepted work, recovery limits and drill evidence.
Fields: recovery_id, starting_state, failure_scenario, destination, artifacts, independent_access, accepted_work_boundary, unresolved_data, unresolved_effects, compatibility, transformation, fencing, ordered_steps, expected_duration, observed_duration, resulting_claim, authority, unsupported_cases, decision_deadline

A09_Decision.csv
Record who decided, on which evidence, with which conditions and consequences.
Fields: decision_id, scope, artifact_versions, evidence_map, coverage_limits, exceptions, recovery_limits, authorised_action, next_state, later_gate_conditions, decision_owner, decision_utc, expiry_trigger, supersedes

A10_Handover_Task.csv
Make an operational handover task observable and assign an accepting owner.
Fields: task_id, receiving_role, trigger, input_case, environment, tools, required_access, expected_outcome, observed_actions, assistance, result, elapsed, gap, escalation, retest, procedure_version

A11_Retirement.csv
Record old-system retirement dependencies, inactivity evidence and approvals.
Fields: item_id, component_or_information, owner, consumers, observation_coverage, replacement_or_archive, retention_hold_decision, keys_and_software, retrieval_evidence, disable_delete_action, authority, actual_result, residual_references, continuing_charge, review_disposal_trigger

ENTRY CONVENTIONS
Use stable identifiers for record references. Record timestamp fields in ISO8601
with a timezone (for example 2026-10-15T19:00:00+01:00). State units for durations
and amounts. Scope/population fields must identify inclusions and exclusions,
not just say all. Evidence/manifest/run/decision reference fields should point to
retained artifacts in your approved evidence location. Owners/reviewers must be
real responsible people or roles; do not invent their approval. Do not use a blank
cell as implicit approval. Mark genuinely inapplicable fields with N/A and a reason.

CSV contains text, not controlled dropdowns or enforcement. Check field meanings
against Appendix A before adapting a form. Links to evidence are references, not
attachments. Restrict permissions at the evidence location; these files implement
no access controls. Use a separate controlled copy for sensitive project work.
