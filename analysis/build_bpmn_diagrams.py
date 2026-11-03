"""Build readable synthetic BPMN drafts for import into demo.bpmn.io."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NS = {
    "bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL",
    "bpmndi": "http://www.omg.org/spec/BPMN/20100524/DI",
    "dc": "http://www.omg.org/spec/DD/20100524/DC",
    "di": "http://www.omg.org/spec/DD/20100524/DI",
}
for prefix, uri in NS.items():
    ET.register_namespace(prefix, uri)
Q = lambda prefix, tag: f"{{{NS[prefix]}}}{tag}"

LANES = [
    ("requester", "Requesting team", 0),
    ("desk", "Access Service Desk", 1),
    ("line", "Line Management", 2),
    ("risk", "Access Risk and Controls", 3),
    ("owners", "Application Owners", 4),
    ("iam", "IAM Engineering", 5),
]
Y = {key: 80 + i * 110 for key, _, i in LANES}
NODE_H = 60
TASK_W = 150
GW = 54
EVENT = 38


def build(name: str, width: int, nodes: list[dict], flows: list[tuple], lanes: dict, annotation: str | None = None) -> Path:
    definitions = ET.Element(Q("bpmn", "definitions"), {
        "id": f"Definitions_{name}",
        "targetNamespace": "https://example.invalid/access-flow-synthetic",
        "exporter": "Codex draft for demo.bpmn.io",
        "exporterVersion": "1.0",
    })
    process = ET.SubElement(definitions, Q("bpmn", "process"), {
        "id": f"Process_{name}", "name": "Access provisioning (synthetic)", "isExecutable": "false"
    })
    lane_set = ET.SubElement(process, Q("bpmn", "laneSet"), {"id": f"LaneSet_{name}"})
    for key, lane_name, _ in LANES:
        lane = ET.SubElement(lane_set, Q("bpmn", "lane"), {"id": f"Lane_{name}_{key}", "name": lane_name})
        for node_id in lanes.get(key, []):
            ET.SubElement(lane, Q("bpmn", "flowNodeRef")).text = node_id

    node_types = {}
    for node in nodes:
        kind = node["kind"]
        element = ET.SubElement(process, Q("bpmn", kind), {
            "id": node["id"], "name": node.get("name", "")
        })
        if kind == "exclusiveGateway":
            default_direction = "Converging" if node["id"].endswith("_merge") else "Diverging"
            element.set("gatewayDirection", node.get("direction", default_direction))
        if kind == "startEvent":
            element.set("isInterrupting", "true")
            element.set("parallelMultiple", "false")
        node_types[node["id"]] = kind
        node["xml"] = element

    flow_ids = []
    for i, flow in enumerate(flows, 1):
        source, target, label, route = flow
        fid = f"Flow_{name}_{i}"
        attrs = {"id": fid, "sourceRef": source, "targetRef": target}
        if label:
            attrs["name"] = label
        ET.SubElement(process, Q("bpmn", "sequenceFlow"), attrs)
        ET.SubElement(nodes_by_id[source]["xml"], Q("bpmn", "outgoing")).text = fid
        ET.SubElement(nodes_by_id[target]["xml"], Q("bpmn", "incoming")).text = fid
        flow_ids.append((fid, source, target, route))

    annotation_node = None
    if annotation:
        text = ET.SubElement(process, Q("bpmn", "textAnnotation"), {"id": f"Annotation_{name}"})
        ET.SubElement(text, Q("bpmn", "text")).text = annotation
        annotation_node = text

    collaboration = ET.SubElement(definitions, Q("bpmn", "collaboration"), {"id": f"Collaboration_{name}"})
    ET.SubElement(collaboration, Q("bpmn", "participant"), {
        "id": f"Participant_{name}", "name": "Access provisioning (synthetic)", "processRef": process.attrib["id"]
    })

    diagram = ET.SubElement(definitions, Q("bpmndi", "BPMNDiagram"), {"id": f"Diagram_{name}"})
    plane = ET.SubElement(diagram, Q("bpmndi", "BPMNPlane"), {
        "id": f"Plane_{name}", "bpmnElement": collaboration.attrib["id"]
    })
    add_shape(plane, f"Participant_{name}", 50, 40, width - 100, 660, isHorizontal="true")
    for key, _, idx in LANES:
        add_shape(plane, f"Lane_{name}_{key}", 50, 40 + idx * 110, width - 100, 110, isHorizontal="true")
    for node in nodes:
        x, y, w, h = node["x"], node["y"], node.get("w", TASK_W), node.get("h", NODE_H)
        add_shape(plane, node["id"], x, y, w, h, isExpanded="true" if node["kind"] == "participant" else None)
    if annotation_node is not None:
        add_shape(plane, annotation_node.attrib["id"], width - 650, 715, 580, 70)
    for fid, source, target, route in flow_ids:
        sx, sy, sw, sh = box[source]
        tx, ty, tw, th = box[target]
        start = (sx + sw, sy + sh / 2)
        end = (tx, ty + th / 2)
        if route == "top":
            points = [start, (start[0] + 30, start[1]), (start[0] + 30, 48), (end[0] - 30, 48), (end[0] - 30, end[1]), end]
        elif route == "bottom":
            points = [start, (start[0] + 25, start[1]), (start[0] + 25, 735), (end[0] - 25, 735), (end[0] - 25, end[1]), end]
        elif route == "direct":
            points = [start, end]
        else:
            mid = (start[0] + end[0]) / 2
            points = [start, (mid, start[1]), (mid, end[1]), end]
        edge = ET.SubElement(plane, Q("bpmndi", "BPMNEdge"), {"id": f"{fid}_di", "bpmnElement": fid})
        for x, y in points:
            ET.SubElement(edge, Q("di", "waypoint"), {"x": str(round(x)), "y": str(round(y))})
    path = ROOT / "lean" / f"{name}.bpmn"
    ET.indent(definitions, space="  ")
    ET.ElementTree(definitions).write(path, encoding="utf-8", xml_declaration=True)
    return path


def add_shape(plane, element_id: str, x: float, y: float, w: float, h: float, **attrs):
    shape_attrs = {"id": f"{element_id}_di", "bpmnElement": element_id}
    shape_attrs.update({k: v for k, v in attrs.items() if v is not None})
    shape = ET.SubElement(plane, Q("bpmndi", "BPMNShape"), shape_attrs)
    ET.SubElement(shape, Q("dc", "Bounds"), {"x": str(round(x)), "y": str(round(y)), "width": str(round(w)), "height": str(round(h))})


def make_nodes(prefix: str, specs: list[tuple]) -> tuple[list[dict], dict[str, list[str]]]:
    global nodes_by_id, box
    nodes_by_id, box = {}, {}
    nodes, lanes = [], {key: [] for key, _, _ in LANES}
    for ident, kind, label, lane, x, w, h in specs:
        height = h or (GW if "Gateway" in kind else EVENT if kind.endswith("Event") else NODE_H)
        width = w or (GW if "Gateway" in kind else EVENT if kind.endswith("Event") else TASK_W)
        y = Y[lane] + (NODE_H - height) / 2
        node = {"id": f"{prefix}_{ident}", "kind": kind, "name": label, "x": x, "y": y, "w": width, "h": height}
        nodes.append(node)
        nodes_by_id[node["id"]] = node
        box[node["id"]] = (x, y, width, height)
        lanes[lane].append(node["id"])
    return nodes, lanes


def f(a, b, label="", route=""):
    return (a, b, label, route)


def main():
    A = "as_is"
    specs = [
        ("start", "startEvent", "Start", "requester", 90, None, None),
        ("merge", "exclusiveGateway", "", "requester", 170, None, None),
        ("s1", "task", "1 Submit request", "requester", 250, None, None),
        ("s2", "task", "2 Validate request", "desk", 460, None, None),
        ("g2", "exclusiveGateway", "Information complete?", "desk", 650, None, None),
        ("s3", "userTask", "3 Line manager approval", "line", 770, None, None),
        ("g3", "exclusiveGateway", "Information complete?", "line", 970, None, None),
        ("s4", "task", "4 SoD / access-risk check", "risk", 1090, None, None),
        ("s5", "userTask", "5 Entitlement owner approval", "owners", 1300, None, None),
        ("g5", "exclusiveGateway", "Information complete?", "owners", 1500, None, None),
        ("s6", "task", "6 Provision access", "iam", 1620, None, None),
        ("s7", "task", "7 Confirm access works", "requester", 1840, None, None),
        ("g7", "exclusiveGateway", "Access works?", "requester", 2040, None, None),
        ("s8", "task", "8 Close request", "desk", 2160, None, None),
        ("end", "endEvent", "End", "desk", 2380, None, None),
    ]
    nodes, lanes = make_nodes(A, specs)
    p=lambda k:f"{A}_{k}"
    flows = [f(p("start"),p("merge")),f(p("merge"),p("s1")),f(p("s1"),p("s2")),f(p("s2"),p("g2")),
      f(p("g2"),p("s3"),"Yes"),f(p("g2"),p("merge"),"No","top"),f(p("s3"),p("g3")),
      f(p("g3"),p("s4"),"Yes"),f(p("g3"),p("merge"),"No","top"),f(p("s4"),p("s5")),f(p("s5"),p("g5")),
      f(p("g5"),p("s6"),"Yes"),f(p("g5"),p("merge"),"No","top"),f(p("s6"),p("s7")),f(p("s7"),p("g7")),
      f(p("g7"),p("s8"),"Yes"),f(p("g7"),p("s6"),"No","bottom"),f(p("s8"),p("end"))]
    build(A, 2520, nodes, flows, lanes)

    A = "to_be"
    specs = [
        ("start", "startEvent", "Start", "requester", 70, None, None),
        ("merge", "exclusiveGateway", "", "requester", 135, None, None),
        ("s1", "task", "1 Submit request", "requester", 210, None, None),
        ("bot", "serviceTask", "Intake validation bot", "desk", 395, None, None),
        ("bot_g", "exclusiveGateway", "Valid?", "desk", 585, None, None),
        ("s2", "task", "2 Validate request", "desk", 690, None, None),
        ("g2", "exclusiveGateway", "Information complete?", "desk", 870, None, None),
        ("triage", "serviceTask", "Triage recommendation (model)", "line", 980, None, None),
        ("priv", "exclusiveGateway", "Privileged?", "line", 1200, None, None),
        ("s3", "userTask", "3 Line manager approval", "line", 1310, None, None),
        ("g3", "exclusiveGateway", "Information complete?", "line", 1490, None, None),
        ("s4", "task", "4 SoD / access-risk check", "risk", 1600, None, None),
        ("s5", "userTask", "5 Entitlement owner approval", "owners", 1800, None, None),
        ("g5", "exclusiveGateway", "Information complete?", "owners", 1990, None, None),
        ("priv2", "exclusiveGateway", "Second approval required?", "owners", 2100, None, None),
        ("second", "userTask", "Second approver confirmation", "owners", 2210, None, None),
        ("s6", "task", "6 Provision access", "iam", 2420, None, None),
        ("s7", "task", "7 Confirm access works", "requester", 2630, None, None),
        ("g7", "exclusiveGateway", "Access works?", "requester", 2810, None, None),
        ("s8", "task", "8 Close request", "desk", 2920, None, None),
        ("end", "endEvent", "End", "desk", 3130, None, None),
    ]
    nodes, lanes = make_nodes(A, specs)
    p=lambda k:f"{A}_{k}"
    flows = [f(p("start"),p("merge")),f(p("merge"),p("s1")),f(p("s1"),p("bot")),f(p("bot"),p("bot_g")),
      f(p("bot_g"),p("s2"),"Valid"),f(p("bot_g"),p("merge"),"Invalid","top"),f(p("s2"),p("g2")),
      f(p("g2"),p("triage"),"Yes"),f(p("g2"),p("merge"),"No","top"),f(p("triage"),p("priv")),
      f(p("priv"),p("s3"),"Privileged"),f(p("priv"),p("s4"),"Not privileged"),f(p("s3"),p("g3")),
      f(p("g3"),p("s4"),"Yes"),f(p("g3"),p("merge"),"No","top"),f(p("s4"),p("s5")),f(p("s5"),p("g5")),
      f(p("g5"),p("priv2"),"Yes"),f(p("g5"),p("merge"),"No","top"),f(p("priv2"),p("second"),"Yes"),
      f(p("priv2"),p("s6"),"No"),f(p("second"),p("s6")),f(p("s6"),p("s7")),f(p("s7"),p("g7")),
      f(p("g7"),p("s8"),"Yes"),f(p("g7"),p("s6"),"No","bottom"),f(p("s8"),p("end"))]
    build(A, 3270, nodes, flows, lanes, "Model recommends only; human decides; blocked attempts logged")


if __name__ == "__main__":
    main()
