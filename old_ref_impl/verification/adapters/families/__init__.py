from genfxn.verification.adapters.families.bitops import (
    ADAPTER as BITOPS_ADAPTER,
)
from genfxn.verification.adapters.families.fsm import ADAPTER as FSM_ADAPTER
from genfxn.verification.adapters.families.graph_queries import (
    ADAPTER as GRAPH_QUERIES_ADAPTER,
)
from genfxn.verification.adapters.families.intervals import (
    ADAPTER as INTERVALS_ADAPTER,
)
from genfxn.verification.adapters.families.piecewise import (
    ADAPTER as PIECEWISE_ADAPTER,
)
from genfxn.verification.adapters.families.sequence_dp import (
    ADAPTER as SEQUENCE_DP_ADAPTER,
)
from genfxn.verification.adapters.families.simple_algorithms import (
    ADAPTER as SIMPLE_ALGORITHMS_ADAPTER,
)
from genfxn.verification.adapters.families.stack_bytecode import (
    ADAPTER as STACK_BYTECODE_ADAPTER,
)
from genfxn.verification.adapters.families.stateful import (
    ADAPTER as STATEFUL_ADAPTER,
)
from genfxn.verification.adapters.families.stringrules import (
    ADAPTER as STRINGRULES_ADAPTER,
)
from genfxn.verification.adapters.families.temporal_logic import (
    ADAPTER as TEMPORAL_LOGIC_ADAPTER,
)

ALL_ADAPTERS = (
    PIECEWISE_ADAPTER,
    STATEFUL_ADAPTER,
    SIMPLE_ALGORITHMS_ADAPTER,
    STRINGRULES_ADAPTER,
    BITOPS_ADAPTER,
    SEQUENCE_DP_ADAPTER,
    INTERVALS_ADAPTER,
    GRAPH_QUERIES_ADAPTER,
    TEMPORAL_LOGIC_ADAPTER,
    STACK_BYTECODE_ADAPTER,
    FSM_ADAPTER,
)

__all__ = ["ALL_ADAPTERS"]
