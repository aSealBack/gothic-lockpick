"""Lockpick combination solver for Gothic 1 Remake.

Graph vertices are all positions (tuples of pin values, one per plate, each
within [1, SLOTS]). An edge p1 -> p2 exists if there is a Movement
(plate, side) that turns p1 into p2, taking plate connections into account.
The graph is never materialized: BFS generates neighbors on the fly and
stops as soon as the target is reached.

Direction convention: side 'l' increases the plate value by 1, side 'r'
decreases it. A 'same' connection moves the dependent plate in the same
direction, 'opposite' — in the opposite one.

The number of plates is variable and is inferred from the --start values.

Example:
    python gothic_lockpick.py --start 3 5 2 4 1 --conn 1:3:same --conn 2:5:opposite
"""

import argparse
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Optional

SLOTS = 7
TARGET_PIN = 4

Position = tuple[int, ...]


def target_position(plates: int) -> Position:
    return (TARGET_PIN,) * plates


class Direction(Enum):
    SAME = 'same'
    OPPOSITE = 'opposite'


class Side(Enum):
    LEFT = 'l'
    RIGHT = 'r'


@dataclass(frozen=True)
class Connection:
    plate: int  # 0-based
    direction: Direction


@dataclass(frozen=True)
class Movement:
    plate: int  # 0-based
    side: Side


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


def move_deltas(
    plates: int,
    connections: list[list[Connection]],
) -> list[tuple[Movement, tuple[int, ...]]]:
    """Every possible movement paired with the pin change it causes on each
    plate (the moved plate itself plus its connections)."""
    moves: list[tuple[Movement, tuple[int, ...]]] = []
    for plate in range(plates):
        for side in Side:
            change = 1 if side is Side.LEFT else -1
            deltas = [0] * plates
            deltas[plate] += change
            for c in connections[plate]:
                deltas[c.plate] += change * (1 if c.direction is Direction.SAME else -1)
            moves.append((Movement(plate=plate, side=side), tuple(deltas)))
    return moves


def solve(
    start: Position,
    target: Position,
    connections: list[list[Connection]],
) -> Optional[list[Movement]]:
    """Shortest movement sequence from start to target (BFS: every movement
    costs 1). Returns [] if already solved, None if unreachable."""
    moves = move_deltas(len(start), connections)
    prev: dict[Position, Optional[tuple[Position, Movement]]] = {start: None}
    queue = deque([start])

    while queue:
        position = queue.popleft()
        if position == target:
            break
        for move, deltas in moves:
            next_position = tuple(pin + d for pin, d in zip(position, deltas))
            if (
                next_position not in prev
                and min(next_position) >= 1
                and max(next_position) <= SLOTS
            ):
                prev[next_position] = (position, move)
                queue.append(next_position)

    if target not in prev:
        return None

    path: list[Movement] = []
    position = target
    while (step := prev[position]) is not None:
        position, move = step
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
        '--start', type=int, nargs='+', required=True, metavar='PIN',
        help=f'starting position: one value from 1 to {SLOTS} per plate. '
             'The number of plates is inferred from the count',
    )
    parser.add_argument(
        '--conn', action='append', default=[], metavar='A:B:DIR',
        help='plate connection (may be given multiple times)',
    )
    return parser.parse_args()


def parse_connections(raw: list[str], plates: int) -> list[list[Connection]]:
    connections: list[list[Connection]] = [[] for _ in range(plates)]
    for item in raw:
        parts = item.split(':')
        if len(parts) != 3:
            raise SystemExit(f'Invalid connection format: {item!r} (expected A:B:same|opposite)')
        src_s, dst_s, direction = parts
        try:
            src, dst = int(src_s), int(dst_s)
        except ValueError:
            raise SystemExit(f'Invalid connection format: {item!r} (plate numbers must be integers)')
        if not (1 <= src <= plates and 1 <= dst <= plates):
            raise SystemExit(f'Plate numbers in {item!r} must be from 1 to {plates}')
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
    plates = len(start_position)
    connections = parse_connections(args.conn, plates)

    path = solve(start_position, target_position(plates), connections)

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
