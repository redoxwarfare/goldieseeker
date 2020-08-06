from pyparsing import alphanums, Word, Forward, Suppress, Optional, Group


class GusherNode:
    def __init__(self, name, graph=None, penalty=1):  # graph is a networkx graph
        self.name = name
        self.low = None  # next gusher to open if this gusher is low
        self.high = None  # next gusher to open if this gusher is high
        self.parent = None  # gusher previously opened in sequence
        if graph:
            self.penalty = graph.nodes[name]['penalty']  # penalty for opening this gusher
        else:
            self.penalty = penalty
        self.cost = 0  # if Goldie is in this gusher, total penalty incurred by following decision tree
        self.obj = 0  # objective function evaluated on subtree with this node as root

    def __str__(self):
        return self.name

    def __repr__(self):
        return f'{{{self.name} > ({self.high}, {self.low}), p: {self.penalty}, c: {self.cost}, o: {self.obj}}}'

    def addchildren(self, high, low, n=0):
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


def writetree(root):
    """Write the strategy encoded by the subtree rooted at 'root' in modified Newick format.
    V(H, L) represents the tree with root node V, high subtree H, and low subtree L."""
    if root.high and root.low:
        return f'{root}({writetree(root.high)}, {writetree(root.low)})'
    elif root.high:
        return f'{root}({writetree(root.high)},)'
    elif root.low:
        return f'{root}(,{writetree(root.low)})'
    else:
        return f'{root}'


# Decision tree grammar
node = Word(alphanums)
LPAREN, COMMA, RPAREN = map(Suppress, '(,)')
tree = Forward()
subtree = Group(Optional(tree))
subtrees = LPAREN + subtree.setResultsName('high') + COMMA + subtree.setResultsName('low') + RPAREN
tree << node.setResultsName('root') + Optional(subtrees)


def readtree(tree_str, graph):
    """Read the strategy encoded in tree_str and build the corresponding decision tree.
    V(H, L) represents the tree with root node V, high subtree H, and low subtree L."""
    def buildtree(tokens):  # recursively convert ParseResults object into GusherNode tree
        root = GusherNode(tokens.root, graph=graph)
        if tokens.high or tokens.low:
            high = None
            low = None
            if tokens.high:
                high = buildtree(tokens.high)
            if tokens.low:
                low = buildtree(tokens.low)
            root.addchildren(high=high, low=low)
        return root

    tokens = tree.parseString(tree_str)
    root = buildtree(tokens)
    root.calc_tree_obj()
    return root
