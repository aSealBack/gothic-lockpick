"""Lockpick combination solver for Gothic 1 Remake.

Graph vertices are all positions (tuples of pin values, one per plate, each
within [1, SLOTS]). An edge p1 -> p2 exists if there is a Movement
(plate, side) that turns p1 into p2, taking plate connections into account.

Direction convention: side 'l' increases the plate value by 1, side 'r'
decreases it. A 'same' connection moves the dependent plate in the same
direction, 'opposite' — in the opposite one.

Example:
    python gothic_lockpick.py --start 3 5 2 4 1 --conn 1:3:same --conn 2:5:opposite
"""

import argparse
import heapq
from dataclasses import dataclass
from enum import Enum
from itertools import product
from typing import Optional

SLOTS = 7
PLATES = 5
TARGET = (4,) * PLATES

Position = tuple[int, ...]


class Direction(Enum):
    SAME = 'same'
    OPPOSITE = 'opposite'


class Side(Enum):
    LEFT = 'l'
    RIGHT = 'r'


@dataclass(frozen=True)
class Connection:
    plate: int  # dependent plate index (0-based)
    direction: Direction


@dataclass(frozen=True)
class Movement:
    plate: int  # moved plate index (0-based)
    side: Side


@dataclass(frozen=True)
class Edge:
    next: int
    move: Movement


Edges = list[list[Edge]]


def fill_vertices() -> list[Position]:
    return list(product(range(1, SLOTS + 1), repeat=PLATES))


def position_to_index(position: Position) -> int:
    """Index of the position in vertices: a position is a base-SLOTS number
    whose digits are (pin - 1)."""
    index = 0
    for pin in position:
        index = index * SLOTS + (pin - 1)
    return index


def apply_movement(
    position: Position,
    move: Movement,
    connections: list[list[Connection]],
) -> Optional[Position]:
    result = list(position)
    change = 1 if move.side is Side.LEFT else -1
    result[move.plate] += change
    for c in connections[move.plate]:
        diff = change * (1 if c.direction is Direction.SAME else -1)
        result[c.plate] += diff
    if all(1 <= pin <= SLOTS for pin in result):
        return tuple(result)
    return None


def fill_edges(
    vertices: list[Position],
    connections: list[list[Connection]],
) -> Edges:
    edges: Edges = []
    for v_pos in vertices:
        out: list[Edge] = []
        for plate in range(PLATES):
            for side in Side:
                move = Movement(plate=plate, side=side)
                next_pos = apply_movement(v_pos, move, connections)
                if next_pos is not None:
                    out.append(Edge(next=position_to_index(next_pos), move=move))
        edges.append(out)
    return edges


def run_dijkstra(edges: Edges, start: int, target: int) -> Optional[list[Movement]]:
    INF = float('inf')
    dist = [INF] * len(edges)
    prev: list[Optional[tuple[int, Movement]]] = [None] * len(edges)
    dist[start] = 0
    heap: list[tuple[int, int]] = [(0, start)]

    while heap:
        d, v = heapq.heappop(heap)
        if d > dist[v]:
            continue
        if v == target:
            break
        for edge in edges[v]:
            nd = d + 1  # every movement costs 1
            if nd < dist[edge.next]:
                dist[edge.next] = nd
                prev[edge.next] = (v, edge.move)
                heapq.heappush(heap, (nd, edge.next))

    if dist[target] == INF:
        return None

    path: list[Movement] = []
    v = target
    while v != start:
        step = prev[v]
        assert step is not None
        v, move = step
        path.append(move)
    path.reverse()
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Find the shortest movement sequence that opens the lock.',
        epilog="Plates are 1-indexed. Connection format: WHO:WHOM:same|opposite, "
               "e.g. --conn 1:3:same (moving plate 1 also moves plate 3 "
               "in the same direction).",
    )
    parser.add_argument(
        '--start', type=int, nargs=PLATES, required=True, metavar='PIN',
        help=f'starting position: {PLATES} values from 1 to {SLOTS}',
    )
    parser.add_argument(
        '--conn', action='append', default=[], metavar='A:B:DIR',
        help='plate connection (may be given multiple times)',
    )
    return parser.parse_args()


def parse_connections(raw: list[str]) -> list[list[Connection]]:
    connections: list[list[Connection]] = [[] for _ in range(PLATES)]
    for item in raw:
        parts = item.split(':')
        if len(parts) != 3:
            raise SystemExit(f'Invalid connection format: {item!r} (expected A:B:same|opposite)')
        src_s, dst_s, direction = parts
        try:
            src, dst = int(src_s), int(dst_s)
        except ValueError:
            raise SystemExit(f'Invalid connection format: {item!r} (plate numbers must be integers)')
        if not (1 <= src <= PLATES and 1 <= dst <= PLATES):
            raise SystemExit(f'Plate numbers in {item!r} must be from 1 to {PLATES}')
        if src == dst:
            raise SystemExit(f'A plate cannot be connected to itself: {item!r}')
        try:
            parsed_direction = Direction(direction)
        except ValueError:
            raise SystemExit(f'Connection direction in {item!r} must be same or opposite')
        connections[src - 1].append(Connection(plate=dst - 1, direction=parsed_direction))
    return connections


def main() -> None:
    args = parse_args()

    for pin in args.start:
        if not (1 <= pin <= SLOTS):
            raise SystemExit(f'Pin value {pin} is out of range [1, {SLOTS}]')
    start_position: Position = tuple(args.start)
    connections = parse_connections(args.conn)

    vertices = fill_vertices()
    edges = fill_edges(vertices, connections)

    path = run_dijkstra(edges, position_to_index(start_position), position_to_index(TARGET))

    if path is None:
        print('No solution: the target position is unreachable from the start.')
        raise SystemExit(1)

    if not path:
        print('The lock is already open: the starting position is the target.')
        return

    print(f'Solution in {len(path)} movements (l: value +1, r: value -1):')
    position = start_position
    for i, move in enumerate(path, 1):
        next_position = apply_movement(position, move, connections)
        assert next_position is not None
        side_name = 'left (l)' if move.side is Side.LEFT else 'right (r)'
        print(f'{i:3}. plate {move.plate + 1} {side_name}  ->  {list(next_position)}')
        position = next_position


if __name__ == '__main__':
    main()
