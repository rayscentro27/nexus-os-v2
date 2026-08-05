"""Hermes Capability Contracts — versioned, executable governance.

This module provides the core types and dispatcher for the Hermes
capability-certification system.  Every production-reachable capability
must be declared as a CapabilityContract, routed through the dispatcher,
and return a typed CapabilityResult.

Usage::

    from nexus_agent_platform.contracts import (
        TaskSpec, CapabilityResult, CapabilityContract,
        SemanticDefinition, dispatch, validate_taskspec,
    )
"""

from nexus_agent_platform.contracts.typed import (
    TaskSpec,
    CapabilityResult,
    Scope,
    Authorization,
    ExecutionInfo,
    SourceInfo,
    TASKSPEC_VERSION,
    RESULT_VERSION,
)
from nexus_agent_platform.contracts.definitions import (
    SemanticDefinition,
    SemanticRegistry,
    semantic_registry,
)
from nexus_agent_platform.contracts.contracts import (
    CapabilityContract,
    LifecycleState,
    ContractRegistry,
    contract_registry,
)
from nexus_agent_platform.contracts.dispatcher import (
    dispatch,
    CapabilityDispatcher,
)
from nexus_agent_platform.contracts.validators import (
    validate_taskspec,
    validate_result,
    validate_contract,
)

__all__ = [
    "TaskSpec", "Scope", "Authorization", "ExecutionInfo", "SourceInfo",
    "CapabilityResult",
    "TASKSPEC_VERSION", "RESULT_VERSION",
    "SemanticDefinition", "SemanticRegistry", "semantic_registry",
    "CapabilityContract", "LifecycleState", "ContractRegistry", "contract_registry",
    "dispatch", "CapabilityDispatcher",
    "validate_taskspec", "validate_result", "validate_contract",
]
