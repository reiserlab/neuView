"""
Simplified domain models for neuView.

This module consolidates the core entities and value objects into a single,
maintainable file while preserving all functionality.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


class SomaSide(Enum):
    """Enumeration for neuron soma side."""

    LEFT = "left"
    RIGHT = "right"
    MIDDLE = "middle"
    COMBINED = "combined"
    ALL = "all"

    @classmethod
    def from_string(cls, value: str) -> "SomaSide":
        """Create SomaSide from string value."""
        if isinstance(value, cls):
            return value

        value_lower = value.lower().strip()
        for side in cls:
            if side.value == value_lower:
                return side

        # Handle aliases
        if value_lower in ("l", "left"):
            return cls.LEFT
        elif value_lower in ("r", "right"):
            return cls.RIGHT
        elif value_lower in ("m", "middle", "center"):
            return cls.MIDDLE
        elif value_lower in ("bilateral", "combined"):
            return cls.COMBINED
        elif value_lower in ("all", "*"):
            return cls.ALL

        raise ValueError(f"Invalid soma side: {value}")


@dataclass(frozen=True)
class BodyId:
    """Value object representing a neuron body ID."""

    value: int

    def __post_init__(self):
        if not isinstance(self.value, int) or self.value <= 0:
            raise ValueError(f"BodyId must be a positive integer, got {self.value}")

    def __str__(self) -> str:
        return str(self.value)

    def __int__(self) -> int:
        return self.value


@dataclass(frozen=True)
class NeuronTypeName:
    """Value object representing a neuron type name."""

    value: str

    def __post_init__(self):
        if not self.value or not self.value.strip():
            raise ValueError("NeuronTypeName cannot be empty")
        # Clean up the value and strip surrounding quotes if present
        cleaned_value = self.value.strip()
        if (cleaned_value.startswith('"') and cleaned_value.endswith('"')) or (
            cleaned_value.startswith("'") and cleaned_value.endswith("'")
        ):
            cleaned_value = cleaned_value[1:-1]
        object.__setattr__(self, "value", cleaned_value)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class SynapseCount:
    """Value object representing synapse counts."""

    pre: int = 0
    post: int = 0

    def __post_init__(self):
        if self.pre < 0 or self.post < 0:
            raise ValueError("Synapse counts cannot be negative")

    @property
    def total(self) -> int:
        """Total synapses (pre + post)."""
        return self.pre + self.post

    def __str__(self) -> str:
        return f"{self.pre}:{self.post}"


@dataclass(frozen=True)
class RoiName:
    """Value object representing a Region of Interest name."""

    value: str

    def __post_init__(self):
        if not self.value or not self.value.strip():
            raise ValueError("RoiName cannot be empty")
        object.__setattr__(self, "value", self.value.strip())

    def __str__(self) -> str:
        return self.value


@dataclass
class Neuron:
    """Entity representing a single neuron."""

    body_id: BodyId
    type_name: NeuronTypeName
    instance: Optional[str] = None
    status: Optional[str] = None
    soma_side: Optional[SomaSide] = None
    soma_x: Optional[float] = None
    soma_y: Optional[float] = None
    soma_z: Optional[float] = None
    synapse_count: SynapseCount = field(default_factory=SynapseCount)
    roi_data: Dict[str, Dict[str, int]] = field(default_factory=dict)
    notes: Optional[str] = None
    cell_class: Optional[str] = None
    cell_subclass: Optional[str] = None
    cell_superclass: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        # Ensure body_id is a BodyId instance
        if not isinstance(self.body_id, BodyId):
            self.body_id = BodyId(int(self.body_id))

        # Ensure type_name is a NeuronTypeName instance
        if not isinstance(self.type_name, NeuronTypeName):
            self.type_name = NeuronTypeName(str(self.type_name))

        # Ensure synapse_count is a SynapseCount instance
        if not isinstance(self.synapse_count, SynapseCount):
            if isinstance(self.synapse_count, dict):
                self.synapse_count = SynapseCount(
                    pre=self.synapse_count.get("pre", 0),
                    post=self.synapse_count.get("post", 0),
                )
            else:
                self.synapse_count = SynapseCount()

    @property
    def has_soma_location(self) -> bool:
        """Check if neuron has soma coordinates."""
        return all(
            coord is not None for coord in [self.soma_x, self.soma_y, self.soma_z]
        )



@dataclass
class NeuronCollection:
    """Entity representing a collection of neurons of the same type."""

    type_name: NeuronTypeName
    neurons: List[Neuron] = field(default_factory=list)
    soma_side_filter: Optional[SomaSide] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Ensure type_name is a NeuronTypeName instance
        if not isinstance(self.type_name, NeuronTypeName):
            self.type_name = NeuronTypeName(str(self.type_name))

    def add_neuron(self, neuron: Neuron) -> None:
        """Add a neuron to the collection."""
        if neuron.type_name != self.type_name:
            raise ValueError(
                f"Neuron type {neuron.type_name} doesn't match collection type {self.type_name}"
            )
        self.neurons.append(neuron)

    def filter_by_soma_side(self, soma_side: SomaSide) -> "NeuronCollection":
        """Create a new collection filtered by soma side."""
        if soma_side == SomaSide.ALL:
            return self

        filtered_neurons = [
            neuron for neuron in self.neurons if neuron.soma_side == soma_side
        ]

        return NeuronCollection(
            type_name=self.type_name,
            neurons=filtered_neurons,
            soma_side_filter=soma_side,
            metadata=self.metadata.copy(),
        )

    @property
    def count(self) -> int:
        """Total number of neurons."""
        return len(self.neurons)

    @property
    def body_ids(self) -> List[BodyId]:
        """List of all body IDs."""
        return [neuron.body_id for neuron in self.neurons]


    def get_synapse_statistics(self) -> Dict[str, float]:
        """Calculate synapse statistics for the collection."""
        if not self.neurons:
            return {
                "avg_pre": 0.0,
                "avg_post": 0.0,
                "avg_total": 0.0,
                "median_total": 0.0,
                "std_dev_total": 0.0,
            }

        pre_counts = [neuron.synapse_count.pre for neuron in self.neurons]
        post_counts = [neuron.synapse_count.post for neuron in self.neurons]
        total_counts = [neuron.synapse_count.total for neuron in self.neurons]

        # Calculate basic statistics
        avg_pre = sum(pre_counts) / len(pre_counts)
        avg_post = sum(post_counts) / len(post_counts)
        avg_total = sum(total_counts) / len(total_counts)

        # Calculate median
        sorted_totals = sorted(total_counts)
        n = len(sorted_totals)
        if n % 2 == 0:
            median_total = (sorted_totals[n // 2 - 1] + sorted_totals[n // 2]) / 2
        else:
            median_total = sorted_totals[n // 2]

        # Calculate standard deviation
        variance = sum((x - avg_total) ** 2 for x in total_counts) / len(total_counts)
        std_dev_total = variance**0.5

        return {
            "avg_pre": avg_pre,
            "avg_post": avg_post,
            "avg_total": avg_total,
            "median_total": median_total,
            "std_dev_total": std_dev_total,
        }


@dataclass
class ConnectivityPartner:
    """Represents a connectivity partner with connection strength."""

    neuron_type: NeuronTypeName
    connection_count: int
    connection_weight: float = 0.0
    neurotransmitter: Optional[str] = None

    def __post_init__(self):
        if not isinstance(self.neuron_type, NeuronTypeName):
            self.neuron_type = NeuronTypeName(str(self.neuron_type))


@dataclass
class NeuronTypeConnectivity:
    """Represents connectivity data for a neuron type."""

    type_name: NeuronTypeName
    upstream_partners: List[ConnectivityPartner] = field(default_factory=list)
    downstream_partners: List[ConnectivityPartner] = field(default_factory=list)

    def __post_init__(self):
        if not isinstance(self.type_name, NeuronTypeName):
            self.type_name = NeuronTypeName(str(self.type_name))

    @property
    def total_upstream_connections(self) -> int:
        """Total number of upstream connections."""
        return sum(partner.connection_count for partner in self.upstream_partners)

    @property
    def total_downstream_connections(self) -> int:
        """Total number of downstream connections."""
        return sum(partner.connection_count for partner in self.downstream_partners)


@dataclass
class NeuronTypeStatistics:
    """Statistics for a neuron type."""

    type_name: NeuronTypeName
    total_count: int = 0
    soma_side_counts: Dict[str, int] = field(default_factory=dict)
    synapse_stats: Dict[str, float] = field(default_factory=dict)
    roi_stats: Dict[str, Dict[str, int]] = field(default_factory=dict)
    connectivity: Optional[NeuronTypeConnectivity] = None
    computed_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not isinstance(self.type_name, NeuronTypeName):
            self.type_name = NeuronTypeName(str(self.type_name))

    @property
    def bilateral_ratio(self) -> float:
        """Calculate bilateral ratio (min(left,right) / max(left,right))."""
        left = self.soma_side_counts.get("left", 0)
        right = self.soma_side_counts.get("right", 0)

        if left == 0 and right == 0:
            return 0.0
        if left == 0 or right == 0:
            return 0.0

        return min(left, right) / max(left, right)
