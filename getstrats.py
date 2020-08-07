import networkx as nx
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
    plt.figure()
    plt.title(graph.graph['name'])
    pos = nx.kamada_kawai_layout(graph)
    pos_attrs = {node: (coord[0] - 0.08, coord[1] + 0.1) for (node, coord) in pos.items()}
    nx.draw_networkx(graph, pos, edge_color='#888888', font_color='#ffffff')
    nx.draw_networkx_labels(graph, pos_attrs, labels=nx.get_node_attributes(graph, 'penalty'))
    plt.show()


def splitgraph(G, V):
    """Split graph G into two subgraphs: nodes adjacent to vertex V, and nodes (excluding V) not adjacent to V."""
    A = G.subgraph(G.adj[V])  # subgraph of vertices adjacent to V
    nonadj = set(G).difference(A)
    nonadj.remove(V)
    B = G.subgraph(nonadj)  # subgraph of vertices non-adjacent to V (excluding V)
    return A, B


def getstratgreedy(G):
    """Build a decision tree for the gusher graph G. Greedy algorithm not guaranteed to find the optimal tree,
    but should still return something decent."""
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
    A, B = splitgraph(G, V)
    high = getstratgreedy(A)
    low = getstratgreedy(B)

    # Construct optimal tree
    root = GusherNode(V, graph=G)
    root.addchildren(high, low, n)
    return root


def getstrat(G, debug=False):
    """Build a decision tree for the gusher graph G. Memoized algorithm will find the optimal "narrow" decision tree,
    but does not consider "wide" decision trees (strategies in which gushers that cannot contain the Goldie are opened
    to obtain information about gushers that could contain the Goldie)."""

    def printlog(*args, **kwargs):
        if debug:
            print(*args, **kwargs)

    def makenode(name):
        return GusherNode(name, G)

    subgraphs = dict()

    # dict for associating subgraphs with their corresponding optimal subtrees and objective scores
    # stores optimal subtrees as strings to avoid entangling references between different candidate subtrees

    def getstratrecurse(O, subgraphs):
        Okey = tuple(O)
        if Okey in subgraphs:  # don't recalculate optimal trees for subgraphs we've already solved
            return readtree(subgraphs[Okey][0], G, obj=subgraphs[Okey][1])
        printlog(f'O: {Okey}, solved {len(subgraphs)} subgraphs')

        root = None
        obj = 0
        n = len(O)
        if n == 1:  # base case
            root = makenode(list(O.nodes)[0])
        elif n > 1:
            Vcand = dict()  # for each possible root V, store objective score for resulting tree
            for V in O:
                A, B = splitgraph(O, V)
                printlog(f'    check gusher {V}\n'
                         f'        adj: {tuple(A)}\n'
                         f'        non-adj: {tuple(B)}')
                high = getstratrecurse(A, subgraphs)
                low = getstratrecurse(B, subgraphs)
                objH = high.obj if high else 0
                objL = low.obj if low else 0
                pV = O.nodes[V]['penalty']
                Vcand[V] = ((n - 1) * pV + objH + objL, high, low)
            printlog(f'options: \n'
                     ''.join(f'    {V}: ({t[0]}, {t[1]}, {t[2]})\n' for V, t in Vcand.items()))
            V = min(Vcand, key=lambda g: Vcand[g][0])  # choose the V that minimizes objective score
            obj, high, low = Vcand[V]

            # Build tree
            root = makenode(V)
            root.addchildren(high, low)
            printlog(f'    root: {str(root)}, {obj}\n'
                     f'    high: {str(high)}, {high.obj if high else 0}\n'
                     f'    low: {str(low)}, {low.obj if low else 0}')

        if root:
            root.obj = obj  # don't need calc_tree_obj since calculations are done as part of tree-finding process
            if root.high or root.low:
                subgraphs[Okey] = (writetree(root), root.obj)
        return root

    root = getstratrecurse(G, subgraphs)
    if debug:
        for O in subgraphs:
            print(f'{O}: {subgraphs[O][1] if subgraphs[O] else 0}')
    return root


def check_sanity(tree):
    for g in tree:
        if g.high:
            assert g.high.parent == g, f'node {g}, node.high {g.high}, node.high.parent {g.high.parent}'
        if g.low:
            assert g.low.parent == g, f'node {g}, node.low {g.high}, node.low.parent {g.low.parent}'


# TODO - start compilation of strategy variants for each map
recstrats = {'sg': 'f(e(d(c,),), h(g(a,), i(b,)))',
             'ap': 'f(g(e, c(d,)), g*(a, b))',
             'ss': 'f(d(b, g), e(c, a))',
             'mb': 'b(c(d(a,), e), c*(f, h(g,)))',
             'lo': 'g(h(i,), d(f(e,), a(c(b,),)))'}
desc = ('recommended', "algorithm's")

if __name__ == '__main__':
    for map_id in recstrats:
        G = load_graph(map_id)
        plot_graph(G)
        print(f'\nMap: {G.graph["name"]}')

        recstrat = readtree(recstrats[map_id], G)
        optstrat = getstrat(G)
        optstrat.calc_tree_obj()
        strats = (recstrat, optstrat)
        for i in range(len(strats)):
            print(f'{desc[i]} strat: {writetree(strats[i])}\n'
                  f'    objective score: {strats[i].obj}\n'
                  '    costs: {' + ', '.join(f'{g}: {g.cost}' for g in strats[i] if g.findable) + '}')

    foo = readtree(writetree(recstrat), G)
    bar = readtree(writetree(optstrat), G)
    heck = readtree('a(b(c, d), e(f, g))', G)
    assert foo.sametree(recstrat)
    assert bar.sametree(optstrat)
    assert not foo.sametree(heck)
    assert not bar.sametree(heck)

    check_sanity(optstrat)
