# bbc_core package - BBC HMPU v8.3
__version__ = "8.3.0"

from .agent_adapter import BBCAgentAdapter, run_adapter_validation
from .adaptive_mode import (
    BBCAdaptiveMode,
    AdaptiveResponse,
    Mode,
    BBCViolation,
    adaptive_mode_query
)

__all__ = [
    'BBCAgentAdapter',
    'run_adapter_validation',
    'BBCAdaptiveMode',
    'AdaptiveResponse',
    'Mode',
    'BBCViolation',
    'adaptive_mode_query'
]