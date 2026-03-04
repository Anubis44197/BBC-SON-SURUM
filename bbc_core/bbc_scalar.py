import json

# BBC States
STABLE = "STABLE"
WEAK = "WEAK"
SLEEPING = "SLEEPING"
NEG_ZERO = "NEG_ZERO"
SATURATED = "SATURATED"
UNSTABLE = "UNSTABLE"
DEGENERATE = "DEGENERATE"

# State multiplication tables (Basic arithmetic)
STATE_MULT_BASIC = {
    (STABLE, STABLE): STABLE,
    (STABLE, WEAK): WEAK,
    (WEAK, STABLE): WEAK,
    (WEAK, WEAK): WEAK,
    (STABLE, SLEEPING): SLEEPING,
    (SLEEPING, STABLE): SLEEPING,
    (STABLE, NEG_ZERO): NEG_ZERO,
    (NEG_ZERO, STABLE): NEG_ZERO,
    (UNSTABLE, STABLE): UNSTABLE,
    (STABLE, UNSTABLE): UNSTABLE,
    (DEGENERATE, STABLE): DEGENERATE,
    (STABLE, DEGENERATE): DEGENERATE,
}

# State multiplication tables (Linear Algebra context)
STATE_MULT_LINALG = {
    (STABLE, STABLE): STABLE,
}

class BBCScalar:
    def __init__(self, value, state=STABLE, heal_count=0, metadata=None, origin=None):
        self.value = float(value)
        self.state = state
        self.heal_count = heal_count
        self.metadata = metadata or {}
        if origin:
            # persist latest semantic origin hint
            self.metadata.setdefault("origin", origin)

    @property
    def origin(self):
        """Shortcut for metadata origin."""
        return self.metadata.get("origin", "unknown")

    def __repr__(self):
        meta_str = f", metadata={self.metadata}" if self.metadata else ""
        return f"BBCScalar({self.value}, state='{self.state}', heal_count={self.heal_count}{meta_str})"

    def __float__(self):
        return self.value

    def __eq__(self, other):
        if isinstance(other, BBCScalar):
            return self.value == other.value and self.state == other.state
        return self.value == float(other)

    def __hash__(self):
        return hash((self.value, self.state))

    def __lt__(self, other):
        val = other.value if isinstance(other, BBCScalar) else float(other)
        return self.value < val

    def __gt__(self, other):
        val = other.value if isinstance(other, BBCScalar) else float(other)
        return self.value > val

    def __le__(self, other):
        val = other.value if isinstance(other, BBCScalar) else float(other)
        return self.value <= val

    def __ge__(self, other):
        val = other.value if isinstance(other, BBCScalar) else float(other)
        return self.value >= val

    def _determine_new_state(self, other_state):
        if self.state == DEGENERATE or other_state == DEGENERATE:
            return DEGENERATE
        if self.state == UNSTABLE or other_state == UNSTABLE:
            return UNSTABLE
        if self.state == NEG_ZERO or other_state == NEG_ZERO:
            return NEG_ZERO
        if self.state == SATURATED or other_state == SATURATED:
            return SATURATED
        if self.state == WEAK or other_state == WEAK:
            return WEAK
        if self.state == SLEEPING or other_state == SLEEPING:
            return SLEEPING
        return STABLE

    def _merge_origin(self, other):
        """Origin downgrade rule: math + semantic -> semantic; math + math -> math."""
        self_origin = self.metadata.get("origin", "unknown")
        other_origin = other.metadata.get("origin", "unknown") if isinstance(other, BBCScalar) else "unknown"
        if self_origin == "math" and other_origin == "math":
            return "math"
        if self_origin == "math" or other_origin == "math":
            return "semantic"
        return self_origin if self_origin != "unknown" else other_origin

    def _build_result_metadata(self, other, new_state):
        """Build metadata for arithmetic result, including security flags."""
        merged_origin = self._merge_origin(other)
        meta = {"origin": merged_origin}
        # Security flag: math-origin scalar hitting DEGENERATE
        if merged_origin == "math" and new_state == DEGENERATE:
            meta["security_flag"] = "MATH_CORE_DEGENERATION_ANOMALY"
        # Also flag if either operand is math-origin and result is degenerate
        self_origin = self.metadata.get("origin", "unknown")
        other_origin = other.metadata.get("origin", "unknown") if isinstance(other, BBCScalar) else "unknown"
        if new_state == DEGENERATE and (self_origin == "math" or other_origin == "math"):
            meta["security_flag"] = "MATH_CORE_DEGENERATION_ANOMALY"
        return meta

    def __add__(self, other):
        val = other.value if isinstance(other, BBCScalar) else float(other)
        other_state = other.state if isinstance(other, BBCScalar) else STABLE
        new_state = self._determine_new_state(other_state)
        new_heal_count = max(self.heal_count, getattr(other, 'heal_count', 0))
        meta = self._build_result_metadata(other, new_state)
        return BBCScalar(self.value + val, new_state, new_heal_count, metadata=meta)

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        val = other.value if isinstance(other, BBCScalar) else float(other)
        other_state = other.state if isinstance(other, BBCScalar) else STABLE
        new_state = self._determine_new_state(other_state)
        new_heal_count = max(self.heal_count, getattr(other, 'heal_count', 0))
        meta = self._build_result_metadata(other, new_state)
        return BBCScalar(self.value - val, new_state, new_heal_count, metadata=meta)

    def __rsub__(self, other):
        val = other.value if isinstance(other, BBCScalar) else float(other)
        other_state = other.state if isinstance(other, BBCScalar) else STABLE
        new_state = self._determine_new_state(other_state)
        new_heal_count = max(self.heal_count, getattr(other, 'heal_count', 0))
        meta = self._build_result_metadata(other, new_state)
        return BBCScalar(val - self.value, new_state, new_heal_count, metadata=meta)

    def __mul__(self, other):
        val = other.value if isinstance(other, BBCScalar) else float(other)
        other_state = other.state if isinstance(other, BBCScalar) else STABLE
        new_state = self._determine_new_state(other_state)
        new_heal_count = max(self.heal_count, getattr(other, 'heal_count', 0))
        meta = self._build_result_metadata(other, new_state)
        return BBCScalar(self.value * val, new_state, new_heal_count, metadata=meta)

    def __rmul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other):
        val = other.value if isinstance(other, BBCScalar) else float(other)
        other_state = other.state if isinstance(other, BBCScalar) else STABLE
        new_heal_count = max(self.heal_count, getattr(other, 'heal_count', 0))
        
        if val == 0:
            return BBCScalar(0.0, UNSTABLE, new_heal_count)
            
        new_state = self._determine_new_state(other_state)
        meta = self._build_result_metadata(other, new_state)
        return BBCScalar(self.value / val, new_state, new_heal_count, metadata=meta)

    def enter_neg_zero(self):
        self.value = -0.0
        self.state = NEG_ZERO

    def resolve_neg_zero(self):
        """
        Modified Strict Logic:
        Always resolves to WEAK, never SLEEPING or STABLE immediately.
        Confidence is permanently degraded.
        """
        if self.state == NEG_ZERO:
            self.value = 0.0
            self.state = WEAK
        return self

    def to_dict(self):
        return {
            "value": self.value, 
            "state": self.state, 
            "heal_count": self.heal_count,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data):
        # Security: origin is always forced to 'semantic' when deserializing
        # to prevent origin spoofing from untrusted data
        meta = dict(data.get("metadata", {}))
        meta["origin"] = "semantic"
        return cls(
            data["value"], 
            data.get("state", STABLE), 
            data.get("heal_count", 0),
            meta
        )

class OmegaOperator:
    @staticmethod
    def trigger(scalar: BBCScalar):
        """
        Modified Strict Logic:
        Healing results in WEAK state (degraded confidence).
        """
        if scalar.state in [NEG_ZERO, UNSTABLE]:
            epsilon = 1e-6 * (1 + scalar.heal_count)
            scalar.value = epsilon
            scalar.state = WEAK
            scalar.heal_count += 1
        # DEGENERATE ise hiçbir değişiklik yapma
        return scalar

class BBCEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, BBCScalar):
            return obj.to_dict()
        return super().default(obj)

def bbc_hook(obj):
    if isinstance(obj, dict) and "value" in obj and "state" in obj:
        return BBCScalar.from_dict(obj)
    return obj

def bbc_data_ingestion(data, origin=None):
    if isinstance(data, list):
        return [bbc_data_ingestion(x, origin=origin) for x in data]
    if isinstance(data, dict):
        return {k: bbc_data_ingestion(v, origin=origin) for k, v in data.items()}
    if isinstance(data, BBCScalar):
        if origin:
            data.metadata.setdefault("origin", origin)
        return data
    if isinstance(data, (float, int)):
        scalar = BBCScalar(data)
        if origin:
            scalar.metadata["origin"] = origin
        return scalar
    return data
