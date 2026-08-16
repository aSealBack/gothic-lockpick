"""Tkinter GUI for the Gothic 1 Remake lockpick solver.

Uses gothic_lockpick.py as a library; run with:
    python gothic_lockpick_gui.py
"""

import tkinter as tk
from tkinter import ttk

from gothic_lockpick import (
    PLATES,
    SLOTS,
    TARGET,
    Connection,
    Direction,
    Side,
    apply_movement,
    fill_edges,
    fill_vertices,
    position_to_index,
    run_dijkstra,
)


class ConnectionMatrix:
    """Adjacency matrix of plate connections: cell (A, B) tells how moving
    plate A affects plate B."""

    NONE = 'none'
    OPTIONS = [NONE, Direction.SAME.value, Direction.OPPOSITE.value]

    def __init__(self, parent: ttk.Frame) -> None:
        self.vars: dict[tuple[int, int], tk.StringVar] = {}

        grid = ttk.Frame(parent)
        grid.pack(anchor=tk.W)
        ttk.Label(grid, text='moves \\ affects').grid(row=0, column=0, padx=(0, 6))
        for plate in range(PLATES):
            ttk.Label(grid, text=str(plate + 1)).grid(row=0, column=plate + 1)
            ttk.Label(grid, text=str(plate + 1)).grid(row=plate + 1, column=0, sticky=tk.E, padx=(0, 6))

        for src in range(PLATES):
            for dst in range(PLATES):
                if src == dst:
                    ttk.Label(grid, text='—').grid(row=src + 1, column=dst + 1)
                    continue
                var = tk.StringVar(value=self.NONE)
                combo = ttk.Combobox(
                    grid, textvariable=var, values=self.OPTIONS,
                    width=8, state='readonly',
                )
                combo.grid(row=src + 1, column=dst + 1, padx=1, pady=1)
                self.vars[src, dst] = var

        ttk.Label(
            parent,
            text='Row = plate you move, column = plate that follows.',
        ).pack(anchor=tk.W, pady=(6, 0))

    def connections(self) -> list[list[Connection]]:
        connections: list[list[Connection]] = [[] for _ in range(PLATES)]
        for (src, dst), var in self.vars.items():
            if var.get() != self.NONE:
                connections[src].append(Connection(plate=dst, direction=Direction(var.get())))
        return connections


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title('Gothic 1 Remake — Lockpick Solver')
        root.resizable(False, False)

        self.vertices = fill_vertices()
        self.edges_cache: dict[tuple, list] = {}

        main = ttk.Frame(root, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        start_frame = ttk.LabelFrame(main, text='Starting position', padding=8)
        start_frame.pack(fill=tk.X)
        self.pins: list[tk.IntVar] = []
        for plate in range(PLATES):
            column = ttk.Frame(start_frame)
            column.pack(side=tk.LEFT, expand=True)
            ttk.Label(column, text=f'Plate {plate + 1}').pack()
            var = tk.IntVar(value=TARGET[plate])
            spin = ttk.Spinbox(
                column, from_=1, to=SLOTS, textvariable=var,
                width=4, state='readonly',
            )
            spin.pack(padx=4)
            self.pins.append(var)

        conn_frame = ttk.LabelFrame(main, text='Plate connections', padding=8)
        conn_frame.pack(fill=tk.X, pady=(8, 0))
        self.matrix = ConnectionMatrix(conn_frame)

        ttk.Button(main, text='Solve', command=self.solve).pack(fill=tk.X, pady=(8, 0))

        out_frame = ttk.LabelFrame(main, text='Solution', padding=8)
        out_frame.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        self.output = tk.Text(
            out_frame, width=44, height=16, state=tk.DISABLED,
            font=('Consolas', 10),
        )
        self.output.pack(fill=tk.BOTH, expand=True)

    def get_edges(self, connections: list[list[Connection]]) -> list:
        key = tuple(
            (src, c.plate, c.direction)
            for src in range(PLATES)
            for c in connections[src]
        )
        if key not in self.edges_cache:
            self.edges_cache[key] = fill_edges(self.vertices, connections)
        return self.edges_cache[key]

    def solve(self) -> None:
        connections = self.matrix.connections()
        start = tuple(var.get() for var in self.pins)
        edges = self.get_edges(connections)
        path = run_dijkstra(edges, position_to_index(start), position_to_index(TARGET))

        if path is None:
            self.show('No solution: the target position is\nunreachable from the start.')
            return
        if not path:
            self.show('The lock is already open.')
            return

        lines = [f'Solution in {len(path)} movements:', '']
        position = start
        for i, move in enumerate(path, 1):
            next_position = apply_movement(position, move, connections)
            assert next_position is not None
            side_name = 'left ' if move.side is Side.LEFT else 'right'
            lines.append(
                f'{i:3}. plate {move.plate + 1} {side_name}  ->  {list(next_position)}'
            )
            position = next_position
        self.show('\n'.join(lines))

    def show(self, text: str) -> None:
        self.output.configure(state=tk.NORMAL)
        self.output.delete('1.0', tk.END)
        self.output.insert('1.0', text)
        self.output.configure(state=tk.DISABLED)


def main() -> None:
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == '__main__':
    main()
