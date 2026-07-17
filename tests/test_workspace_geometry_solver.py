from cbo_hub.avatar_web.workspace_v0 import (
    certify_workspace_proposal,
    normalize_board_state,
    validate_board_geometry,
)


def test_validate_board_geometry_detects_overlap_contact_and_gap() -> None:
    board = normalize_board_state(
        {
            "elements": [
                {"id": "shape_a", "type": "shape", "shape_kind": "rect", "x": 10, "y": 10, "width": 100, "height": 100},
                {"id": "shape_b", "type": "shape", "shape_kind": "rect", "x": 80, "y": 30, "width": 100, "height": 100},
                {"id": "shape_c", "type": "shape", "shape_kind": "rect", "x": 180, "y": 30, "width": 100, "height": 100},
                {"id": "shape_d", "type": "shape", "shape_kind": "rect", "x": 281, "y": 30, "width": 100, "height": 100},
            ]
        }
    )

    result = validate_board_geometry(board, minimum_gap=2)

    assert result["status"] == "invalid"
    assert result["summary"]["overlap_count"] == 1
    assert result["summary"]["contact_count"] == 1
    assert result["summary"]["gap_count"] >= 1


def test_certify_workspace_proposal_repairs_overlapping_layout_deterministically() -> None:
    board = normalize_board_state(
        {
            "elements": [
                {"id": "shape_a", "type": "shape", "shape_kind": "rect", "x": 40, "y": 40, "width": 120, "height": 80, "text": "A"},
                {"id": "shape_b", "type": "shape", "shape_kind": "rect", "x": 60, "y": 55, "width": 120, "height": 80, "text": "B"},
                {"id": "shape_c", "type": "shape", "shape_kind": "rect", "x": 80, "y": 70, "width": 120, "height": 80, "text": "C"},
            ]
        }
    )
    intent = {
        "task_type": "separate_shapes",
        "preserve_order": True,
        "minimum_gap": 4,
        "preferred_strategy": "grid",
        "allow_resize": False,
        "target_element_ids": ["shape_a", "shape_b", "shape_c"],
        "axis": "horizontal",
    }

    first = certify_workspace_proposal(board_state=board, operations=[], intent_schema=intent, proposal_kind="mutation_bearing")
    second = certify_workspace_proposal(board_state=board, operations=[], intent_schema=intent, proposal_kind="mutation_bearing")

    assert first["geometry_status"] == "repaired"
    assert first["constraint_summary"] == "satisfied"
    assert first["solver_strategy_used"] == "grid"
    assert first["validation_result"]["status"] == "valid"
    assert first["operations"] == second["operations"]
    assert len(first["operations"]) >= 2
