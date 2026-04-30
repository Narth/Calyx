from __future__ import annotations

import json
import math
import uuid
from copy import deepcopy
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

_ALLOWED_ELEMENT_TYPES = {"text", "shape", "stroke"}
_ALLOWED_SHAPES = {"rect", "ellipse"}
_ALLOWED_OPERATION_TYPES = {"add", "update", "delete", "group", "relabel"}
_ALLOWED_PROPOSAL_KINDS = {"no_op", "advisory_only", "mutation_bearing"}
_ALLOWED_SOLVER_STRATEGIES = {"grid", "linear", "radial", "greedy", "direct"}
_ALLOWED_INTENT_TASK_TYPES = {
    "observe",
    "advisory",
    "separate_shapes",
    "spread_elements",
    "layout_reorganize",
    "place_element",
    "creative_layout",
}
_DEFAULT_CANVAS_WIDTH = 1600.0
_DEFAULT_CANVAS_HEIGHT = 900.0
_DEFAULT_MINIMUM_GAP = 1.0


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _coerce_float(value: Any, *, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(number) or math.isinf(number):
        return default
    return round(number, 2)


def _coerce_int(value: Any, *, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp_dimension(value: Any, *, default: float, minimum: float = 1.0) -> float:
    coerced = _coerce_float(value, default=default)
    return max(minimum, coerced)


def _normalize_points(points: Any) -> list[dict[str, float]]:
    normalized: list[dict[str, float]] = []
    if not isinstance(points, list):
        return normalized
    for point in points:
        if not isinstance(point, dict):
            continue
        normalized.append(
            {
                "x": _coerce_float(point.get("x")),
                "y": _coerce_float(point.get("y")),
            }
        )
    return normalized


def _bounds_from_points(points: list[dict[str, float]]) -> tuple[float, float, float, float]:
    if not points:
        return 0.0, 0.0, 1.0, 1.0
    xs = [point["x"] for point in points]
    ys = [point["y"] for point in points]
    min_x = min(xs)
    min_y = min(ys)
    return (
        min_x,
        min_y,
        max(1.0, max(xs) - min_x),
        max(1.0, max(ys) - min_y),
    )


def _normalize_element(raw: dict[str, Any], *, fallback_order: int = 0) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("element_must_be_object")
    element_type = str(raw.get("type") or "").strip().lower()
    if element_type not in _ALLOWED_ELEMENT_TYPES:
        raise ValueError("unsupported_element_type")
    element_id = str(raw.get("id") or f"el_{uuid.uuid4().hex[:10]}").strip()
    if not element_id:
        raise ValueError("element_id_required")
    order = _coerce_int(raw.get("order"), default=fallback_order)
    base = {
        "id": element_id,
        "type": element_type,
        "order": order,
        "connection_refs": list(raw.get("connection_refs") or []),
        "group_id": str(raw.get("group_id") or "").strip() or None,
    }
    if element_type == "text":
        text = str(raw.get("text") or "").strip()
        base.update(
            {
                "x": _coerce_float(raw.get("x")),
                "y": _coerce_float(raw.get("y")),
                "width": _clamp_dimension(raw.get("width"), default=220.0),
                "height": _clamp_dimension(raw.get("height"), default=72.0),
                "text": text,
                "fill": str(raw.get("fill") or "#f7f3e8"),
                "stroke": str(raw.get("stroke") or "#f6b73c"),
                "stroke_width": _coerce_float(raw.get("stroke_width"), default=1.0),
            }
        )
        return base
    if element_type == "shape":
        shape_payload = raw.get("shape") if isinstance(raw.get("shape"), dict) else {}
        kind = str(raw.get("shape_kind") or shape_payload.get("kind") or "rect").strip().lower()
        if kind not in _ALLOWED_SHAPES:
            raise ValueError("unsupported_shape_kind")
        base.update(
            {
                "x": _coerce_float(raw.get("x")),
                "y": _coerce_float(raw.get("y")),
                "width": _clamp_dimension(raw.get("width"), default=220.0),
                "height": _clamp_dimension(raw.get("height"), default=140.0),
                "text": str(raw.get("text") or "").strip(),
                "fill": str(raw.get("fill") or "rgba(64, 109, 136, 0.18)"),
                "stroke": str(raw.get("stroke") or "#4f9ec4"),
                "stroke_width": _coerce_float(raw.get("stroke_width"), default=2.0),
                "shape_kind": kind,
                "shape": {"kind": kind},
            }
        )
        return base
    points = _normalize_points(raw.get("points"))
    if len(points) < 2:
        raise ValueError("stroke_points_required")
    x, y, width, height = _bounds_from_points(points)
    base.update(
        {
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "points": points,
            "stroke": str(raw.get("stroke") or "#7bdff2"),
            "stroke_width": _coerce_float(raw.get("stroke_width"), default=3.0),
        }
    )
    return base


def default_board_state() -> dict[str, Any]:
    return {
        "board_id": "workspace-v0",
        "version": 1,
        "updated_at": _now_iso(),
        "elements": [],
    }


def normalize_board_state(raw: Any) -> dict[str, Any]:
    if raw in (None, ""):
        return default_board_state()
    if not isinstance(raw, dict):
        raise ValueError("board_state_must_be_object")
    elements_raw = raw.get("elements")
    if elements_raw is None:
        elements_raw = []
    if not isinstance(elements_raw, list):
        raise ValueError("elements_must_be_list")
    elements = [
        _normalize_element(element, fallback_order=index)
        for index, element in enumerate(elements_raw)
    ]
    elements.sort(key=lambda element: (element.get("order", 0), element.get("id", "")))
    return {
        "board_id": str(raw.get("board_id") or "workspace-v0"),
        "version": 1,
        "updated_at": str(raw.get("updated_at") or _now_iso()),
        "elements": elements,
    }


def board_state_hash(board_state: dict[str, Any]) -> str:
    normalized = normalize_board_state(board_state)
    return sha256(json.dumps(normalized, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def default_discussion_state() -> dict[str, Any]:
    return {
        "session_id": "workspace-v0",
        "updated_at": _now_iso(),
        "messages": [],
    }


def default_workspace_meta() -> dict[str, Any]:
    return {
        "session_id": "workspace-v0",
        "updated_at": _now_iso(),
        "last_submission": None,
        "last_proposal": None,
        "last_decision": None,
        "last_failure": None,
    }


def _bbox_intersects(a: dict[str, float], b: dict[str, float]) -> bool:
    return (
        a["left"] < b["right"]
        and a["right"] > b["left"]
        and a["top"] < b["bottom"]
        and a["bottom"] > b["top"]
    )


def _bbox_touching(a: dict[str, float], b: dict[str, float], *, tolerance: float = 0.01) -> bool:
    horizontal_overlap = min(a["right"], b["right"]) - max(a["left"], b["left"])
    vertical_overlap = min(a["bottom"], b["bottom"]) - max(a["top"], b["top"])
    edge_touch = (
        abs(a["right"] - b["left"]) <= tolerance
        or abs(b["right"] - a["left"]) <= tolerance
        or abs(a["bottom"] - b["top"]) <= tolerance
        or abs(b["bottom"] - a["top"]) <= tolerance
    )
    corner_touch = (
        (abs(a["right"] - b["left"]) <= tolerance or abs(b["right"] - a["left"]) <= tolerance)
        and (abs(a["bottom"] - b["top"]) <= tolerance or abs(b["bottom"] - a["top"]) <= tolerance)
    )
    return (edge_touch and horizontal_overlap >= -tolerance and vertical_overlap >= -tolerance) or corner_touch


def _expanded_bbox(geometry: dict[str, Any], gap: float) -> dict[str, float]:
    half_gap = max(0.0, gap) / 2.0
    bbox = geometry["bounding_box"]
    return {
        "left": bbox["left"] - half_gap,
        "right": bbox["right"] + half_gap,
        "top": bbox["top"] - half_gap,
        "bottom": bbox["bottom"] + half_gap,
    }


def normalize_workspace_geometry(
    board_state: dict[str, Any],
    *,
    minimum_gap: float = _DEFAULT_MINIMUM_GAP,
    canvas_width: float = _DEFAULT_CANVAS_WIDTH,
    canvas_height: float = _DEFAULT_CANVAS_HEIGHT,
) -> dict[str, Any]:
    normalized_board = normalize_board_state(board_state)
    elements_geometry: list[dict[str, Any]] = []
    gap_value = max(0.0, _coerce_float(minimum_gap, default=_DEFAULT_MINIMUM_GAP))
    for element in normalized_board["elements"]:
        bbox = {
            "left": _coerce_float(element.get("x")),
            "top": _coerce_float(element.get("y")),
            "right": _coerce_float(element.get("x")) + _clamp_dimension(element.get("width"), default=1.0),
            "bottom": _coerce_float(element.get("y")) + _clamp_dimension(element.get("height"), default=1.0),
        }
        geometry = {
            "id": element["id"],
            "type": element["type"],
            "x": bbox["left"],
            "y": bbox["top"],
            "width": bbox["right"] - bbox["left"],
            "height": bbox["bottom"] - bbox["top"],
            "rotation": 0.0,
            "bounding_box": bbox,
            "expanded_bounding_box": {
                "left": bbox["left"] - (gap_value / 2.0),
                "top": bbox["top"] - (gap_value / 2.0),
                "right": bbox["right"] + (gap_value / 2.0),
                "bottom": bbox["bottom"] + (gap_value / 2.0),
            },
            "center": {
                "x": round((bbox["left"] + bbox["right"]) / 2.0, 2),
                "y": round((bbox["top"] + bbox["bottom"]) / 2.0, 2),
            },
            "edges": {
                "left": bbox["left"],
                "right": bbox["right"],
                "top": bbox["top"],
                "bottom": bbox["bottom"],
            },
        }
        elements_geometry.append(geometry)
    return {
        "board_id": normalized_board["board_id"],
        "canvas": {"width": _coerce_float(canvas_width, default=_DEFAULT_CANVAS_WIDTH), "height": _coerce_float(canvas_height, default=_DEFAULT_CANVAS_HEIGHT)},
        "minimum_gap": gap_value,
        "elements": elements_geometry,
    }


def validate_board_geometry(
    board_state: dict[str, Any],
    *,
    target_element_ids: list[str] | None = None,
    minimum_gap: float = _DEFAULT_MINIMUM_GAP,
    canvas_width: float = _DEFAULT_CANVAS_WIDTH,
    canvas_height: float = _DEFAULT_CANVAS_HEIGHT,
) -> dict[str, Any]:
    geometry = normalize_workspace_geometry(
        board_state,
        minimum_gap=minimum_gap,
        canvas_width=canvas_width,
        canvas_height=canvas_height,
    )
    target_set = {str(item).strip() for item in (target_element_ids or []) if str(item).strip()}
    overlaps: list[dict[str, Any]] = []
    contacts: list[dict[str, Any]] = []
    gap_violations: list[dict[str, Any]] = []
    out_of_bounds: list[dict[str, Any]] = []
    elements = geometry["elements"]
    canvas = geometry["canvas"]
    for index, first in enumerate(elements):
        first_targeted = not target_set or first["id"] in target_set
        if first_targeted:
            bbox = first["bounding_box"]
            if bbox["left"] < 0 or bbox["top"] < 0 or bbox["right"] > canvas["width"] or bbox["bottom"] > canvas["height"]:
                out_of_bounds.append(
                    {
                        "element_id": first["id"],
                        "bounds": bbox,
                    }
                )
        for second in elements[index + 1 :]:
            if target_set and first["id"] not in target_set and second["id"] not in target_set:
                continue
            if _bbox_intersects(first["bounding_box"], second["bounding_box"]):
                overlaps.append({"element_ids": [first["id"], second["id"]]})
                continue
            if _bbox_touching(first["bounding_box"], second["bounding_box"]):
                contacts.append({"element_ids": [first["id"], second["id"]]})
            if _bbox_intersects(_expanded_bbox(first, minimum_gap), _expanded_bbox(second, minimum_gap)):
                gap_violations.append({"element_ids": [first["id"], second["id"]], "minimum_gap": max(0.0, minimum_gap)})
    if overlaps or out_of_bounds:
        status = "invalid"
        severity = "high"
    elif contacts or gap_violations:
        status = "partial"
        severity = "medium"
    else:
        status = "valid"
        severity = "none"
    return {
        "status": status,
        "violations": {
            "overlap_pairs": overlaps,
            "contact_pairs": contacts,
            "gap_pairs": gap_violations,
            "out_of_bounds": out_of_bounds,
        },
        "summary": {
            "violation_count": len(overlaps) + len(contacts) + len(gap_violations) + len(out_of_bounds),
            "severity": severity,
            "overlap_count": len(overlaps),
            "contact_count": len(contacts),
            "gap_count": len(gap_violations),
            "out_of_bounds_count": len(out_of_bounds),
        },
    }


def normalize_workspace_intent_schema(
    raw_intent: Any,
    *,
    operations: list[dict[str, Any]],
    board_state: dict[str, Any],
    operator_note: str = "",
    discussion_response: str = "",
    assessment_only: bool = False,
) -> dict[str, Any]:
    source = raw_intent if isinstance(raw_intent, dict) else {}
    board = normalize_board_state(board_state)
    changed_ids: list[str] = []
    for operation in operations:
        if not isinstance(operation, dict):
            continue
        op_type = str(operation.get("type") or "").strip().lower()
        if op_type == "add":
            element = operation.get("element")
            if isinstance(element, dict) and str(element.get("id") or "").strip():
                changed_ids.append(str(element["id"]).strip())
        elif op_type == "group":
            changed_ids.extend([str(item).strip() for item in operation.get("member_ids") or [] if str(item).strip()])
        else:
            element_id = str(operation.get("element_id") or "").strip()
            if element_id:
                changed_ids.append(element_id)
    note_blob = f"{operator_note} {discussion_response}".lower()
    task_type = str(source.get("task_type") or "").strip().lower()
    if task_type not in _ALLOWED_INTENT_TASK_TYPES:
        if assessment_only:
            task_type = "observe"
        elif any(term in note_blob for term in ("overlap", "separate", "spacing", "minimum gap", "grid", "distribute")):
            task_type = "separate_shapes"
        elif any(term in note_blob for term in ("linear", "row", "column", "horizontal", "vertical")):
            task_type = "spread_elements"
        elif any(term in note_blob for term in ("radial", "around center", "circle", "orbit")):
            task_type = "spread_elements"
        elif any(term in note_blob for term in ("robot", "smile", "smiling", "face", "portrait", "creative")):
            task_type = "creative_layout"
        elif operations:
            task_type = "layout_reorganize"
        else:
            task_type = "observe"
    preferred_strategy = str(source.get("preferred_strategy") or "").strip().lower()
    if preferred_strategy not in _ALLOWED_SOLVER_STRATEGIES:
        if task_type == "separate_shapes":
            preferred_strategy = "grid"
        elif "vertical" in note_blob:
            preferred_strategy = "linear"
        elif any(term in note_blob for term in ("radial", "circle", "orbit")):
            preferred_strategy = "radial"
        elif task_type == "observe":
            preferred_strategy = "direct"
        else:
            preferred_strategy = "greedy"
    preserve_order = bool(source.get("preserve_order", True))
    allow_resize = bool(source.get("allow_resize", False))
    minimum_gap = max(0.0, _coerce_float(source.get("minimum_gap"), default=_DEFAULT_MINIMUM_GAP))
    axis = str(source.get("axis") or "").strip().lower()
    if axis not in {"horizontal", "vertical"}:
        axis = "vertical" if "vertical" in note_blob else "horizontal"
    target_element_ids = [str(item).strip() for item in source.get("target_element_ids") or [] if str(item).strip()]
    if not target_element_ids:
        if task_type in {"separate_shapes", "spread_elements", "layout_reorganize", "creative_layout"}:
            target_element_ids = [str(element["id"]).strip() for element in board["elements"] if element["type"] in {"shape", "text", "stroke"}] + changed_ids
        else:
            target_element_ids = changed_ids
    seen: set[str] = set()
    ordered_targets: list[str] = []
    for item in target_element_ids:
        if item in seen:
            continue
        seen.add(item)
        ordered_targets.append(item)
    return {
        "task_type": task_type,
        "preserve_order": preserve_order,
        "minimum_gap": minimum_gap,
        "preferred_strategy": preferred_strategy,
        "allow_resize": allow_resize,
        "target_element_ids": ordered_targets,
        "axis": axis,
    }


def _solver_sort_key(element: dict[str, Any], *, preserve_order: bool) -> tuple[Any, ...]:
    if preserve_order:
        return (_coerce_int(element.get("order"), default=0), _coerce_float(element.get("y")), _coerce_float(element.get("x")), str(element.get("id") or ""))
    return (_coerce_float(element.get("y")), _coerce_float(element.get("x")), _coerce_int(element.get("order"), default=0), str(element.get("id") or ""))


def _solver_target_elements(board_state: dict[str, Any], target_element_ids: list[str], *, preserve_order: bool) -> list[dict[str, Any]]:
    board = normalize_board_state(board_state)
    target_set = {str(item).strip() for item in target_element_ids if str(item).strip()}
    elements = [deepcopy(element) for element in board["elements"] if element["id"] in target_set]
    elements.sort(key=lambda element: _solver_sort_key(element, preserve_order=preserve_order))
    return elements


def _clamp_position(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, round(value, 2)))


def _reposition_element(element: dict[str, Any], *, x: float, y: float) -> dict[str, Any]:
    next_element = deepcopy(element)
    dx = round(x - _coerce_float(element.get("x")), 2)
    dy = round(y - _coerce_float(element.get("y")), 2)
    next_element["x"] = round(x, 2)
    next_element["y"] = round(y, 2)
    if element.get("type") == "stroke":
        next_element["points"] = [
            {"x": round(_coerce_float(point.get("x")) + dx, 2), "y": round(_coerce_float(point.get("y")) + dy, 2)}
            for point in (element.get("points") or [])
            if isinstance(point, dict)
        ]
    return _normalize_element(next_element, fallback_order=_coerce_int(next_element.get("order"), default=0))


def _apply_positions_to_board(board_state: dict[str, Any], positions: dict[str, dict[str, float]]) -> dict[str, Any]:
    board = normalize_board_state(board_state)
    next_elements: list[dict[str, Any]] = []
    for element in board["elements"]:
        position = positions.get(element["id"])
        if position:
            next_elements.append(_reposition_element(element, x=position["x"], y=position["y"]))
        else:
            next_elements.append(deepcopy(element))
    return normalize_board_state({**board, "elements": next_elements})


def _solve_grid_positions(elements: list[dict[str, Any]], *, canvas_width: float, canvas_height: float, gap: float, preserve_order: bool) -> dict[str, dict[str, float]]:
    if not elements:
        return {}
    items = sorted(elements, key=lambda item: _solver_sort_key(item, preserve_order=preserve_order))
    cols = max(1, math.ceil(math.sqrt(len(items) * max(canvas_width, 1.0) / max(canvas_height, 1.0))))
    max_width = max(_coerce_float(item.get("width"), default=1.0) for item in items)
    max_height = max(_coerce_float(item.get("height"), default=1.0) for item in items)
    step_x = max_width + gap + 24.0
    step_y = max_height + gap + 24.0
    start_x = max(16.0, min(_coerce_float(items[0].get("x")), max(16.0, canvas_width - step_x)))
    start_y = max(16.0, min(_coerce_float(items[0].get("y")), max(16.0, canvas_height - step_y)))
    positions: dict[str, dict[str, float]] = {}
    for index, item in enumerate(items):
        row = index // cols
        col = index % cols
        positions[item["id"]] = {
            "x": _clamp_position(start_x + (col * step_x), 0.0, max(0.0, canvas_width - _coerce_float(item.get("width"), default=1.0))),
            "y": _clamp_position(start_y + (row * step_y), 0.0, max(0.0, canvas_height - _coerce_float(item.get("height"), default=1.0))),
        }
    return positions


def _solve_linear_positions(elements: list[dict[str, Any]], *, canvas_width: float, canvas_height: float, gap: float, preserve_order: bool, axis: str) -> dict[str, dict[str, float]]:
    if not elements:
        return {}
    items = sorted(elements, key=lambda item: _solver_sort_key(item, preserve_order=preserve_order))
    positions: dict[str, dict[str, float]] = {}
    cursor = 24.0
    if axis == "vertical":
        anchor_x = max(12.0, min(_coerce_float(items[0].get("x")), canvas_width / 2.0))
        for item in items:
            positions[item["id"]] = {
                "x": _clamp_position(anchor_x, 0.0, max(0.0, canvas_width - _coerce_float(item.get("width"), default=1.0))),
                "y": _clamp_position(cursor, 0.0, max(0.0, canvas_height - _coerce_float(item.get("height"), default=1.0))),
            }
            cursor += _coerce_float(item.get("height"), default=1.0) + gap + 20.0
        return positions
    anchor_y = max(12.0, min(_coerce_float(items[0].get("y")), canvas_height / 2.0))
    for item in items:
        positions[item["id"]] = {
            "x": _clamp_position(cursor, 0.0, max(0.0, canvas_width - _coerce_float(item.get("width"), default=1.0))),
            "y": _clamp_position(anchor_y, 0.0, max(0.0, canvas_height - _coerce_float(item.get("height"), default=1.0))),
        }
        cursor += _coerce_float(item.get("width"), default=1.0) + gap + 20.0
    return positions


def _solve_radial_positions(elements: list[dict[str, Any]], *, canvas_width: float, canvas_height: float, gap: float, preserve_order: bool) -> dict[str, dict[str, float]]:
    if not elements:
        return {}
    items = sorted(elements, key=lambda item: _solver_sort_key(item, preserve_order=preserve_order))
    center_x = round(sum(_coerce_float(item.get("x")) + (_coerce_float(item.get("width"), default=1.0) / 2.0) for item in items) / len(items), 2)
    center_y = round(sum(_coerce_float(item.get("y")) + (_coerce_float(item.get("height"), default=1.0) / 2.0) for item in items) / len(items), 2)
    avg_size = sum(max(_coerce_float(item.get("width"), default=1.0), _coerce_float(item.get("height"), default=1.0)) for item in items) / len(items)
    radius = max(avg_size + gap + 24.0, (len(items) * (avg_size + gap + 12.0)) / (2.0 * math.pi))
    positions: dict[str, dict[str, float]] = {}
    for index, item in enumerate(items):
        theta = (2.0 * math.pi * index) / max(1, len(items))
        x = center_x + (radius * math.cos(theta)) - (_coerce_float(item.get("width"), default=1.0) / 2.0)
        y = center_y + (radius * math.sin(theta)) - (_coerce_float(item.get("height"), default=1.0) / 2.0)
        positions[item["id"]] = {
            "x": _clamp_position(x, 0.0, max(0.0, canvas_width - _coerce_float(item.get("width"), default=1.0))),
            "y": _clamp_position(y, 0.0, max(0.0, canvas_height - _coerce_float(item.get("height"), default=1.0))),
        }
    return positions


def _solve_greedy_positions(elements: list[dict[str, Any]], *, canvas_width: float, canvas_height: float, gap: float, preserve_order: bool) -> dict[str, dict[str, float]]:
    if not elements:
        return {}
    working = {item["id"]: {"x": _coerce_float(item.get("x")), "y": _coerce_float(item.get("y"))} for item in elements}
    ordered = sorted(elements, key=lambda item: _solver_sort_key(item, preserve_order=preserve_order))
    for _ in range(40):
        moved = False
        board = _apply_positions_to_board({"elements": ordered}, working)
        validation = validate_board_geometry(board, target_element_ids=[item["id"] for item in ordered], minimum_gap=gap, canvas_width=canvas_width, canvas_height=canvas_height)
        pairs = validation["violations"]["overlap_pairs"] + validation["violations"]["gap_pairs"]
        if not pairs and not validation["violations"]["out_of_bounds"]:
            break
        for violation in pairs:
            first_id, second_id = violation["element_ids"]
            first = next(item for item in ordered if item["id"] == first_id)
            second = next(item for item in ordered if item["id"] == second_id)
            first_center_x = working[first_id]["x"] + (_coerce_float(first.get("width"), default=1.0) / 2.0)
            first_center_y = working[first_id]["y"] + (_coerce_float(first.get("height"), default=1.0) / 2.0)
            second_center_x = working[second_id]["x"] + (_coerce_float(second.get("width"), default=1.0) / 2.0)
            second_center_y = working[second_id]["y"] + (_coerce_float(second.get("height"), default=1.0) / 2.0)
            push_x = gap + max(_coerce_float(first.get("width"), default=1.0), _coerce_float(second.get("width"), default=1.0)) / 6.0
            push_y = gap + max(_coerce_float(first.get("height"), default=1.0), _coerce_float(second.get("height"), default=1.0)) / 6.0
            if abs(first_center_x - second_center_x) >= abs(first_center_y - second_center_y):
                direction = -1.0 if first_center_x <= second_center_x else 1.0
                working[second_id]["x"] = _clamp_position(working[second_id]["x"] + (push_x * direction), 0.0, max(0.0, canvas_width - _coerce_float(second.get("width"), default=1.0)))
            else:
                direction = -1.0 if first_center_y <= second_center_y else 1.0
                working[second_id]["y"] = _clamp_position(working[second_id]["y"] + (push_y * direction), 0.0, max(0.0, canvas_height - _coerce_float(second.get("height"), default=1.0)))
            moved = True
        if not moved:
            break
    return working


def _solve_strategy_positions(
    strategy: str,
    elements: list[dict[str, Any]],
    *,
    canvas_width: float,
    canvas_height: float,
    gap: float,
    preserve_order: bool,
    axis: str,
) -> dict[str, dict[str, float]]:
    if strategy == "grid":
        return _solve_grid_positions(elements, canvas_width=canvas_width, canvas_height=canvas_height, gap=gap, preserve_order=preserve_order)
    if strategy == "linear":
        return _solve_linear_positions(elements, canvas_width=canvas_width, canvas_height=canvas_height, gap=gap, preserve_order=preserve_order, axis=axis)
    if strategy == "radial":
        return _solve_radial_positions(elements, canvas_width=canvas_width, canvas_height=canvas_height, gap=gap, preserve_order=preserve_order)
    if strategy == "greedy":
        return _solve_greedy_positions(elements, canvas_width=canvas_width, canvas_height=canvas_height, gap=gap, preserve_order=preserve_order)
    return {}


def _strategy_attempt_order(preferred_strategy: str) -> list[str]:
    order = ["direct", preferred_strategy, "grid", "linear", "radial", "greedy"]
    seen: set[str] = set()
    unique: list[str] = []
    for item in order:
        if item not in _ALLOWED_SOLVER_STRATEGIES or item in seen:
            continue
        seen.add(item)
        unique.append(item)
    return unique


def _board_delta_operations(
    original_board: dict[str, Any],
    next_board: dict[str, Any],
    *,
    summary_prefix: str,
) -> list[dict[str, Any]]:
    def _stable_op_id(kind: str, element_id: str) -> str:
        return f"op_{sha256(f'{kind}:{element_id}'.encode('utf-8')).hexdigest()[:10]}"

    original = normalize_board_state(original_board)
    updated = normalize_board_state(next_board)
    original_map = {element["id"]: element for element in original["elements"]}
    updated_map = {element["id"]: element for element in updated["elements"]}
    operations: list[dict[str, Any]] = []
    for element_id in sorted(original_map):
        if element_id not in updated_map:
            operations.append({"operation_id": _stable_op_id("delete", element_id), "type": "delete", "summary": f"{summary_prefix} remove {element_id}", "element_id": element_id})
    for element_id, element in updated_map.items():
        if element_id not in original_map:
            operations.append({"operation_id": _stable_op_id("add", element_id), "type": "add", "summary": f"{summary_prefix} add {element_id}", "element": deepcopy(element)})
            continue
        before = original_map[element_id]
        patch: dict[str, Any] = {}
        for field in ("x", "y", "width", "height", "text", "fill", "stroke", "stroke_width", "shape_kind", "group_id", "points", "connection_refs"):
            if before.get(field) != element.get(field):
                patch[field] = deepcopy(element.get(field))
        if patch:
            operations.append({"operation_id": _stable_op_id("update", element_id), "type": "update", "summary": f"{summary_prefix} adjust {element_id}", "element_id": element_id, "patch": patch})
    return operations


def certify_workspace_proposal(
    *,
    board_state: dict[str, Any],
    operations: list[dict[str, Any]],
    intent_schema: dict[str, Any],
    proposal_kind: str,
    canvas_width: float = _DEFAULT_CANVAS_WIDTH,
    canvas_height: float = _DEFAULT_CANVAS_HEIGHT,
) -> dict[str, Any]:
    normalized_board = normalize_board_state(board_state)
    normalized_ops = validate_and_normalize_operations(operations, normalized_board)
    normalized_intent = normalize_workspace_intent_schema(
        intent_schema,
        operations=normalized_ops,
        board_state=normalized_board,
        operator_note="",
        discussion_response="",
        assessment_only=(proposal_kind != "mutation_bearing"),
    )
    if proposal_kind != "mutation_bearing":
        return {
            "operations": normalized_ops,
            "intent_schema": normalized_intent,
            "geometry_status": "certified",
            "constraint_summary": "no_geometry_mutation",
            "solver_strategy_used": "direct",
            "validation_result": {
                "status": "valid",
                "violations": {"overlap_pairs": [], "contact_pairs": [], "gap_pairs": [], "out_of_bounds": []},
                "summary": {"violation_count": 0, "severity": "none", "overlap_count": 0, "contact_count": 0, "gap_count": 0, "out_of_bounds_count": 0},
            },
            "solver_diagnostics": {"attempted_strategies": ["direct"], "failed_strategies": []},
        }
    target_ids = normalized_intent["target_element_ids"]
    minimum_gap = normalized_intent["minimum_gap"]
    candidate_board = apply_operations_to_board(normalized_board, normalized_ops)
    direct_validation = validate_board_geometry(
        candidate_board,
        target_element_ids=target_ids,
        minimum_gap=minimum_gap,
        canvas_width=canvas_width,
        canvas_height=canvas_height,
    )
    attempted = ["direct"]
    failed: list[dict[str, Any]] = []
    if direct_validation["status"] == "valid":
        return {
            "operations": normalized_ops,
            "intent_schema": normalized_intent,
            "geometry_status": "certified",
            "constraint_summary": "satisfied",
            "solver_strategy_used": "direct",
            "validation_result": direct_validation,
            "solver_diagnostics": {"attempted_strategies": attempted, "failed_strategies": failed},
        }
    failed.append({"strategy": "direct", "validation_result": direct_validation})
    if not target_ids:
        return {
            "operations": normalized_ops,
            "intent_schema": normalized_intent,
            "geometry_status": "invalid",
            "constraint_summary": "violated",
            "solver_strategy_used": "direct",
            "validation_result": direct_validation,
            "solver_diagnostics": {"attempted_strategies": attempted, "failed_strategies": failed},
        }
    target_elements = _solver_target_elements(candidate_board, target_ids, preserve_order=normalized_intent["preserve_order"])
    repaired_board = candidate_board
    repaired_strategy = "direct"
    repaired_validation = direct_validation
    for strategy in _strategy_attempt_order(normalized_intent["preferred_strategy"]):
        if strategy == "direct":
            continue
        attempted.append(strategy)
        positions = _solve_strategy_positions(
            strategy,
            target_elements,
            canvas_width=canvas_width,
            canvas_height=canvas_height,
            gap=minimum_gap,
            preserve_order=normalized_intent["preserve_order"],
            axis=normalized_intent["axis"],
        )
        candidate_repair = _apply_positions_to_board(candidate_board, positions)
        validation = validate_board_geometry(
            candidate_repair,
            target_element_ids=target_ids,
            minimum_gap=minimum_gap,
            canvas_width=canvas_width,
            canvas_height=canvas_height,
        )
        if validation["status"] == "valid":
            repaired_board = candidate_repair
            repaired_strategy = strategy
            repaired_validation = validation
            break
        failed.append({"strategy": strategy, "validation_result": validation})
    if repaired_strategy != "direct":
        repaired_operations = _board_delta_operations(normalized_board, repaired_board, summary_prefix=f"Solver {repaired_strategy}")
        final_operations = validate_and_normalize_operations(repaired_operations, normalized_board)
        return {
            "operations": final_operations,
            "intent_schema": normalized_intent,
            "geometry_status": "repaired",
            "constraint_summary": "satisfied",
            "solver_strategy_used": repaired_strategy,
            "validation_result": repaired_validation,
            "solver_diagnostics": {"attempted_strategies": attempted, "failed_strategies": failed},
        }
    return {
        "operations": normalized_ops,
        "intent_schema": normalized_intent,
        "geometry_status": "invalid",
        "constraint_summary": "violated",
        "solver_strategy_used": "direct",
        "validation_result": direct_validation,
        "solver_diagnostics": {"attempted_strategies": attempted, "failed_strategies": failed},
    }


def build_workspace_submission_prompt(
    *,
    submission_id: str,
    board_state: dict[str, Any],
    board_state_hash_value: str,
    board_snapshot_ref: str,
    board_snapshot_sha256: str,
    discussion_context: list[dict[str, str]],
    operator_note: str,
) -> str:
    discussion_window = discussion_context[-8:]
    board_summary = {
        "submission_id": submission_id,
        "board_state_hash": board_state_hash_value,
        "board_snapshot_ref": board_snapshot_ref,
        "board_snapshot_sha256": board_snapshot_sha256,
        "element_count": len(board_state.get("elements") or []),
        "elements": board_state.get("elements") or [],
        "discussion_context": discussion_window,
        "operator_note": operator_note,
    }
    return (
        "You are Calyx Workspace v0 operating in proposal mode.\n"
        "Return strict JSON only with this shape:\n"
        "{\n"
        '  "discussion_response": "short explanation for the operator",\n'
        '  "operations": [\n'
        "    {\n"
        '      "type": "add|update|delete|group|relabel",\n'
        '      "summary": "why this change helps",\n'
        '      "element": {...},\n'
        '      "element_id": "existing id when relevant",\n'
        '      "patch": {...},\n'
        '      "member_ids": ["..."],\n'
        '      "group_id": "optional group id",\n'
        '      "text": "replacement text for relabel"\n'
        "    }\n"
        "  ]\n"
        "}\n"
        "Rules:\n"
        "- Candidate operations only. Nothing is auto-approved.\n"
        "- Use only element types text, shape, stroke.\n"
        "- Use shape_kind rect or ellipse for shapes.\n"
        "- Keep operations bounded, concrete, and spatially useful.\n"
        "- If no canvas change is justified, return an empty operations array.\n"
        "- No markdown fences. No prose outside the JSON object.\n\n"
        f"Hybrid submission payload:\n{json.dumps(board_summary, ensure_ascii=False)}"
    )


def _extract_json_candidates(raw_text: str) -> list[str]:
    candidates: list[str] = []
    stripped = raw_text.strip()
    if stripped:
        candidates.append(stripped)
    for marker in ("```json", "```"):
        start = stripped.find(marker)
        if start >= 0:
            start_index = start + len(marker)
            end_index = stripped.find("```", start_index)
            if end_index > start_index:
                candidates.append(stripped[start_index:end_index].strip())
    brace_start = stripped.find("{")
    if brace_start >= 0:
        depth = 0
        for index in range(brace_start, len(stripped)):
            char = stripped[index]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    candidates.append(stripped[brace_start : index + 1])
                    break
    return [candidate for candidate in candidates if candidate]


def parse_workspace_model_response(raw_text: str) -> dict[str, Any]:
    if not isinstance(raw_text, str) or not raw_text.strip():
        raise ValueError("empty_model_reply")
    for candidate in _extract_json_candidates(raw_text):
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if not isinstance(parsed, dict):
            continue
        discussion_response = parsed.get("discussion_response")
        operations = parsed.get("operations")
        if not isinstance(discussion_response, str):
            discussion_response = parsed.get("discussion") or parsed.get("reply") or parsed.get("message")
        if not isinstance(discussion_response, str):
            continue
        if not isinstance(operations, list):
            operations = parsed.get("candidate_markup") or parsed.get("candidate_operations")
        if not isinstance(operations, list):
            continue
        return {
            "discussion_response": discussion_response.strip(),
            "operations": operations,
            "raw": parsed,
        }
    raise ValueError("malformed_model_output")


def validate_workspace_proposal_response(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("malformed_model_output")
    discussion_response = payload.get("discussion_response")
    operations = payload.get("operations")
    proposal_tier = payload.get("proposal_tier")
    tier_label = payload.get("tier_label")
    tier_rationale = payload.get("tier_rationale")
    confidence_summary = payload.get("confidence_summary")
    proposal_kind = payload.get("proposal_kind")
    quality_signal = payload.get("quality_signal")
    selected_route = payload.get("selected_route")
    actual_route = payload.get("actual_route")
    intent_schema = payload.get("intent_schema")
    if (
        not isinstance(discussion_response, str)
        or not isinstance(operations, list)
        or not isinstance(proposal_tier, int)
        or proposal_tier < 0
        or proposal_tier > 4
        or not isinstance(tier_label, str)
        or not tier_label.strip()
        or not isinstance(tier_rationale, str)
        or not tier_rationale.strip()
        or not isinstance(confidence_summary, str)
        or not confidence_summary.strip()
        or not isinstance(proposal_kind, str)
        or proposal_kind not in _ALLOWED_PROPOSAL_KINDS
        or not isinstance(quality_signal, str)
        or not quality_signal.strip()
        or not isinstance(selected_route, str)
        or not selected_route.strip()
        or (actual_route is not None and not isinstance(actual_route, str))
        or not isinstance(intent_schema, dict)
    ):
        raise ValueError("malformed_model_output")
    return {
        "discussion_response": discussion_response.strip(),
        "operations": operations,
        "proposal_tier": proposal_tier,
        "tier_label": tier_label.strip(),
        "tier_rationale": tier_rationale.strip(),
        "confidence_summary": confidence_summary.strip(),
        "proposal_kind": proposal_kind,
        "quality_signal": quality_signal.strip(),
        "selected_route": selected_route.strip(),
        "actual_route": (actual_route or "").strip() or selected_route.strip(),
        "provider_used": payload.get("provider_used"),
        "intent_schema": intent_schema,
    }


def _apply_patch_to_element(element: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(element)
    for key in (
        "x",
        "y",
        "width",
        "height",
        "text",
        "fill",
        "stroke",
        "stroke_width",
        "shape_kind",
        "group_id",
        "points",
        "connection_refs",
    ):
        if key in patch:
            merged[key] = patch[key]
    if "shape_kind" in patch:
        merged["shape"] = {"kind": patch["shape_kind"]}
    return _normalize_element(merged, fallback_order=_coerce_int(merged.get("order"), default=0))


def validate_and_normalize_operations(
    operations: Any,
    board_state: dict[str, Any],
) -> list[dict[str, Any]]:
    allowed_patch_fields = {"x", "y", "width", "height", "text", "fill", "stroke", "stroke_width", "shape_kind", "group_id", "points", "connection_refs"}
    if not isinstance(operations, list):
        raise ValueError("operations_must_be_list")
    working_board = normalize_board_state(board_state)
    normalized: list[dict[str, Any]] = []
    for index, raw_operation in enumerate(operations):
        if not isinstance(raw_operation, dict):
            raise ValueError("operation_must_be_object")
        operation_type = str(raw_operation.get("type") or "").strip().lower()
        if operation_type not in _ALLOWED_OPERATION_TYPES:
            raise ValueError("unsupported_operation_type")
        operation_id = str(raw_operation.get("operation_id") or f"op_{uuid.uuid4().hex[:10]}").strip()
        summary = str(raw_operation.get("summary") or f"{operation_type} candidate").strip()
        operation: dict[str, Any] = {
            "operation_id": operation_id,
            "type": operation_type,
            "summary": summary,
        }
        if operation_type == "add":
            element = _normalize_element(raw_operation.get("element"), fallback_order=len(working_board["elements"]) + index)
            if any(existing["id"] == element["id"] for existing in working_board["elements"]):
                raise ValueError("duplicate_element_id")
            operation["element"] = element
            working_board["elements"].append(element)
            normalized.append(operation)
            continue
        element_id = str(raw_operation.get("element_id") or "").strip()
        if operation_type in {"update", "delete", "relabel"} and not element_id:
            raise ValueError("element_id_required")
        if operation_type in {"update", "delete", "relabel"}:
            target = next((element for element in working_board["elements"] if element["id"] == element_id), None)
            if target is None:
                raise ValueError("element_not_found")
        if operation_type == "update":
            patch = raw_operation.get("patch")
            if not isinstance(patch, dict) or not patch:
                raise ValueError("patch_required")
            if not any(key in allowed_patch_fields for key in patch):
                raise ValueError("unsupported_patch_fields")
            updated = _apply_patch_to_element(target, patch)
            for idx, element in enumerate(working_board["elements"]):
                if element["id"] == element_id:
                    working_board["elements"][idx] = updated
                    break
            operation["element_id"] = element_id
            operation["patch"] = patch
            normalized.append(operation)
            continue
        if operation_type == "delete":
            working_board["elements"] = [element for element in working_board["elements"] if element["id"] != element_id]
            operation["element_id"] = element_id
            normalized.append(operation)
            continue
        if operation_type == "group":
            member_ids = raw_operation.get("member_ids")
            if not isinstance(member_ids, list) or len(member_ids) < 2:
                raise ValueError("member_ids_required")
            member_ids = [str(member_id).strip() for member_id in member_ids if str(member_id).strip()]
            if len(member_ids) < 2:
                raise ValueError("member_ids_required")
            if not all(any(element["id"] == member_id for element in working_board["elements"]) for member_id in member_ids):
                raise ValueError("group_member_missing")
            group_id = str(raw_operation.get("group_id") or f"group_{uuid.uuid4().hex[:8]}").strip()
            for element in working_board["elements"]:
                if element["id"] in member_ids:
                    element["group_id"] = group_id
            operation["group_id"] = group_id
            operation["member_ids"] = member_ids
            operation["label"] = str(raw_operation.get("label") or "").strip()
            normalized.append(operation)
            continue
        replacement_text = str(raw_operation.get("text") or "").strip()
        if not replacement_text:
            raise ValueError("replacement_text_required")
        for element in working_board["elements"]:
            if element["id"] == element_id:
                element["text"] = replacement_text
                break
        operation["element_id"] = element_id
        operation["text"] = replacement_text
        normalized.append(operation)
    return normalized


def apply_operations_to_board(
    board_state: dict[str, Any],
    operations: list[dict[str, Any]],
) -> dict[str, Any]:
    working_board = normalize_board_state(board_state)
    for operation in operations:
        operation_type = operation["type"]
        if operation_type == "add":
            working_board["elements"].append(deepcopy(operation["element"]))
            continue
        if operation_type == "update":
            for index, element in enumerate(working_board["elements"]):
                if element["id"] == operation["element_id"]:
                    working_board["elements"][index] = _apply_patch_to_element(element, operation["patch"])
                    break
            else:
                raise ValueError("element_not_found")
            continue
        if operation_type == "delete":
            next_elements = [element for element in working_board["elements"] if element["id"] != operation["element_id"]]
            if len(next_elements) == len(working_board["elements"]):
                raise ValueError("element_not_found")
            working_board["elements"] = next_elements
            continue
        if operation_type == "group":
            touched = 0
            for element in working_board["elements"]:
                if element["id"] in operation["member_ids"]:
                    element["group_id"] = operation["group_id"]
                    touched += 1
            if touched < len(operation["member_ids"]):
                raise ValueError("group_member_missing")
            continue
        if operation_type == "relabel":
            for element in working_board["elements"]:
                if element["id"] == operation["element_id"]:
                    element["text"] = operation["text"]
                    break
            else:
                raise ValueError("element_not_found")
            continue
    working_board["updated_at"] = _now_iso()
    working_board["elements"] = [
        _normalize_element(element, fallback_order=index)
        for index, element in enumerate(sorted(working_board["elements"], key=lambda item: (item.get("order", 0), item.get("id", ""))))
    ]
    return working_board
