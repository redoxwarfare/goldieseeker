import pathlib
import networkx as nx
from ast import literal_eval
from numpy import genfromtxt, minimum
from scipy.spatial.distance import cdist
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import warnings

# Special characters for parsing files
COMMENT_CHAR = '#'
DEFAULT_CHAR = '.'
BASKET_LABEL = '@'

DISTANCE_SCALE_FACTOR = 32*4

# Constants for plotting graphs
EXTENTS = {'ap': (660, 300, 760),
           'lo': (396, 222, 1074),
           'mb': (570, 260, 870),
           'sg': (888, 640, 850),
           'ss': (363, 526, 720)}

# Colormap for plotting strategies
HIGH_CDICT = {'red':   [[0.0, 1.0, 1.0],
                        [1.0, 1.0, 1.0]],
              'green': [[0.0, 0.8, 0.8],
                        [0.6, 0.8, 0.8],
                        [1.0, 1.0, 1.0]],
              'blue':  [[0.0, 0.0, 0.0],
                        [0.6, 0.0, 0.0],
                        [1.0, 0.6, 0.6]]}

LOW_CDICT =  {'red':   [[0.0, 0.0, 0.0],
                        [0.6, 0.0, 0.0],
                        [1.0, 0.6, 0.6]],
              'green': [[0.0, 0.7, 0.7],
                        [1.0, 0.9, 0.9]],
              'blue':  [[0.0, 0.2, 0.2],
                        [0.6, 0.3, 0.3],
                        [1.0, 0.7, 0.7]]}

high_cmap = LinearSegmentedColormap('HighPath', segmentdata=HIGH_CDICT, N=256)
low_cmap = LinearSegmentedColormap('LowPath', segmentdata=LOW_CDICT, N=256)


# noinspection PyTypeChecker,PyTypeChecker
class GusherMap:
    def __init__(self, map_id, weights=None, squad=False):
        self.map_id = map_id
        self._path = pathlib.Path(__file__).parent.resolve() / f'maps/{map_id}'

        self._load_gushers(str(self._path/'gushers.csv'))
        self._load_distances(str(self._path/'distance_modifiers.txt'), squad)
        self._validate_distances()
        self._load_connections(str(self._path/'connections.txt'))
        if not weights:
            # Read the weight dictionary from the first non-commented line of the file
            # https://stackoverflow.com/a/26284995
            f = (line for line in open(str(self._path/'weights.txt'))
                 if not line.lstrip().startswith(COMMENT_CHAR))
            weights = next(f).strip()
        self._load_weights(literal_eval(weights))

    def _load_gushers(self, filename):
        self._gushers = genfromtxt(filename, delimiter=',', names=['name', 'coord'], dtype=['U8', '2u4'])

    def _load_distances(self, filename, squad=False):
        coords = self._gushers['coord']
        # Read norm from the 2nd line of the file
        with open(filename) as f:
            f.readline()
            norm_raw = f.readline().split(': ')[-1].strip(' \n')
        norm = float(norm_raw)
        adjacency_matrix = cdist(coords, coords, 'minkowski', p=norm) / DISTANCE_SCALE_FACTOR
        try:
            distance_modifiers = genfromtxt(filename, delimiter=',', comments=COMMENT_CHAR)
            adjacency_matrix += distance_modifiers
            if squad:
                # Assume that it never takes longer to reach a gusher than it would have taken coming from basket/spawn
                adjacency_matrix = minimum(adjacency_matrix, adjacency_matrix[0, :])
        except ValueError as e:
            warnings.warn(f"Couldn't read distance modifiers from '{filename}'\n" + str(e))
        self.distances = nx.from_numpy_array(adjacency_matrix, create_using=nx.DiGraph)
        # noinspection PyTypeChecker
        nx.relabel_nodes(self.distances, lambda i: self._gushers['name'][i], False)

    # May not be necessary
    def _load_distances_all_equal(self, nodes, all_distances=1, norm=2):
        self.distances = nx.complete_graph(nodes, create_using=nx.DiGraph)
        nx.set_edge_attributes(self.distances, all_distances, name='weight')
        # Use real distances for outgoing edges from the basket
        basket_distances = cdist(self._gushers['coord'][0].reshape(1, 2),
                                 self._gushers['coord'][1:],
                                 metric='minkowski', p=norm) / DISTANCE_SCALE_FACTOR
        edge_list = [(BASKET_LABEL, self._gushers['name'][i+1], basket_distances[0][i]) for i in range(len(nodes))]
        self.distances.add_node(BASKET_LABEL)
        self.distances.add_weighted_edges_from(edge_list)

    def _validate_distances(self):
        violations = self._find_triangle_inequality_violations()
        if violations:
            warnings.warn(f"Distances matrix for map '{self.map_id}' does not satisfy triangle inequality:\n" +
                          ''.join(f"    {t[0]}->{t[1]}->{t[2]} ({t[3]:g}) is shorter than {t[0]}->{t[2]} ({t[4]}:g)\n"
                                  for t in violations))

    def _load_connections(self, filename):
        # Read the map name from the first line of the file
        with open(filename) as f:
            self.name = f.readline().strip(COMMENT_CHAR + ' \n')
        connections_raw = nx.read_adjlist(filename, comments=COMMENT_CHAR)
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
                for other in neighborhood.difference({neighbor}):
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

    def plot(self, strategy=None):
        background = plt.imread(str(self._path.parent.parent.resolve()/f'images/{self.map_id}.png'))
        pos = {gusher['name']: tuple(gusher['coord']) for gusher in self._gushers if gusher['name'] != BASKET_LABEL}
        pos_attrs = {node: (coord[0] - 40, coord[1]) for (node, coord) in pos.items()}

        if self.map_id in EXTENTS:
            x, y, length = EXTENTS[self.map_id]
            extent = [x, x+length, y+length, y]
            background = background[y:y+length, x:x+length]
        else:
            extent = None

        plt.figure()
        ax = plt.subplot()
        ax.set_facecolor('#444444')
        plt.imshow(background, extent=extent)
        plt.title(self.name)
        nx.draw_networkx_edges(nx.to_undirected(self.connections), pos,
                               edge_color='#888888', style='dashed', width=1.5)
        nx.draw_networkx_labels(self.connections, pos_attrs, labels={gusher: self.weight(gusher) for gusher in pos},
                                font_weight='bold', font_color='#ff4a4a', horizontalalignment='right')

        if strategy:
            nonfindable = tuple(strategy.nonfindable_nodes())
            nonfindable_str = tuple(str(node) for node in nonfindable)
            if nonfindable:
                pos.update({str(node): (pos[node.name][0] + 50, pos[node.name][1]) for node in nonfindable})
            strat_graph = nx.to_networkx_graph(strategy.get_adj_dict(), create_using=nx.DiGraph)

            def node_color(node):
                if node == strategy.name:
                    return '#2bff2b'
                elif node in nonfindable_str:
                    return '#aaaaaa'
                else:
                    return '#ffffff'
            node_colors = [node_color(node) for node in strat_graph.nodes]
            high_edges = [(s, t) for s, t in strat_graph.edges if strat_graph[s][t]['high']]
            high_colors = [strat_graph[s][t]['depth'] for s, t in high_edges]
            low_edges = [(s, t) for s, t in strat_graph.edges if not strat_graph[s][t]['high']]
            low_colors = [strat_graph[s][t]['depth'] for s, t in low_edges]
            color_kwargs = ({'edgelist':  high_edges, 'edge_color': high_colors, 'edge_cmap': high_cmap},
                            {'edgelist': low_edges, 'edge_color': low_colors, 'edge_cmap': low_cmap})
            for kwargs in color_kwargs:
                nx.draw_networkx_edges(strat_graph, pos,
                                       width=2, connectionstyle='arc3, rad=0.25', min_target_margin=12,
                                       arrowstyle='simple, head_length=1.2, head_width=1.2', **kwargs)

            nx.draw_networkx_nodes(strat_graph, pos, node_color=node_colors)
        else:
            nx.draw_networkx_nodes(self.connections, pos, node_color='#ffffff')

        nx.draw_networkx_labels(self.connections, pos, labels={gusher: gusher for gusher in pos}, font_color='#111111')

        plt.show()


# TODO - move to separate test file
if __name__ == '__main__':
    for map_id in ('sg', 'ss', 'mb', 'lo', 'ap'):
        gusher_map = GusherMap(map_id)
        print('-'*len(gusher_map.name))
        print(gusher_map.name)
        for node in gusher_map:
            print(f"gusher {node} (weight {gusher_map.weight(node):g}) is adjacent to " +
                  ', '.join(f"{v} ({e['weight']:0.2f})" for v, e in gusher_map.adj(node).items()))
        gusher_map.plot()
