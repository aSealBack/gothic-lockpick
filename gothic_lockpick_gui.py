"""Tkinter GUI for the Gothic 1 Remake lockpick solver.

Uses gothic_lockpick.py as a library; run with:
    python gothic_lockpick_gui.py
"""

import tkinter as tk
from tkinter import ttk

from gothic_lockpick import (
    SLOTS,
    TARGET_PIN,
    Connection,
    Direction,
    Side,
    apply_movement,
    solve,
    target_position,
)

PLATE_CHOICES = (5, 6, 7)
DEFAULT_PLATES = 5


class ConnectionMatrix:
    """Adjacency matrix of plate connections: cell (A, B) tells how moving
    plate A affects plate B."""

    NONE = 'none'
    OPTIONS = [NONE, Direction.SAME.value, Direction.OPPOSITE.value]

    def __init__(
        self,
        parent: ttk.Frame,
        plates: int,
        initial: dict[tuple[int, int], str] | None = None,
    ) -> None:
        initial = initial or {}
        self.plates = plates
        self.vars: dict[tuple[int, int], tk.StringVar] = {}

        grid = ttk.Frame(parent)
        grid.pack(anchor=tk.W)
        ttk.Label(grid, text='moves \\ affects').grid(row=0, column=0, padx=(0, 6))
        for plate in range(plates):
            ttk.Label(grid, text=str(plate + 1)).grid(row=0, column=plate + 1)
            ttk.Label(grid, text=str(plate + 1)).grid(row=plate + 1, column=0, sticky=tk.E, padx=(0, 6))

        for src in range(plates):
            for dst in range(plates):
                if src == dst:
                    ttk.Label(grid, text='—').grid(row=src + 1, column=dst + 1)
                    continue
                var = tk.StringVar(value=initial.get((src, dst), self.NONE))
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

    def values(self) -> dict[tuple[int, int], str]:
        return {key: var.get() for key, var in self.vars.items()}

    def connections(self) -> list[list[Connection]]:
        connections: list[list[Connection]] = [[] for _ in range(self.plates)]
        for (src, dst), var in self.vars.items():
            if var.get() != self.NONE:
                connections[src].append(Connection(plate=dst, direction=Direction(var.get())))
        return connections


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title('Gothic 1 Remake — Lockpick Solver')
        root.resizable(False, False)

        main = ttk.Frame(root, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        top = ttk.Frame(main)
        top.pack(fill=tk.X)
        ttk.Label(top, text='Plates:').pack(side=tk.LEFT)
        self.plate_var = tk.IntVar(value=DEFAULT_PLATES)
        plate_combo = ttk.Combobox(
            top, textvariable=self.plate_var, values=PLATE_CHOICES,
            width=4, state='readonly',
        )
        plate_combo.pack(side=tk.LEFT, padx=(4, 0))
        plate_combo.bind('<<ComboboxSelected>>', lambda _event: self.rebuild_inputs())
        ttk.Button(top, text='Reset', command=self.reset).pack(side=tk.RIGHT)

        self.start_frame = ttk.LabelFrame(main, text='Starting position', padding=8)
        self.start_frame.pack(fill=tk.X, pady=(8, 0))
        self.conn_frame = ttk.LabelFrame(main, text='Plate connections', padding=8)
        self.conn_frame.pack(fill=tk.X, pady=(8, 0))

        self.pins: list[tk.IntVar] = []
        self.matrix: ConnectionMatrix
        self.build_inputs()

        ttk.Button(main, text='Solve', command=self.on_solve).pack(fill=tk.X, pady=(8, 0))

        out_frame = ttk.LabelFrame(main, text='Solution', padding=8)
        out_frame.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        self.output = tk.Text(
            out_frame, width=52, height=16, state=tk.DISABLED,
            font=('Consolas', 10),
        )
        self.output.pack(fill=tk.BOTH, expand=True)

    def build_inputs(
        self,
        pin_values: dict[int, int] | None = None,
        matrix_values: dict[tuple[int, int], str] | None = None,
    ) -> None:
        """(Re)create the pin spinboxes and the connection matrix for the
        current plate count, keeping the passed-in values where they fit."""
        pin_values = pin_values or {}
        plates = self.plate_var.get()

        for frame in (self.start_frame, self.conn_frame):
            for child in frame.winfo_children():
                child.destroy()

        self.pins = []
        for plate in range(plates):
            column = ttk.Frame(self.start_frame)
            column.pack(side=tk.LEFT, expand=True)
            ttk.Label(column, text=f'Plate {plate + 1}').pack()
            var = tk.IntVar(value=pin_values.get(plate, TARGET_PIN))
            spin = ttk.Spinbox(
                column, from_=1, to=SLOTS, textvariable=var,
                width=4, state='readonly',
            )
            spin.pack(padx=4)
            self.pins.append(var)

        self.matrix = ConnectionMatrix(self.conn_frame, plates, matrix_values)

    def rebuild_inputs(self) -> None:
        """Plate count changed: rebuild inputs, preserving current values."""
        self.build_inputs(
            pin_values={i: var.get() for i, var in enumerate(self.pins)},
            matrix_values=self.matrix.values(),
        )

    def reset(self) -> None:
        self.plate_var.set(DEFAULT_PLATES)
        self.build_inputs()
        self.show('')

    def on_solve(self) -> None:
        plates = self.plate_var.get()
        connections = self.matrix.connections()
        start = tuple(var.get() for var in self.pins)
        self.show('Solving…')
        self.root.update_idletasks()
        path = solve(start, target_position(plates), connections)

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
