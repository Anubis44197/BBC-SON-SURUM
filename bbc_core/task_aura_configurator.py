"""
BBC Task-Aware Aura Configurator  
Adapts Harrier's task-specific instruction to BBC Aura Field mathematics

Dynamically configures HMPU Governor's Aura matrix based on task type
NO neural networks - pure BBC mathematical matrix operations
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from .bbc_scalar import BBCScalar, bbc_data_ingestion, STABLE, WEAK, DEGENERATE
from .hmpu_core import HMPU_Governor


@dataclass
class AuraProfile:
    """Configuration profile for Aura Field matrix"""
    name: str
    base_matrix: List[List[float]]  # 3x3 S/C/P matrix
    description: str
    # Weight multipliers for different symbol types
    symbol_weights: Dict[str, float]
    # Chaos tolerance: how much complexity is acceptable
    chaos_tolerance: float  # 0.0-1.0, higher = more tolerant
    # Pulse priority: how important is recency
    pulse_priority: float  # 0.0-1.0


class TaskAwareAuraConfigurator:
    """
    Configures HMPU Governor's Aura Field based on task type.
    
    Each task (bugfix, feature, refactor, review) has an optimal
    Aura matrix configuration that maximizes relevant symbol retrieval.
    
    This is BBC's adaptation of Harrier's task-specific instruction
    prompting - but using matrix mathematics instead of text prefixes.
    """
    
    # Pre-defined Aura profiles for each task type
    # Matrix format: [S_row, C_row, P_row] where each row is [S_col, C_col, P_col]
    TASK_AURA_PROFILES = {
        "bugfix": AuraProfile(
            name="bugfix",
            description="Optimized for finding and fixing bugs",
            base_matrix=[
                #       S_col    C_col    P_col
                [0.85, 0.10, 0.05],  # S_row: Structure focused, less chaos
                [0.75, 0.18, 0.07],  # C_row: Error handling patterns
                [0.65, 0.15, 0.20]   # P_row: Recent changes important
            ],
            symbol_weights={
                "error_handler": 2.5,
                "exception_class": 2.0,
                "validator": 1.8,
                "test_function": 1.5,
                "logger": 1.3,
                "class": 1.0,
                "function": 0.9,
                "method": 0.85
            },
            chaos_tolerance=0.8,  # High tolerance (bugs often in complex code)
            pulse_priority=0.7    # Recent changes likely caused bug
        ),
        
        "feature": AuraProfile(
            name="feature",
            description="Optimized for implementing new features",
            base_matrix=[
                [0.95, 0.03, 0.02],  # S_row: Very high structure (patterns)
                [0.55, 0.30, 0.15],  # C_row: Moderate chaos (new code complex)
                [0.80, 0.08, 0.12]   # P_row: High pulse (new code)
            ],
            symbol_weights={
                "interface": 2.2,
                "abstract_class": 2.0,
                "factory": 1.8,
                "pattern": 1.7,
                "base_class": 1.6,
                "api_endpoint": 1.5,
                "service": 1.4,
                "model": 1.3
            },
            chaos_tolerance=0.5,  # Low tolerance (new code should be clean)
            pulse_priority=0.9    # Very high (new feature = new code)
        ),
        
        "refactor": AuraProfile(
            name="refactor",
            description="Optimized for code refactoring",
            base_matrix=[
                [0.88, 0.08, 0.04],  # S_row: High structure (refactoring targets)
                [0.80, 0.12, 0.08],  # C_row: High chaos (complex code to refactor)
                [0.60, 0.15, 0.25]   # P_row: Medium pulse (refactor old code too)
            ],
            symbol_weights={
                "duplicate": 2.5,
                "long_function": 2.2,
                "complex_class": 2.0,
                "smelly_code": 1.8,
                "legacy": 1.5,
                "class": 1.0,
                "function": 1.1  # Functions often need refactoring
            },
            chaos_tolerance=0.9,  # Very high (refactor = target complex code)
            pulse_priority=0.4     # Low (refactor old code too)
        ),
        
        "review": AuraProfile(
            name="review",
            description="Optimized for code review",
            base_matrix=[
                [0.90, 0.06, 0.04],  # S_row: High structure
                [0.70, 0.20, 0.10],  # C_row: Medium-high chaos (complex code)
                [0.85, 0.08, 0.07]   # P_row: High pulse (recent changes)
            ],
            symbol_weights={
                "security_sensitive": 2.5,
                "performance_critical": 2.3,
                "public_api": 2.0,
                "core_module": 1.8,
                "database": 1.6,
                "auth": 1.7,
                "test": 1.2
            },
            chaos_tolerance=0.7,
            pulse_priority=0.8     # Recent changes need review
        ),
        
        "test": AuraProfile(
            name="test",
            description="Optimized for test generation",
            base_matrix=[
                [0.92, 0.05, 0.03],  # S_row: Very high structure
                [0.65, 0.25, 0.10],  # C_row: Medium chaos (edge cases)
                [0.50, 0.20, 0.30]   # P_row: Medium pulse (tests for old code too)
            ],
            symbol_weights={
                "untested": 2.5,
                "critical_path": 2.2,
                "branching": 1.9,
                "edge_case": 1.7,
                "public_method": 1.5,
                "complex_logic": 1.4
            },
            chaos_tolerance=0.6,
            pulse_priority=0.5
        ),
        
        "general": AuraProfile(
            name="general",
            description="Balanced configuration for general tasks",
            base_matrix=[
                [1.00, 0.00, 0.00],  # S_row: Pure structural (default HMPU)
                [0.75, 0.15, 0.10],  # C_row: Default chaos
                [0.70, 0.10, 0.20]   # P_row: Default pulse
            ],
            symbol_weights={
                "class": 1.0,
                "function": 0.9,
                "method": 0.85,
                "variable": 0.3
            },
            chaos_tolerance=0.6,
            pulse_priority=0.5
        )
    }
    
    def __init__(self, governor: Optional[HMPU_Governor] = None):
        self.governor = governor
    
    def configure_for_task(self, task_type: str, 
                           governor: Optional[HMPU_Governor] = None) -> HMPU_Governor:
        """
        Configure HMPU Governor's Aura Field for specific task type.
        
        Args:
            task_type: One of "bugfix", "feature", "refactor", "review", "test", "general"
            governor: HMPU Governor instance (uses self.governor if None)
            
        Returns:
            Configured HMPU Governor
        """
        gov = governor or self.governor
        if gov is None:
            raise ValueError("No HMPU Governor provided")
        
        # Get profile for task (default to "general")
        profile = self.TASK_AURA_PROFILES.get(task_type, self.TASK_AURA_PROFILES["general"])
        
        # Convert base matrix to BBCScalar matrix
        bbc_matrix = bbc_data_ingestion(profile.base_matrix, origin="math")
        
        # Apply to governor
        gov._Aura_Base = bbc_matrix
        
        # Log configuration (if verbose)
        if hasattr(gov, '_log'):
            gov._log(f"Aura configured for task: {profile.name}")
        
        return gov
    
    def get_profile(self, task_type: str) -> AuraProfile:
        """Get Aura profile for a task type"""
        return self.TASK_AURA_PROFILES.get(task_type, self.TASK_AURA_PROFILES["general"])
    
    def calculate_symbol_weight(self, task_type: str, symbol_type: str) -> float:
        """
        Get task-specific weight for a symbol type.
        
        Args:
            task_type: Task type
            symbol_type: Type of symbol (class, function, etc.)
            
        Returns:
            Weight multiplier for the symbol
        """
        profile = self.get_profile(task_type)
        return profile.symbol_weights.get(symbol_type, 1.0)
    
    def should_include_symbol(self, task_type: str, 
                               symbol_chaos: float,
                               symbol_pulse: float) -> bool:
        """
        Determine if symbol should be included based on task profile.
        
        Args:
            task_type: Task type
            symbol_chaos: Symbol's chaos score (0-1)
            symbol_pulse: Symbol's pulse score (0-1)
            
        Returns:
            True if symbol should be included in context
        """
        profile = self.get_profile(task_type)
        
        # Chaos tolerance check
        if symbol_chaos > profile.chaos_tolerance:
            return False
        
        # Pulse priority check (for tasks that care about recency)
        if profile.pulse_priority > 0.7 and symbol_pulse < 0.3:
            # High pulse priority but low pulse symbol
            return False
        
        return True
    
    def get_task_description(self, task_type: str) -> str:
        """Get human-readable description of task profile"""
        profile = self.get_profile(task_type)
        return f"{profile.name}: {profile.description}"


# Convenience functions for common use cases

def configure_governor_for_bugfix(governor: HMPU_Governor) -> HMPU_Governor:
    """Quick configure for bugfix task"""
    configurator = TaskAwareAuraConfigurator()
    return configurator.configure_for_task("bugfix", governor)

def configure_governor_for_feature(governor: HMPU_Governor) -> HMPU_Governor:
    """Quick configure for feature task"""
    configurator = TaskAwareAuraConfigurator()
    return configurator.configure_for_task("feature", governor)

def configure_governor_for_refactor(governor: HMPU_Governor) -> HMPU_Governor:
    """Quick configure for refactor task"""
    configurator = TaskAwareAuraConfigurator()
    return configurator.configure_for_task("refactor", governor)


def get_optimal_aura_for_task(task_type: str) -> List[List[BBCScalar]]:
    """
    Get the optimal Aura matrix for a task type as BBCScalar matrix.
    
    Args:
        task_type: Task type string
        
    Returns:
        3x3 BBCScalar matrix [S/C/P rows][S/C/P cols]
    """
    configurator = TaskAwareAuraConfigurator()
    profile = configurator.get_profile(task_type)
    return bbc_data_ingestion(profile.base_matrix, origin="math")
