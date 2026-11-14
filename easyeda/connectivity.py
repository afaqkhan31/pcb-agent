
import json
import math

def distance(a, b):
    return math.hypot(a["x"] - b["x"], a["y"] - b["y"])


def point_to_segment(p, a, b):
    dx = b["x"] - a["x"]
    dy = b["y"] - a["y"]

    if dx == 0 and dy == 0:
        return distance(p, a)

    t = (
        (p["x"] - a["x"]) * dx
        + (p["y"] - a["y"]) * dy
    ) / (dx * dx + dy * dy)

    t = max(0.0, min(1.0, t))

    nearest = {
        "x": a["x"] + t * dx,
        "y": a["y"] + t * dy
    }

    return distance(p, nearest)


def tracks_touch(a, b):
    endpoints_a = [a["start"], a["end"]]
    endpoints_b = [b["start"], b["end"]]

    tolerance = (a["width"] + b["width"]) / 2

    for p in endpoints_a:
        if point_to_segment(p, b["start"], b["end"]) <= tolerance:
            return True

    for p in endpoints_b:
        if point_to_segment(p, a["start"], a["end"]) <= tolerance:
            return True

    return False


def check_connectivity(nets):
    results = {}

    for net_name, items in nets.items():
        pads = [
            x for x in items
            if x.get("pcbItemPrimitiveType") == "Pad"
        ]

        tracks = [
            x for x in items
            if x.get("pcbItemPrimitiveType") == "Track"
            and x.get("layerId") == 2
        ]

        nodes = tracks + pads
        graph = {i: set() for i in range(len(nodes))}

        for i, track_a in enumerate(tracks):
            for j in range(i + 1, len(tracks)):
                if tracks_touch(track_a, tracks[j]):
                    graph[i].add(j)
                    graph[j].add(i)

        for i, pad in enumerate(pads, start=len(tracks)):
            center = pad["center"]

            radius = max(
                pad.get("bottomWidth", 0),
                pad.get("bottomHeight", 0)
            ) / 2

            for j, track in enumerate(tracks):
                if point_to_segment(
                    center, track["start"], track["end"]
                ) <= radius + track["width"] / 2:
                    graph[i].add(j)
                    graph[j].add(i)

        visited = set()
        components = []

        for start in graph:
            if start in visited:
                continue

            stack = [start]
            visited.add(start)
            component = []

            while stack:
                current = stack.pop()
                component.append(current)

                for neighbour in graph[current]:
                    if neighbour not in visited:
                        visited.add(neighbour)
                        stack.append(neighbour)

            components.append(component)

        pad_components = set()

        for component_id, component in enumerate(components):
            if any(index >= len(tracks) for index in component):
                pad_components.add(component_id)

        connected = (
            len(components) == 1
            and len(pad_components) == 1
            and len(pads) > 0
            and len(tracks) > 0
        )

        results[net_name] = {
            "pads": len(pads),
            "tracks": len(tracks),
            "groups": len(components),
            "pad_groups": len(pad_components),
            "preliminary_connected": connected
        }

        print(
            f"\n{net_name}: {len(pads)} pads, "
            f"{len(tracks)} bottom-layer tracks"
        )
        print("  Connected copper groups:", len(components))
        print("  Groups containing pads:", len(pad_components))

        if connected:
            print("  Preliminary result: one connected network")
        else:
            print("  Result: connectivity needs inspection")

    return results


def main():
    with open(
        "output/pcb_connectivity.json",
        encoding="utf-8"
    ) as f:
        nets = json.load(f)

    check_connectivity(nets)


if __name__ == "__main__":
    main()
