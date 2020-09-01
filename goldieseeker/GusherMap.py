import pathlib
import networkx as nx
from ast import literal_eval
from numpy import genfromtxt
from scipy.spatial import distance_matrix
import matplotlib.pyplot as plt
import warnings

# Special characters for parsing files
COMMENT_CHAR = '#'
DEFAULT_CHAR = '.'
BASKET_LABEL = '@'

# Constants for plotting graphs
EXTENTS = {'ap': (660, 300, 760),
           'lo': (396, 222, 1074),
           'mb': (570, 260, 870),
           'sg': (888, 640, 850),
           'ss': (363, 526, 720)}


class GusherMap:
    def __init__(self, map_id, weights=None, norm=2):
        self.map_id = map_id
        self._pkg_dir = pathlib.Path(__file__).parent.resolve()
        self.load(weights=weights, norm=norm)

    def load(self, weights=None, norm=2):
        path = self._pkg_dir/f'maps/{self.map_id}/'
        self._load_gushers(str(path/'gushers.csv'))
        self._load_distances(str(path/'distance_modifiers.txt'), norm=norm)
        self._load_connections(str(path/'connections.txt'))
        if not weights:
            # Read the weight dictionary from the first non-commented line of the file
            # https://stackoverflow.com/a/26284995
            f = (line for line in open(str(path/'weights.txt'))
                 if not line.lstrip().startswith(COMMENT_CHAR))
            weights = next(f).strip()
        self._load_weights(literal_eval(weights))

    def _load_gushers(self, filename):
        self._gushers = genfromtxt(filename, delimiter=',', names=['name', 'coord'], dtype=['U8', '2u4'])

    def _load_distances(self, filename, norm=2):
        coords = self._gushers['coord']
        adjacency_matrix = distance_matrix(coords, coords, p=norm) / (32*4)
        try:
            distance_modifiers = genfromtxt(filename, delimiter=',', comments=COMMENT_CHAR)
            adjacency_matrix += distance_modifiers
        except ValueError as e:
            warnings.warn(f"Couldn't read distance modifiers from '{filename}'\n" + str(e))

        self.distances = nx.from_numpy_array(adjacency_matrix, create_using=nx.DiGraph)
        # noinspection PyTypeChecker
        nx.relabel_nodes(self.distances, lambda i: self._gushers['name'][i], False)
        violations = self._find_triangle_inequality_violations()
        if violations:
            warnings.warn(f"Distances matrix in '{filename}' does not satisfy triangle inequality:\n" +
                          ''.join(f"    {t[0]}->{t[1]}->{t[2]} ({t[3]:g}) is shorter than {t[0]}->{t[2]} ({t[4]}:g)\n"
                                  for t in violations))

    def _load_connections(self, filename):
        # Read the map name from the first line of the file
        with open(filename) as f:
            self.name = f.readline().strip(COMMENT_CHAR + ' \n')
        connections_raw = nx.read_adjlist(filename, comments=COMMENT_CHAR)
        # If _load_distances failed, generate complete digraph from connections graph
        # may no longer be necessary?
        if not self.distances:
            self.distances = nx.complete_graph(connections_raw.nodes, create_using=nx.DiGraph)
            edge_list = [(BASKET_LABEL, node) for node in self.distances]
            self.distances.add_node(BASKET_LABEL)
            self.distances.add_edges_from(edge_list)
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

    def _load_weights(self, weights_dict):
        self.weights = {BASKET_LABEL: 0}
        for gusher in self.connections:
            gusher_weight = weights_dict[DEFAULT_CHAR]
            for group in weights_dict:
                if gusher in group:
                    gusher_weight = weights_dict[group]
                    break
            self.weights[gusher] = gusher_weight

    def _find_triangle_inequality_violations(self):
        def distance(start, end):
            return self.distances.adj[start][end]['weight']
        violations = set()
        for vertex in self.distances:
            neighborhood = set(self.distances.adj[vertex])
            for neighbor in neighborhood:
                shortest_distance = distance(vertex, neighbor)
                for other in neighborhood.difference(set(neighbor)):
                    other_distance = distance(vertex, other) + distance(other, neighbor)
                    if other_distance < shortest_distance:
                        violations.add((vertex, other, neighbor, other_distance, shortest_distance))
        return violations

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

    def plot(self):
        background = plt.imread(str(self._pkg_dir/f'images/{self.map_id}.png'))
        pos = {gusher['name']: tuple(gusher['coord']) for gusher in self._gushers if gusher['name'] != BASKET_LABEL}
        pos_attrs = {node: (coord[0] - 40, coord[1]) for (node, coord) in pos.items()}

        if self.map_id in EXTENTS:
            x, y, length = EXTENTS[self.map_id]
            extent = [x, x+length, y+length, y]
            background = background[y:y+length, x:x+length]
        else:
            extent = None

        plt.figure()
        plt.imshow(background, extent=extent)
        plt.title(self.name)
        nx.draw_networkx(self.connections, pos,
                         node_color='#1a611b', edge_color='#35cc37', font_color='#ffffff', arrows=False)
        nx.draw_networkx_labels(self.connections, pos_attrs, labels={gusher: self.weights[gusher] for gusher in pos},
                                font_weight='bold', font_color='#ff4a4a', horizontalalignment='right')
        plt.show()


def split(graph, vertex, adj=None):
    """Split graph into two subgraphs: nodes adjacent to vertex V, and nodes not adjacent to V."""
    if not adj:
        adj = graph.adj[vertex]
    adj_subgraph = graph.subgraph(adj)  # subgraph of vertices adjacent to V

    non_adj = set(graph).difference(adj_subgraph)
    non_adj = non_adj.difference({vertex})
    non_adj_subgraph = graph.subgraph(non_adj)  # subgraph of vertices non-adjacent to V (excluding V)

    return adj_subgraph, non_adj_subgraph


# TODO - move to separate test file
if __name__ == '__main__':
    for map_id in ('sg', 'ss', 'mb', 'lo', 'ap'):
        gusher_map = GusherMap(map_id)
        print('-'*len(gusher_map.name))
        print(gusher_map.name)
        for node in gusher_map:
            print(f"gusher {node} (weight {gusher_map.weights[node]:g}) is adjacent to " +
                  ', '.join(f"{v} ({e['weight']:0.2f})" for v, e in gusher_map.adj(node).items()))
        gusher_map.plot()
