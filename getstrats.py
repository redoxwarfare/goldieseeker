import networkx as nx
# noinspection PyUnresolvedReferences
import matplotlib.pyplot as plt
from ast import literal_eval as l_eval
from GusherNode import GusherNode, writetree, readtree

# Special characters for parsing files
COMMENTCHAR = '$'
DEFAULTCHAR = '.'


def load_graph(mapname):  # TODO - separate gusher map and penalty assignment(s) into 2 files
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


def plot_graph(graph):
    plt.plot()
    plt.title(graph.graph['name'])
    pos = nx.kamada_kawai_layout(graph)
    pos_attrs = {node: (coord[0] - 0.08, coord[1] + 0.1) for (node, coord) in pos.items()}
    nx.draw_networkx(graph, pos, edge_color='#888888', font_color='#ffffff')
    nx.draw_networkx_labels(graph, pos_attrs, labels=nx.get_node_attributes(graph, 'penalty'))
    plt.show()


# TODO - write more thorough version of getstrat that checks all possible trees and uses dynamic programming
def getstrat(G):
    root = None
    return root


def getstratfast(G):
    """Build an optimal decision tree for the gusher graph G."""
    n = len(G)
    # Base cases
    if n == 0:
        return None
    if n == 1:
        return GusherNode(list(G.nodes)[0], graph=G)

    # Choose vertex V w/ lowest penalty and degree closest to n/2
    minpenalty = min([G.nodes[g]['penalty'] for g in G])
    Vcand = [g for g in G if G.nodes[g]['penalty'] == minpenalty]
    V = min(Vcand, key=lambda g: abs(G.degree[g] - n / 2))

    # Build subtrees
    A = G.subgraph(G.adj[V])  # subgraph of vertices adjacent to V
    nonadj = set(G).difference(A)
    nonadj.remove(V)
    B = G.subgraph(nonadj)  # subgraph of vertices non-adjacent to V (excluding V)
    high = getstratfast(A)
    low = getstratfast(B)

    # Construct optimal tree
    root = GusherNode(V, graph=G)
    root.addchildren(high, low, n)
    return root


recstrats = {'sg': 'f(e(d(c,),), h(g(a,), i(b,)))',
             'ap': 'f(g(e, c(d,)), g*(a, b))',
             'ss': 'f(d(b, g), e(c, a))',
             'mb': 'b(c(d(a,), e), c*(f, h(g,)))',
             'lo': 'g(h(i,), d(f(e,), a(c(b,),)))'}
desc = ('recommended', "algorithm's")

if __name__ == '__main__':
    map_id = 'mb'
    G = load_graph(map_id)
    plot_graph(G)

    recstrat = readtree(recstrats[map_id], G)
    optstrat = getstratfast(G)
    optstrat.calc_tree_obj()
    strats = (recstrat, optstrat)
    for i in range(len(strats)):
        print(f'\n{desc[i]} strat: {writetree(strats[i])}\n'
              f'    objective score: {strats[i].obj}\n'
              '    costs: {' + ', '.join(f'{g}: {g.cost}' for g in strats[i] if g.findable) + '}')
