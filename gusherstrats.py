import networkx as nx
# noinspection PyUnresolvedReferences
import matplotlib.pyplot as plt
from ast import literal_eval as l_eval
from GusherNode import GusherNode, writetree, readtree

# Special characters for parsing files
COMMENTCHAR = '$'
DEFAULTCHAR = '.'


def load_map(mapname):  # TODO - separate gusher map and penalty assignment(s) into 2 files
    """Create graph from the gusher layout and penalty values specified in external file."""
    path = f'gusher graphs/{mapname}.txt'
    G = nx.read_adjlist(path, comments=COMMENTCHAR)

    # Assign penalties
    with open(path) as f:
        # Read the map name from the first line of the file
        name = f.readline().lstrip(COMMENTCHAR + ' ')
        G.graph['name'] = name.rstrip()

        # Read the penalty dictionary from the second line of the file
        penalties = l_eval(f.readline().lstrip(COMMENTCHAR + ' '))

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


# TODO - write more thorough version of optimalstrat that checks all possible trees and uses dynamic programming

def getstratfast(G):
    """Build an optimal decision tree for the gusher graph G."""
    n = len(G)
    # Base cases
    if n == 0:
        return None
    if n == 1:
        return GusherNode(G, list(G.nodes)[0])

    # Choose vertex V w/ lowest penalty and degree closest to n/2
    minpenalty = min([G.nodes[g]['penalty'] for g in G])
    Vcand = [g for g in G if G.nodes[g]['penalty'] == minpenalty]
    V = min(Vcand, key=lambda g: abs(G.degree[g] - n // 2))

    # Build subtrees
    A = G.subgraph(G.adj[V])  # subgraph of vertices adjacent to V
    nonadj = set(G).difference(A)
    nonadj.remove(V)
    B = G.subgraph(nonadj)  # subgraph of vertices non-adjacent to V (excluding V)
    high = getstratfast(A)
    low = getstratfast(B)

    # Construct optimal tree
    root = GusherNode(G, V)
    root.addchildren(high, low, n)
    return root


if __name__ == '__main__':
    map_id = 'sg'
    G = load_map(map_id)

    # noinspection PyUnreachableCode
    if False:
        plt.plot()
        plt.title(G.graph['name'])
        pos = nx.kamada_kawai_layout(G)
        pos_attrs = {node: (coord[0] - 0.08, coord[1] + 0.1) for (node, coord) in pos.items()}
        nx.draw_networkx(G, pos, edge_color='#888888', font_color='#ffffff')
        nx.draw_networkx_labels(G, pos_attrs, labels=nx.get_node_attributes(G, 'penalty'))
        plt.show()

    recstrat = readtree('f(e(d(c,),), h(g(a,), i(b,)))', G)
    print(f'recommended strat: {writetree(recstrat)}')

    optstrat = getstratfast(G)
    print(f'algorithm\'s strat: {writetree(optstrat)}')
