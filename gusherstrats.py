import networkx as nx
import matplotlib.pyplot as plt
import re
from ast import literal_eval as l_eval
from collections import deque
from random import shuffle

# Special characters for parsing files
COMMENTCHAR = '$'
DEFAULTCHAR = '.'


class BNode:
    def __init__(self, G, name):
        self.name = name
        self.low = None  # next gusher to open if this gusher is low
        self.high = None  # next gusher to open if this gusher is high
        self.parent = None # gusher previously opened in sequence
        self.penalty = G.nodes[name]['penalty']  # penalty for opening this gusher
        self.cost = 0  # if Goldie is in this gusher, total penalty incurred by following decision tree
        self.obj = 0  # objective function evaluated on subtree with this node as root

    def addchildren(self, low, high, n=0):
        objL = 0
        objH = 0
        if low:
            self.low = low
            low.parent = self
            objL = self.low.obj
        if high:
            self.high = high
            high.parent = self
            objH = self.high.obj
        if n:
            self.obj = self.penalty * (n - 1) + objL + objH
        self.updatecost()

    def updatecost(self):
        """Recursively update costs of node and its children."""
        if self.parent:
            self.cost = self.parent.penalty + self.parent.cost
        if self.low:
            self.low.updatecost()
        if self.high:
            self.high.updatecost()

    def calc_tree_obj(self):
        """Calculate and store the objective score of the tree rooted at this node."""
        def recurse_sum(node):
            hsum = 0
            lsum = 0
            if node.high:
                hsum = recurse_sum(node.high)
            if node.low:
                lsum = recurse_sum(node.low)
            return node.cost + hsum + lsum
        self.updatecost()
        self.obj = recurse_sum(self)

    def __str__(self):
        return self.name

    def __repr__(self):
        return f'{{{self.name} > ({self.high}, {self.low}), p: {self.penalty}, c: {self.cost}, o: {self.obj}}}'


    def writetree(self):
        """Write the strategy encoded by the subtree rooted at this node in modified Newick format.
        V(H, L) represents the tree with root node V, high subtree H, and low subtree L."""
        if self.high and self.low:
            return f'{self}({self.high.writetree()}, {self.low.writetree()})'
        elif self.high:
            return f'{self}({self.high.writetree()})'
        elif self.low:
            return f'{self}({self.low.writetree()})'
        else:
            return f'{self}'

    @staticmethod
    def readtree(tree_str, G):
        """Read the strategy encoded in tree_str and build the corresponding decision tree.
        V(H, L) represents the tree with root node V, high subtree H, and low subtree L."""
        # TODO - write parser that constructs trees from Newick format strings
        stack = deque()
        prev = None
        current = None
        tree_str = tree_str.replace(' ', '')
        for token in re.split(r'', tree_str):
            if token is '(':
                pass
            elif token is ',':
                pass
            elif token is ')':
                pass
            else:
                current = BNode(G, token)



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

def getstratfast(G):
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
    high = getstratfast(A)
    low = getstratfast(B)

    # Construct optimal tree
    root = BNode(G, V)
    root.addchildren(low, high, n)
    return root


if __name__ == '__main__':
    map = 'sg'
    G = load_map(map)

    if False:
        plt.plot()
        plt.title(G.graph['name'])
        pos = nx.kamada_kawai_layout(G)
        pos_attrs = {node: (coord[0] - 0.08, coord[1] + 0.1) for (node, coord) in pos.items()}
        nx.draw_networkx(G, pos, edge_color='#888888', font_color='#ffffff')
        nx.draw_networkx_labels(G, pos_attrs, labels=nx.get_node_attributes(G, 'penalty'))
        plt.show()

    nodes = {name: BNode(G, name) for name in G.nodes}
    # build recommended strat tree in random order; objective function should be the same every time
    add_commands = ["nodes['d'].addchildren(None, nodes['c'])",
                    "nodes['d'].addchildren(None, nodes['c'])",
                    "nodes['e'].addchildren(None, nodes['d'])",
                    "nodes['g'].addchildren(None, nodes['a'])",
                    "nodes['i'].addchildren(None, nodes['b'])",
                    "nodes['h'].addchildren(nodes['i'], nodes['g'])",
                    "nodes['f'].addchildren(nodes['h'], nodes['e'])"]
    shuffle(add_commands)
    for command in add_commands:
        eval(command)
    recstrat = nodes['f']
    recstrat.calc_tree_obj()
    print(f'recommended strat: {recstrat.writetree()}')

    optstrat = getstratfast(G)
    print(f'algorithm\'s strat: {optstrat.writetree()}')
