import networkx as nx
from ast import literal_eval
from numpy import genfromtxt, nan_to_num
import warnings

# Special characters for parsing files
COMMENT_CHAR = '#'
DEFAULT_CHAR = '.'
BASKET_LABEL = '@'


class GusherMap:
    def __init__(self, map_id):
        self._folder = f'gusher graphs/{map_id}'
        self.load()

    def load(self):
        self._load_distances(f'{self._folder}/distances.txt')
        self._load_connections(f'{self._folder}/connections.txt')
        self._load_weights(f'{self._folder}/weights.txt')

    def _load_distances(self, filename):
        try:
            distances_raw = genfromtxt(filename, delimiter=', ', comments=COMMENT_CHAR)
            nan_to_num(distances_raw, copy=False, nan=1)
            self.distances = nx.from_numpy_array(distances_raw[:, 1:], create_using=nx.DiGraph)
        except ValueError as e:
            warnings.warn(f"Couldn't read distances matrix from '{filename}'\n" + str(e))
            self.distances = None
        else:
            # noinspection PyTypeChecker
            nx.relabel_nodes(self.distances, lambda i: f'{BASKET_LABEL}abcdefghijklmnopqrstuvwxyz'[i], False)
            if not self._satisfies_triangle_inequality():
                warnings.warn(f"Distances matrix in '{self._folder}' does not satisfy triangle inequality")

    def _load_connections(self, filename):
        # Read the gushers name from the first line of the file
        with open(filename) as f:
            self.name = f.readline().strip(COMMENT_CHAR + ' \n')
        connections_raw = nx.read_adjlist(filename, comments=COMMENT_CHAR)
        # If _load_distances failed, generate complete digraph from connections graph
        if not self.distances:
            self.distances = nx.complete_graph(connections_raw.nodes, create_using=nx.DiGraph)
            nx.set_edge_attributes(self.distances, 1, name='weight')
        else:
            conn_size = len(connections_raw)
            dist_size = len(self.distances)
            assert dist_size == conn_size + 1, f"Couldn't read {filename}\n" + \
                                               f"Distances matrix is {dist_size}x{dist_size} " + \
                                               f"but connections graph has {conn_size} vertices"
        self.connections = self.distances.edge_subgraph(connections_raw.to_directed(as_view=True).edges)
        # There's probably some way to induce a subgraph of 'distances' by reading edges directly from connections.txt,
        #   but I'm too lazy to figure out what that is

    def _load_weights(self, filename):
        # Read the weight dictionary from the first non-commented line of the file
        # https://stackoverflow.com/a/26284995
        f = (line for line in open(filename) if not line.lstrip().startswith(COMMENT_CHAR))
        weights_raw = literal_eval(next(f).strip())
        self.weights = {BASKET_LABEL: 0}
        for gusher in self.connections:
            gusher_weight = weights_raw[DEFAULT_CHAR]
            for group in weights_raw:
                if gusher in group:
                    gusher_weight = weights_raw[group]
                    break
            self.weights[gusher] = gusher_weight

    # TODO - write function to check whether 'distances' satisfies triangle inequality
    def _satisfies_triangle_inequality(self):
        return True

    def __len__(self):
        return len(self.connections)

    def __iter__(self):
        return self.connections.__iter__()

    def __contains__(self, item):
        return item in self.connections

    def distance(self, start, end):
        """Return distance between two gushers."""
        return self.distances.adj[start][end]['weight']

    def weight(self, vertex):
        """Return the weight of a gusher."""
        return self.weights[vertex]

    def adj(self, vertex):
        """Return adjacent gushers for a given gusher."""
        return self.connections.adj[vertex]

    def degree(self, vertex):
        """Return the number of adjacent gushers for a given gusher."""
        return self.connections.degree[vertex]


def split(graph, vertex, adj=None):
    """Split graph into two subgraphs: nodes adjacent to vertex V, and nodes not adjacent to V."""
    if not adj:
        adj = graph.adj[vertex]
    adj_subgraph = graph.subgraph(adj)  # subgraph of vertices adjacent to V

    non_adj = set(graph).difference(adj_subgraph)
    non_adj = non_adj.difference(set(vertex))
    non_adj_subgraph = graph.subgraph(non_adj)  # subgraph of vertices non-adjacent to V (excluding V)

    return adj_subgraph, non_adj_subgraph


if __name__ == '__main__':
    for map_id in ('sg', 'ss', 'mb', 'lo', 'ap'):
        gusher_map = GusherMap(map_id)
        print(gusher_map.name)
        for node in gusher_map:
            print(f"gusher {node} (weight {gusher_map.weights[node]:g}) is adjacent to " +
                  ', '.join(f"{v} ({e['weight']:g})" for v, e in gusher_map.adj(node).items()))
