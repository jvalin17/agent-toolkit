"""Session state persistence and limit thresholds for session_monitor."""

import json
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

WARN_THRESHOLD_BYTES = 500_000  # ~70% of 200K token window → warning
HARD_THRESHOLD_BYTES = 700_000  # ~85% → handoff trigger
FALLBACK_MAX_EXCHANGES = 30  # Raised from 20
GRACE_TOOL_CALLS = 10  # Tool calls allowed after stop triggers
DEFAULT_MAX_SESSION_MINUTES = 0  # Time-based hard stop (0 = disabled)

SESSION_DIR = ".session"
STATE_FILENAME = "state.json"


@dataclass
class SessionState:
    session_start: int
    exchanges: int = 0
    tool_calls: int = 0
    cumulative_output_bytes: int = 0
    compactions: int = 0
    warned: bool = False
    stopped: int = 0  # 0=running, 1=grace, 2=hard-stop
    stop_at_tool_call: int = 0
    # Strict mode drift tracking
    mode: str = "normal"
    exchanges_since_query: int = 0
    patch_forward_count: int = 0
    slabs_without_data: int = 0
    last_tool_sequence: list = field(default_factory=list)
    has_queried_this_slab: bool = False
    max_session_minutes: int = 0  # 0 = disabled, set via gates.json
    gate_protect: bool = True  # G-GATE-1: block agent writes to .gates/
    report_protect: bool = True  # G-REPORT-1: block agent writes to reports/
    last_test_edits: list = field(default_factory=list)  # F2.6: recent test file paths
    demo_completed: bool = False  # F3.3: set when agent demos after implementation slab
    continue_mode: bool = True  # Assume wrapper; set False only if explicitly disabled


def load_state(state_file: Path) -> SessionState:
    """Load session state from JSON file. Returns fresh state if missing/corrupt."""
    if not state_file.exists():
        return SessionState(session_start=int(time.time()))
    try:
        data = json.loads(state_file.read_text(encoding="utf-8"))
        valid_fields = {f.name for f in SessionState.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        state = SessionState(**filtered)
        if state.max_session_minutes > 0:
            elapsed = int(time.time()) - state.session_start
            if elapsed > state.max_session_minutes * 60 * 2:
                state.session_start = int(time.time())
        return state
    except (json.JSONDecodeError, TypeError, KeyError):
        return SessionState(session_start=int(time.time()))


def save_state(state: SessionState, state_file: Path) -> None:
    """Atomic save — write to temp file then rename."""
    state_file.parent.mkdir(parents=True, exist_ok=True)
    temp_fd, temp_path = tempfile.mkstemp(
        dir=str(state_file.parent), suffix=".tmp"
    )
    try:
        with open(temp_fd, "w", encoding="utf-8") as temp_file:
            json.dump(asdict(state), temp_file, indent=2)
            temp_file.write("\n")
        Path(temp_path).replace(state_file)
    except Exception:
        Path(temp_path).unlink(missing_ok=True)
        raise


def make_hook_response(event_name: str, context: str) -> str:
    """Build the JSON response expected by Claude Code hooks."""
    return json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": event_name,
                "additionalContext": context,
            }
        }
    )


def check_thresholds(state: SessionState) -> tuple:
    """Check if any hard-stop threshold is met. Returns (triggered, reason)."""
    if state.compactions >= 1:
        return True, (
            f"Context compacted ({state.compactions} time(s)) "
            f"— context window is full"
        )

    if state.max_session_minutes > 0:
        elapsed_seconds = int(time.time()) - state.session_start
        elapsed_minutes = elapsed_seconds / 60
        if elapsed_minutes >= state.max_session_minutes:
            return True, (
                f"Session time ({int(elapsed_minutes)} minutes) "
                f"exceeded limit ({state.max_session_minutes} minutes)"
            )

    if state.cumulative_output_bytes > HARD_THRESHOLD_BYTES:
        return True, (
            f"Cumulative output bytes ({state.cumulative_output_bytes:,}) "
            f"exceeded threshold ({HARD_THRESHOLD_BYTES:,})"
        )

    return False, ""


def should_warn(state: SessionState) -> bool:
    """True when approaching byte limit (exchange count is diagnostic only)."""
    if state.warned:
        return False
    return state.cumulative_output_bytes > WARN_THRESHOLD_BYTES
