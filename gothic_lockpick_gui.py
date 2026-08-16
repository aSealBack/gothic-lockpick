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

PLATE_NAMES = [str(i + 1) for i in range(PLATES)]
DIRECTION_NAMES = [d.value for d in Direction]


class ConnectionRow:
    """One 'plate A moves plate B same/opposite' row with a remove button."""

    def __init__(self, parent: ttk.Frame, on_change, on_remove) -> None:
        self.frame = ttk.Frame(parent)
        self.src = tk.StringVar(value=PLATE_NAMES[0])
        self.dst = tk.StringVar(value=PLATE_NAMES[1])
        self.direction = tk.StringVar(value=DIRECTION_NAMES[0])

        ttk.Label(self.frame, text='Plate').pack(side=tk.LEFT)
        self._combo(self.src, on_change).pack(side=tk.LEFT, padx=(4, 4))
        ttk.Label(self.frame, text='moves plate').pack(side=tk.LEFT)
        self._combo(self.dst, on_change).pack(side=tk.LEFT, padx=(4, 4))
        combo = ttk.Combobox(
            self.frame, textvariable=self.direction,
            values=DIRECTION_NAMES, width=9, state='readonly',
        )
        combo.bind('<<ComboboxSelected>>', lambda _e: on_change())
        combo.pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(
            self.frame, text='Remove', width=8,
            command=lambda: on_remove(self),
        ).pack(side=tk.LEFT)
        self.frame.pack(anchor=tk.W, pady=2)

    def _combo(self, var: tk.StringVar, on_change) -> ttk.Combobox:
        combo = ttk.Combobox(
            self.frame, textvariable=var,
            values=PLATE_NAMES, width=3, state='readonly',
        )
        combo.bind('<<ComboboxSelected>>', lambda _e: on_change())
        return combo

    def value(self) -> tuple[int, int, Direction]:
        """(source plate, dependent plate) as 0-based indices, plus direction."""
        return (
            int(self.src.get()) - 1,
            int(self.dst.get()) - 1,
            Direction(self.direction.get()),
        )

    def destroy(self) -> None:
        self.frame.destroy()


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
                width=4, state='readonly', command=self.solve,
            )
            spin.pack(padx=4)
            self.pins.append(var)

        conn_frame = ttk.LabelFrame(main, text='Plate connections', padding=8)
        conn_frame.pack(fill=tk.X, pady=(8, 0))
        self.rows_frame = ttk.Frame(conn_frame)
        self.rows_frame.pack(fill=tk.X)
        self.rows: list[ConnectionRow] = []
        ttk.Button(
            conn_frame, text='Add connection', command=self.add_row,
        ).pack(anchor=tk.W, pady=(4, 0))

        out_frame = ttk.LabelFrame(main, text='Solution', padding=8)
        out_frame.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        self.output = tk.Text(
            out_frame, width=44, height=16, state=tk.DISABLED,
            font=('Consolas', 10),
        )
        self.output.pack(fill=tk.BOTH, expand=True)

        self.solve()

    def add_row(self) -> None:
        self.rows.append(ConnectionRow(self.rows_frame, self.solve, self.remove_row))
        self.solve()

    def remove_row(self, row: ConnectionRow) -> None:
        self.rows.remove(row)
        row.destroy()
        self.solve()

    def read_connections(self) -> list[list[Connection]]:
        """Connections from the UI rows; raises ValueError on a self-connection."""
        connections: list[list[Connection]] = [[] for _ in range(PLATES)]
        for row in self.rows:
            src, dst, direction = row.value()
            if src == dst:
                raise ValueError(f'Plate {src + 1} cannot be connected to itself')
            connections[src].append(Connection(plate=dst, direction=direction))
        return connections

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
        try:
            connections = self.read_connections()
        except ValueError as e:
            self.show(str(e))
            return

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
