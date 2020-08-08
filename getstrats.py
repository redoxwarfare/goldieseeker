import networkx as nx
import matplotlib.pyplot as plt
from ast import literal_eval as l_eval
from GusherNode import GusherNode, writetree, readtree
from statistics import mean, pstdev

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


def splitgraph(G, V, G_orig=None):
    """Split graph G into two subgraphs: nodes adjacent to vertex V, and nodes (excluding V) not adjacent to V."""
    if not G_orig:
        G_orig = G
    adj = G_orig.adj[V]
    A = G.subgraph(adj)  # subgraph of vertices adjacent to V

    nonadj = set(G).difference(A)
    nonadj = nonadj.difference(set(V))
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


def getstratnarrow(G, debug=False):
    """Build a decision tree for the gusher graph G. Memoized algorithm will find the optimal "narrow" decision tree,
    but does not consider "wide" decision trees (strategies in which gushers that cannot contain the Goldie are opened
    to obtain information about gushers that could contain the Goldie)."""

    def printlog(*args, **kwargs):
        if debug:
            print(*args, **kwargs)

    subgraphs = dict()

    # dict for associating subgraphs with their corresponding optimal subtrees and objective scores
    # stores optimal subtrees as strings to avoid entangling references between different candidate subtrees

    def recursenarrow(U, subgraphs):  # U = subgraph of unopened nodes
        key = tuple(U)
        if key in subgraphs:  # don't recalculate optimal trees for subgraphs we've already solved
            return readtree(subgraphs[key][0], G, obj=subgraphs[key][1])
        printlog(f'U: {key}, solved {len(subgraphs)} subgraphs')

        root = None
        obj = 0
        n = len(U)
        if n == 1:  # Base case
            root = GusherNode(list(U.nodes)[0], G)
        elif n > 1:
            Vcand = dict()  # For each possible root V, store objective score for resulting tree
            for V in U:
                A, B = splitgraph(U, V)
                printlog(f'    check gusher {V}\n'
                         f'        adj: {tuple(A)}\n'
                         f'        non-adj: {tuple(B)}')
                high = recursenarrow(A, subgraphs)
                low = recursenarrow(B, subgraphs)
                objH = high.obj if high else 0
                objL = low.obj if low else 0
                pV = G.nodes[V]['penalty']
                Vcand[V] = ((n-1)*pV+objH+objL, high, low)
            printlog(f'options: \n'
                     ''.join(f'    {V}: ({t[0]}, {t[1]}, {t[2]})\n' for V, t in Vcand.items()))
            V = min(Vcand, key=lambda g: Vcand[g][0])  # Choose the V that minimizes objective score
            obj, high, low = Vcand[V]

            # Build tree
            root = GusherNode(V, G)
            root.addchildren(high, low)
            printlog(f'    root: {str(root)}, {obj}\n'
                     f'    high: {str(high)}, {high.obj if high else 0}\n'
                     f'    low: {str(low)}, {low.obj if low else 0}')

        if root:
            root.obj = obj  # Don't need calc_tree_obj since calculations are done as part of tree-finding process
            if root.high or root.low:
                subgraphs[key] = (writetree(root), root.obj)
        return root

    root = recursenarrow(G, subgraphs)
    root.updatecost()
    if debug:
        for subgraph in subgraphs:
            print(f'{subgraph}: {subgraphs[subgraph][1] if subgraphs[subgraph] else 0}')
    return root


def getstrat(G, debug=False):
    """Build the optimal "wide" decision tree for the gusher graph G. Memoized algorithm."""

    def printlog(*args, **kwargs):
        if debug:
            print(*args, **kwargs)

    def widen(working, excluded, orig_graph):
        """Widen the working set of vertices to include any vertices adjacent to those in the original set, while
        excluding the vertices in the excluded set."""
        wide = set(working)
        for node in working:
            wide = wide.union(orig_graph.adj[node])
        wide = wide.difference(excluded)
        return wide

    subgraphs = dict()

    # dict for associating subgraphs with their corresponding optimal subtrees and objective scores
    # stores optimal subtrees as strings to avoid entangling references between different candidate subtrees

    def recursewide(U, O, subgraphs):
        # U = subgraph of unopened gushers that might have the Goldie
        # O = set of opened gushers
        key = (tuple(U), frozenset(O))
        keystr = f'({", ".join(str(u) for u in U)} | {", ".join(str(o) for o in O)})'
        if key in subgraphs:  # don't recalculate optimal trees for subgraphs we've already solved
            return readtree(subgraphs[key][0], G, obj=subgraphs[key][1])
        printlog(f'{keystr}; solved {len(subgraphs)} subgraphs')

        root = None
        obj = 0
        n = len(U)
        if n == 1:  # Base case
            root = GusherNode(list(U.nodes)[0], G)
        elif n > 1:
            Uwide = widen(U, O, G)  # also consider gushers adjacent to those in U
            Vcand = dict()  # For each possible root V, store objective score for resulting tree
            for V in Uwide:
                findable = V in U
                A, B = splitgraph(U, V, G)
                printlog(f'{keystr}; check gusher {V}{"*" if not findable else ""}\n'
                         f'    adj: {tuple(A)}\n'
                         f'    non-adj: {tuple(B)}')
                high = recursewide(A, O.union(set(V)), subgraphs)
                low = recursewide(B, O.union(set(V)), subgraphs)

                objH = high.obj if high else 0
                sizeH = high.size if high else 0
                objL = low.obj if low else 0
                sizeL = low.size if low else 0
                pV = G.nodes[V]['penalty']
                Vcand[V] = ((sizeH+sizeL)*pV+objH+objL, high, low, findable)
            printlog(f'{keystr}; options: \n'+
                     '\n'.join(f'    {V}{"*" if not t[3] else ""} > ({t[1]}, {t[2]}), score: {t[0]}'
                               for V, t in Vcand.items()))
            V = min(Vcand, key=lambda g: Vcand[g][0])  # Choose the V that minimizes objective score
            obj, high, low, findable = Vcand[V]

            # Build tree
            root = GusherNode(V, G, findable=findable)
            root.addchildren(high, low)
            printlog(f'    root: {str(root)}, {obj}\n'
                     f'    high: {str(high)}, {high.obj if high else 0}\n'
                     f'    low: {str(low)}, {low.obj if low else 0}\n')

        if root:
            root.obj = obj  # Don't need calc_tree_obj since calculations are done as part of tree-finding process
            if root.high or root.low:
                subgraphs[key] = (writetree(root), root.obj)
        return root

    root = recursewide(G, set(), subgraphs)
    root.updatecost()
    return root


# TODO - start compilation of strategy variants for each map
recstrats = {'sg': 'f(e(d(c,),), h(g(a,), i(b,)))',
             'ap': 'f(g(e, c(d,)), g*(a, b))',
             'ss': 'f(d(b, g), e(c, a))',
             'mb': 'b(c(d(a,), e), c*(f, h(g,)))',
             'lo': 'g(h(i,), d(f(e,), a(c(b,),)))'}
mbhybrid = readtree('b(e(d, c(a,)), c*(f, h(g,)))', load_graph('mb'))
lostaysee = readtree('h(f(e, g(i,)), f*(d, a(c(b,),)))', load_graph('lo'))

if __name__ == '__main__':
    map_id = 'mb'
    G = load_graph(map_id)
    plot_graph(G)
    print(f'\nMap: {G.graph["name"]}')

    recstrat = readtree(recstrats[map_id], G)
    greedystrat = getstratgreedy(G)
    narrowstrat = getstratnarrow(G)
    optstrat = getstrat(G, debug=True)

    strats = {"greedy": greedystrat,
              "optimized narrow": narrowstrat,
              "optimized wide": optstrat,
              "recommended": recstrat}
    for desc in strats:
        strat = strats[desc]
        try:
            strat.validate()
        except AssertionError as e:
            print(f'validate() failed for {desc} strat with error "{e}"')
        strat.updatecost()
        costs = {str(g): g.cost for g in strat if g.findable}
        print(f'{desc} strat: {writetree(strat)}\n'
              f'    objective score: {strat.obj}\n'
              f'    costs: {{'+', '.join(f'{node}: {costs[node]}' for node in costs)+'}\n'
                                                                                     f'    mean cost: {mean(costs.values()):0.2f}, stdev: {pstdev(costs.values()):0.2f}')
