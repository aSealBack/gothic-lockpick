"""Подборщик комбинаций для взлома замков в Gothic 1 Remake.

Вершины графа — все позиции (наборы значений пинов, по одному на пластину,
каждое в отрезке [1, SLOTS]). Ребро p1 -> p2 существует, если есть Movement
(plate, side), переводящий p1 в p2 с учётом связей пластин.

Соглашение о направлениях: side 'l' увеличивает значение пластины на 1,
side 'r' — уменьшает. Связь 'same' двигает зависимую пластину в ту же сторону,
'opposite' — в противоположную.

Пример запуска:
    python gothic_lockpick.py --start 3 5 2 4 1 --conn 1:3:same --conn 2:5:opposite
"""

import argparse
import heapq
import sys
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
    plate: int  # индекс зависимой пластины (0-based)
    direction: Direction


@dataclass(frozen=True)
class Movement:
    plate: int  # индекс двигаемой пластины (0-based)
    side: Side


@dataclass(frozen=True)
class Edge:
    next: int
    move: Movement


Edges = list[list[Edge]]


def fill_vertices() -> list[Position]:
    return list(product(range(1, SLOTS + 1), repeat=PLATES))


def position_to_index(position: Position) -> int:
    """Номер позиции в vertices: позиция — это число в системе счисления
    с основанием SLOTS, где цифры — (pin - 1)."""
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
            nd = d + 1  # каждое движение стоит 1
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
        description='Поиск кратчайшей последовательности движений для взлома замка.',
        epilog="Пластины в аргументах нумеруются с 1. "
               "Формат связи: КТО:КОГО:same|opposite, например --conn 1:3:same "
               "(движение пластины 1 двигает пластину 3 в ту же сторону).",
    )
    parser.add_argument(
        '--start', type=int, nargs=PLATES, required=True, metavar='PIN',
        help=f'начальная позиция: {PLATES} значений от 1 до {SLOTS}',
    )
    parser.add_argument(
        '--conn', action='append', default=[], metavar='A:B:DIR',
        help='связь пластин (можно указывать несколько раз)',
    )
    return parser.parse_args()


def parse_connections(raw: list[str]) -> list[list[Connection]]:
    connections: list[list[Connection]] = [[] for _ in range(PLATES)]
    for item in raw:
        parts = item.split(':')
        if len(parts) != 3:
            raise SystemExit(f'Неверный формат связи: {item!r} (ожидается A:B:same|opposite)')
        src_s, dst_s, direction = parts
        try:
            src, dst = int(src_s), int(dst_s)
        except ValueError:
            raise SystemExit(f'Неверный формат связи: {item!r} (номера пластин должны быть числами)')
        if not (1 <= src <= PLATES and 1 <= dst <= PLATES):
            raise SystemExit(f'Номера пластин в {item!r} должны быть от 1 до {PLATES}')
        if src == dst:
            raise SystemExit(f'Пластина не может быть связана сама с собой: {item!r}')
        try:
            parsed_direction = Direction(direction)
        except ValueError:
            raise SystemExit(f'Направление связи в {item!r} должно быть same или opposite')
        connections[src - 1].append(Connection(plate=dst - 1, direction=parsed_direction))
    return connections


def main() -> None:
    # Windows-консоль может использовать cp1252/cp866 — кириллица в них не печатается
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

    args = parse_args()

    for pin in args.start:
        if not (1 <= pin <= SLOTS):
            raise SystemExit(f'Значение пина {pin} вне отрезка [1, {SLOTS}]')
    start_position: Position = tuple(args.start)
    connections = parse_connections(args.conn)

    vertices = fill_vertices()
    edges = fill_edges(vertices, connections)

    path = run_dijkstra(edges, position_to_index(start_position), position_to_index(TARGET))

    if path is None:
        print('Решения нет: целевая позиция недостижима из начальной.')
        raise SystemExit(1)

    if not path:
        print('Замок уже открыт: начальная позиция совпадает с целевой.')
        return

    print(f'Решение за {len(path)} движений (l: значение +1, r: значение -1):')
    position = start_position
    for i, move in enumerate(path, 1):
        next_position = apply_movement(position, move, connections)
        assert next_position is not None
        side_name = 'влево (l)' if move.side is Side.LEFT else 'вправо (r)'
        print(f'{i:3}. пластина {move.plate + 1} {side_name}  ->  {list(next_position)}')
        position = next_position


if __name__ == '__main__':
    main()
