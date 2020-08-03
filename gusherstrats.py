import networkx as nx
import matplotlib.pyplot as plt
from ast import literal_eval as l_eval

COMMENTCHAR = '$'
DEFAULTCHAR = '.'


def load_map(mapname=None):
    """Create graph from the gusher layout and penalty values specified in external file."""
    path = f'goldie seeking/gusher graphs/{mapname}.txt'
    G = nx.read_adjlist(path, comments=COMMENTCHAR)

    # Assign penalties
    with open(path) as f:
        # Read the map name from the first line of the file
        name = f.readline().split(COMMENTCHAR)[-1]
        G.graph['name'] = name

        # Read the penalty dictionary from the second line of the file
        penalties = l_eval(f.readline().split(COMMENTCHAR)[-1])

        # For each node, check if its name is in any of the penalty groups and assign the corresponding penalty value
        # If no matches are found, assign the default penalty
        for node in G.nodes:
            penalty = penalties[DEFAULTCHAR]
            for group in penalties:
                if node in group:
                    penalty = penalties[group]
                    break
            G.nodes[node]['penalty'] = penalty

    return G


map = 'sg'
G = load_map(map)

plt.plot()
plt.title(G.graph['name'])
pos = nx.kamada_kawai_layout(G)
pos_attrs = {node: (coord[0]-0.08, coord[1]+0.1) for (node, coord) in pos.items()}
nx.draw_networkx(G, pos, edge_color='#888888', font_color='#ffffff')
nx.draw_networkx_labels(G, pos_attrs, labels=nx.get_node_attributes(G, 'penalty'))
plt.show()
