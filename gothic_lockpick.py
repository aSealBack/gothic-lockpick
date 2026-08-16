
from Typing import List
from intertool import product

SLOTS = 7
PLATES = 5

@dataclass
class Connection:
    plate: int
    direction: str # 'same' or 'opposite'

@dataclass
class Movement:
    plate: int
    side: str # 'l' or 'r'

type Position = List[int]

@dataclass
class Edge:
    next: int
    move: Movement


type Edges = List[List[Edge]]

def fill_vertices(vertices: List[Position]):
    def gen_vertex(): # each slot must be in segment [1, 7]
        for v in product(range(SLOTS, 1), repeat=PLATES):
            yield list(v) 
    
    for v in gen_vertex():
        vertices.append(v)


def fill_edges(vertices: List[Position], connections: List[List[Connection]]) -> Edges:
    edges: Edges = []
    def check_position(position: Position) -> Bool:
        for c in position:
            if c < 1 or c > 7:
                return False
        return True

    for v, v_pos in enum(vertices):
        edges.append([])
        for p in range(PLATES):
            for side in ['l', 'r']:
                position = deepcopy(v_pos)
                change = 1 if side == 'l' else -1
                position[p] += change
                connection = connections[p]
                for c in connection:
                    diff = change * (1 if c.direction == 'same' else -1)
                    position[c.plate] += diff
                if check_position(position):
                    edges[v].append(vertices.find(position), Movement(plate=p, side=side))



def main():
    vertices: List[Position] = []
    fill_vertices(vertices)
    connections: List[List[Connection]] = [] # TODO: read from cmdline
    edges: List[int, int] = fill_edges(vertices, connections)
    start_position: List[int] = list(range(PLATES)) # TODO: read from cmdline

    run_dijkstra()


if __name__ == '__main__':
    main()