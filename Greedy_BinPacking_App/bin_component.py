"""Custom drag-and-drop component for the bin-packing board.

Uses Streamlit's stable v1 custom-component protocol (declare_component with
a static frontend directory) rather than any bundler/React setup — the
frontend is a single self-contained frontend/index.html implementing the
well-established postMessage handshake (streamlit:componentReady /
streamlit:render / streamlit:setComponentValue / streamlit:setFrameHeight).

Items are dragged from a palette on the left — at real-to-scale size while
dragging — and dropped onto a fixed (no pan/zoom) grid bin on the right.
Placement validity is still enforced server-side in game_logic.can_place;
the client-side overlap check in the frontend is only for live drag-preview
feedback.
"""

from pathlib import Path

import streamlit.components.v1 as components

CELL_PX = 26

_FRONTEND_DIR = Path(__file__).parent / "frontend"
_bin_packer_component = components.declare_component("bin_packer", path=str(_FRONTEND_DIR))


def bin_packer(bin_w, bin_h, items, placed, key=None, on_change=None):
    """Render the drag-and-drop bin board.

    Returns the last drop event as {"item_id", "x", "y", "rotated"}, or None
    if nothing has been dropped yet for this component instance. If
    on_change is given, it is called with no arguments before the rerun that
    a new drop event triggers; the event is then in st.session_state[key].
    """
    return _bin_packer_component(
        bin_w=bin_w, bin_h=bin_h, items=items, placed=placed, key=key, default=None,
        on_change=on_change,
    )
