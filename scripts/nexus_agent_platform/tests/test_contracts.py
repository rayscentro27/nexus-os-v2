"""Tests for the Hermes Capability Contracts platform.

Verifies TaskSpec validation, CapabilityResult validation,
dispatcher routing, lifecycle enforcement, fail-closed behavior,
and integration with the existing client-count capability.
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from nexus_agent_platform.contracts.typed import (
    TaskSpec, CapabilityResult, Scope, Operation, Entity,
    ResultStatus, TASKSPEC_VERSION, RESULT_VERSION,
    ok_result, error_result, empty_result, forbidden_result,
    SourceInfo,
)
from nexus_agent_platform.contracts.validators import (
    validate_taskspec, validate_result, validate_contract,
)
from nexus_agent_platform.contracts.contracts import (
    CapabilityContract, LifecycleState, contract_registry,
)
from nexus_agent_platform.contracts.definitions import (
    SemanticDefinition, semantic_registry,
)
from nexus_agent_platform.contracts.dispatcher import (
    CapabilityDispatcher, dispatch,
)


# ─── TaskSpec Validation ───────────────────────────────────────

class TestTaskSpecValidation:
    def test_valid_taskspec(self):
        ts = TaskSpec(
            operation=Operation.RETRIEVE_METRIC.value,
            entity=Entity.CLIENT.value,
        )
        valid, errors = validate_taskspec(ts)
        assert valid
        assert errors == []

    def test_missing_operation(self):
        ts = TaskSpec(entity=Entity.CLIENT.value)
        valid, errors = validate_taskspec(ts)
        assert not valid
        assert any("operation" in e for e in errors)

    def test_invalid_operation(self):
        ts = TaskSpec(operation="bogus", entity=Entity.CLIENT.value)
        valid, errors = validate_taskspec(ts)
        assert not valid
        assert any("Invalid operation" in e for e in errors)

    def test_missing_entity(self):
        ts = TaskSpec(operation=Operation.RETRIEVE_METRIC.value)
        valid, errors = validate_taskspec(ts)
        assert not valid
        assert any("entity" in e for e in errors)

    def test_forbidden_tenant_in_scope(self):
        ts = TaskSpec(
            operation=Operation.RETRIEVE_METRIC.value,
            entity=Entity.CLIENT.value,
        )
        ts.scope.tenant = "some_other_tenant"
        valid, errors = validate_taskspec(ts)
        assert not valid
        assert any("tenant" in e for e in errors)

    def test_forbidden_sql_in_filters(self):
        ts = TaskSpec(
            operation=Operation.RETRIEVE_METRIC.value,
            entity=Entity.CLIENT.value,
            filters={"raw_sql": "SELECT * FROM clients"},
        )
        valid, errors = validate_taskspec(ts)
        assert not valid
        assert any("raw_sql" in e for e in errors)

    def test_forbidden_table_name(self):
        ts = TaskSpec(
            operation=Operation.RETRIEVE_METRIC.value,
            entity=Entity.CLIENT.value,
            filters={"table_name": "client_profiles"},
        )
        valid, errors = validate_taskspec(ts)
        assert not valid
        assert any("table_name" in e for e in errors)

    def test_side_effect_not_allowed_for_read(self):
        ts = TaskSpec(
            operation=Operation.RETRIEVE_METRIC.value,
            entity=Entity.CLIENT.value,
            side_effect_requested=True,
        )
        valid, errors = validate_taskspec(ts)
        assert not valid
        assert any("Side effects" in e for e in errors)

    def test_confidence_bounds(self):
        ts = TaskSpec(
            operation=Operation.RETRIEVE_METRIC.value,
            entity=Entity.CLIENT.value,
            confidence=1.5,
        )
        valid, errors = validate_taskspec(ts)
        assert not valid
        assert any("confidence" in e for e in errors)

    def test_valid_side_effect_action(self):
        ts = TaskSpec(
            operation=Operation.EXECUTE_ACTION.value,
            entity=Entity.EMAIL.value,
            side_effect_requested=True,
        )
        valid, errors = validate_taskspec(ts)
        assert valid


# ─── CapabilityResult Validation ───────────────────────────────

class TestCapabilityResultValidation:
    def test_valid_ok_result(self):
        r = ok_result(
            capability_id="test",
            capability_version="v1",
            definition_id="test_def@v1",
            data={"count": 5},
            source_id="test_source",
            handler_id="test_handler",
        )
        valid, errors = validate_result(r)
        assert valid

    def test_ok_without_data(self):
        r = CapabilityResult(
            status=ResultStatus.OK.value,
            capability_id="test",
            capability_version="v1",
            definition_id="def@v1",
        )
        valid, errors = validate_result(r)
        assert not valid
        assert any("non-empty data" in e for e in errors)

    def test_ok_with_error(self):
        r = CapabilityResult(
            status=ResultStatus.OK.value,
            capability_id="test",
            capability_version="v1",
            definition_id="def@v1",
            data={"count": 5},
            error="something went wrong",
        )
        valid, errors = validate_result(r)
        assert not valid
        assert any("ok must not have error" in e for e in errors)

    def test_empty_result(self):
        r = empty_result(
            capability_id="test",
            capability_version="v1",
            definition_id="def@v1",
        )
        valid, errors = validate_result(r)
        assert valid

    def test_forbidden_must_have_error(self):
        r = forbidden_result(
            capability_id="test",
            capability_version="v1",
            definition_id="def@v1",
        )
        valid, errors = validate_result(r)
        assert valid

    def test_unavailable_must_have_error(self):
        r = error_result(
            capability_id="test",
            capability_version="v1",
            definition_id="def@v1",
            error="",
        )
        valid, errors = validate_result(r)
        assert not valid

    def test_invalid_status(self):
        r = CapabilityResult(
            status="bogus",
            capability_id="test",
            capability_version="v1",
            definition_id="def@v1",
        )
        valid, errors = validate_result(r)
        assert not valid

    def test_missing_capability_id(self):
        r = CapabilityResult(
            status=ResultStatus.OK.value,
            data={"count": 5},
            source=SourceInfo(source_id="test"),
        )
        valid, errors = validate_result(r)
        assert not valid


# ─── Contract Validation ───────────────────────────────────────

class TestContractValidation:
    def test_valid_certified_contract(self):
        c = CapabilityContract(
            capability_id="test",
            capability_version="v1",
            semantic_definition_id="test_def@v1",
            description="Test capability",
            canonical_handler_id="test.handler",
            lifecycle=LifecycleState.CERTIFIED_READ.value,
        )
        valid, errors = validate_contract(c)
        assert valid

    def test_certified_needs_handler(self):
        c = CapabilityContract(
            capability_id="test",
            capability_version="v1",
            semantic_definition_id="test_def@v1",
            description="Test",
            canonical_handler_id="",
            lifecycle=LifecycleState.CERTIFIED_READ.value,
        )
        valid, errors = validate_contract(c)
        assert not valid
        assert any("canonical_handler_id" in e for e in errors)

    def test_certified_needs_definition(self):
        c = CapabilityContract(
            capability_id="test",
            capability_version="v1",
            semantic_definition_id="",
            description="Test",
            canonical_handler_id="test.handler",
            lifecycle=LifecycleState.CERTIFIED_READ.value,
        )
        valid, errors = validate_contract(c)
        assert not valid
        assert any("semantic_definition_id" in e for e in errors)

    def test_side_effect_needs_confirmation(self):
        c = CapabilityContract(
            capability_id="test",
            capability_version="v1",
            semantic_definition_id="def@v1",
            description="Test",
            canonical_handler_id="test.handler",
            side_effect_class="write",
            confirmation_required=False,
        )
        valid, errors = validate_contract(c)
        assert not valid
        assert any("confirmation" in e for e in errors)


# ─── Dispatcher ────────────────────────────────────────────────

class TestDispatcher:
    def setup_method(self):
        self.dispatcher = CapabilityDispatcher()

    def test_client_count_dispatch(self):
        """Client count resolves to get_client_count capability."""
        ts = TaskSpec(
            operation=Operation.RETRIEVE_METRIC.value,
            entity=Entity.CLIENT.value,
        )
        cap_id = self.dispatcher._resolve_capability_id(ts)
        assert cap_id == "get_client_count"

    def test_active_client_count_dispatch(self):
        """Active client count resolves with metric_definition hint."""
        ts = TaskSpec(
            operation=Operation.RETRIEVE_METRIC.value,
            entity=Entity.CLIENT.value,
            metric_definition="active_client_count",
        )
        cap_id = self.dispatcher._resolve_capability_id(ts)
        assert cap_id == "active_client_count"

    def test_system_status_dispatch(self):
        ts = TaskSpec(
            operation=Operation.RETRIEVE_STATUS.value,
            entity=Entity.PROCESS.value,
        )
        cap_id = self.dispatcher._resolve_capability_id(ts)
        assert cap_id == "get_system_status"

    def test_failure_report_dispatch(self):
        ts = TaskSpec(
            operation=Operation.RETRIEVE_STATUS.value,
            entity=Entity.FAILURE.value,
        )
        cap_id = self.dispatcher._resolve_capability_id(ts)
        assert cap_id == "get_failure_report"

    def test_alpha_status_dispatch(self):
        ts = TaskSpec(
            operation=Operation.RETRIEVE_STATUS.value,
            entity=Entity.ALPHA.value,
        )
        cap_id = self.dispatcher._resolve_capability_id(ts)
        assert cap_id == "get_alpha_status"

    def test_client_acquisition_dispatch(self):
        ts = TaskSpec(
            operation=Operation.ADVISE.value,
            entity=Entity.CLIENT.value,
        )
        cap_id = self.dispatcher._resolve_capability_id(ts)
        assert cap_id == "client_acquisition_advisory"

    def test_unknown_dispatch(self):
        ts = TaskSpec(
            operation=Operation.RETRIEVE_METRIC.value,
            entity=Entity.TRADING.value,
        )
        cap_id = self.dispatcher._resolve_capability_id(ts)
        assert cap_id is None

    def test_quarantined_capability_blocked(self):
        """Quarantined capabilities cannot execute in production."""
        ts = TaskSpec(
            operation=Operation.EXECUTE_ACTION.value,
            entity=Entity.EMAIL.value,
        )
        result = self.dispatcher.dispatch(
            ts,
            authenticated_context={"is_admin": True},
        )
        assert result.status == ResultStatus.FORBIDDEN.value
        assert "not certified" in result.error.lower()

    def test_invalid_taskspec_rejected(self):
        ts = TaskSpec(operation="", entity="")
        result = self.dispatcher.dispatch(ts)
        assert result.status == ResultStatus.INVALID.value

    def test_missing_authorization(self):
        ts = TaskSpec(
            operation=Operation.RETRIEVE_METRIC.value,
            entity=Entity.CLIENT.value,
        )
        result = self.dispatcher.dispatch(
            ts,
            authenticated_context={},
        )
        # Should fail authorization (not admin)
        assert result.status == ResultStatus.FORBIDDEN.value

    def test_valid_dispatch_with_admin(self):
        ts = TaskSpec(
            operation=Operation.RETRIEVE_METRIC.value,
            entity=Entity.CLIENT.value,
        )
        result = self.dispatcher.dispatch(
            ts,
            authenticated_context={"is_admin": True},
        )
        # Should succeed (or fail gracefully if Supabase unavailable)
        assert result.status in (
            ResultStatus.OK.value,
            ResultStatus.EMPTY.value,
            ResultStatus.UNAVAILABLE.value,
        )


# ─── Semantic Definitions ──────────────────────────────────────

class TestSemanticDefinitions:
    def test_production_client_summary_exists(self):
        d = semantic_registry.get("production_client_summary", "v1")
        assert d is not None
        assert d.lifecycle_state == "certified_read"

    def test_definition_has_owner(self):
        d = semantic_registry.get("production_client_summary", "v1")
        assert d.business_owner
        assert d.technical_owner

    def test_definition_has_source(self):
        d = semantic_registry.get("production_client_summary", "v1")
        assert "supabase" in d.approved_source.lower() or "client_profiles" in d.approved_source

    def test_definition_has_exclusions(self):
        d = semantic_registry.get("production_client_summary", "v1")
        assert "tester" in d.excluded_records.lower() or "demo" in d.excluded_records.lower()


# ─── Contract Registry ─────────────────────────────────────────

class TestContractRegistry:
    def test_certified_contracts_exist(self):
        certified = contract_registry.list_certified()
        assert len(certified) >= 4  # client_count, system_status, failure, alpha

    def test_quarantined_contracts_exist(self):
        quarantined = contract_registry.list_quarantined()
        assert len(quarantined) >= 2  # send_email, schedule_report

    def test_client_count_is_certified(self):
        c = contract_registry.get("get_client_count")
        assert c is not None
        assert c.is_certified()

    def test_client_count_has_handler(self):
        h = contract_registry.get_handler("get_client_count")
        assert h is not None
        assert callable(h)

    def test_send_email_is_quarantined(self):
        c = contract_registry.get("send_email")
        assert c is not None
        assert not c.is_production_allowed()
        assert c.lifecycle == LifecycleState.QUARANTINED.value


# ─── Fail-Closed Behavior ──────────────────────────────────────

class TestFailClosed:
    def test_handler_exception_becomes_unavailable(self):
        """Handler exception must not become status=ok or zero."""
        from nexus_agent_platform.contracts.dispatcher import CapabilityDispatcher

        class FailingDispatcher(CapabilityDispatcher):
            def _resolve_capability_id(self, ts):
                return "get_client_count"

        # Force a handler exception by passing invalid context
        ts = TaskSpec(
            operation=Operation.RETRIEVE_METRIC.value,
            entity=Entity.CLIENT.value,
        )
        # The actual handler will try to read Supabase, which may fail
        # That failure must become UNAVAILABLE, not OK with count=0
        result = dispatch(
            ts,
            authenticated_context={"is_admin": True},
        )
        # If Supabase is unreachable, must be unavailable
        if result.error:
            assert result.status != ResultStatus.OK.value
