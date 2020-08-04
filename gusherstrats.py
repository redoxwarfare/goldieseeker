import networkx as nx
import matplotlib.pyplot as plt
from ast import literal_eval as l_eval
from collections import deque

# Special characters for parsing gusher graph files
COMMENTCHAR = '$'
DEFAULTCHAR = '.'


class BNode:
    def __init__(self, G, name):
        self.name = name
        self.low = None  # next gusher to open if this gusher is low
        self.high = None  # next gusher to open if this gusher is high
        self.penalty = G.nodes[name]['penalty']  # penalty for opening this gusher
        self.cost = 0  # if Goldie is in this gusher, total penalty incurred by following decision tree
        self.obj = 0  # objective function evaluated on subtree with this node as root
        # TODO - need to fix objective score to properly implement dynamic programming?

    def addchildren(self, low, high, n=0):
        objL = 0
        objH = 0
        if low:
            self.low = low
            self.low.update(self.penalty)
            objL = self.low.obj
        if high:
            self.high = high
            self.high.update(self.penalty)
            objH = self.high.obj
        if n:
            self.obj = self.penalty * (n - 1) + objL + objH

    def update(self, p):  # only works if tree is built from bottom up
        self.cost += p
        if self.low:
            self.low.update(p)
        if self.high:
            self.high.update(p)

    def __str__(self):
        return self.name

    def __repr__(self):
        return f'{{{self.name} > {self.high} ({self.low}), p: {self.penalty}, c: {self.cost}, o: {self.obj}}}'

    def writestrat(self):  # TODO - replace with a better pretty-printer
        s = ""
        high = self
        lows = deque([deque()])
        while high or (lows and lows[0]):
            # first traverse as many "high" gushers as possible
            high_exhausted = not high
            if high_exhausted:  # after exhausting high gushers, traverse entire "low" subtree
                high = lows[0].popleft()

            current = high
            s += str(current)
            high = current.high

            if current.low:
                if high_exhausted:
                    lows.appendleft(deque([current.low]))
                else:
                    lows[0].append(current.low)

            if not high:
                if lows and lows[0]:
                    s += '('
                else:
                    s += ')'
                    lows.popleft()
                    if lows:
                        s += ','
        return s + ')'


def load_map(mapname):  # TODO - separate gusher map and penalty assignment(s) into 2 files
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


# TODO - write more thorough version of optimalstrat that checks all possible trees and uses dynamic programming

def optimalstrat(G):
    """Build an optimal decision tree for the gusher graph G."""
    n = len(G)
    # Base cases
    if n == 0:
        return None
    if n == 1:
        return BNode(G, list(G.nodes)[0])

    # Choose vertex V w/ lowest penalty and degree closest to n/2
    minpenalty = min([G.nodes[g]['penalty'] for g in G])
    Vcand = [g for g in G if G.nodes[g]['penalty'] == minpenalty]
    V = min(Vcand, key=lambda g: abs(G.degree[g] - n // 2))

    # Build subtrees
    A = G.subgraph(G.adj[V])  # subgraph of vertices adjacent to V
    nonadj = set(G).difference(A)
    nonadj.remove(V)
    B = G.subgraph(nonadj)  # subgraph of vertices non-adjacent to V (excluding V)
    high = optimalstrat(A)
    low = optimalstrat(B)

    # Construct optimal tree
    root = BNode(G, V)
    root.addchildren(low, high, n)
    return root


if __name__ == '__main__':
    map = 'sg'
    G = load_map(map)

    plt.plot()
    plt.title(G.graph['name'])
    pos = nx.kamada_kawai_layout(G)
    pos_attrs = {node: (coord[0] - 0.08, coord[1] + 0.1) for (node, coord) in pos.items()}
    nx.draw_networkx(G, pos, edge_color='#888888', font_color='#ffffff')
    nx.draw_networkx_labels(G, pos_attrs, labels=nx.get_node_attributes(G, 'penalty'))
    plt.show()

    nodes = {name: BNode(G, name) for name in G.nodes}
    recstrat = nodes['f']
    nodes['d'].addchildren(None, nodes['c'], 2)
    nodes['e'].addchildren(None, nodes['d'], 3)
    nodes['g'].addchildren(None, nodes['a'], 2)
    nodes['i'].addchildren(None, nodes['b'], 2)
    nodes['h'].addchildren(nodes['i'], nodes['g'], 5)
    nodes['f'].addchildren(nodes['h'], nodes['e'], 9)
    print(f'recommended strat: {recstrat.writestrat()}')

    optstrat = optimalstrat(G)
    print(f'algorithm\'s strat: {optstrat.writestrat()}')
