from pyparsing import Regex, Forward, Suppress, Optional, Group

NEVERFINDFLAG = '*'


class GusherNode:
    def __init__(self, name, graph=None, penalty=1, findable=True):  # graph is a networkx graph
        self.name = name
        self.low = None  # next gusher to open if this gusher is low
        self.high = None  # next gusher to open if this gusher is high
        self.parent = None  # gusher previously opened in sequence
        self.findable = findable  # whether it is possible to find the Goldie at this gusher
        # if findable is False, the gusher is being opened solely for information (e.g. gusher C on Marooner's Bay)
        # non-findable nodes still count towards their children's costs, but don't count towards tree's objective score
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

    def __iter__(self):
        yield self
        if self.high:
            yield from self.high.__iter__()
        if self.low:
            yield from self.low.__iter__()

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

    def updatecost(self):
        """Update costs of node and its children."""
        for node in self:
            if node.parent:
                node.cost = node.parent.cost + node.parent.penalty

    def calc_tree_obj(self):
        """Calculate and store the objective score of the tree rooted at this node."""
        self.updatecost()
        self.obj = sum(node.cost for node in self if node.findable)


def writetree(root):
    """Write the strategy encoded by the subtree rooted at 'root' in modified Newick format.
    V(H, L) represents the tree with root node V, high subtree H, and low subtree L.
    A node name followed by * indicates that the gusher is being opened solely for information and the Goldie will
    never be found there."""
    flag = '' if root.findable else NEVERFINDFLAG
    if root.high and root.low:
        return f'{root}{flag}({writetree(root.high)}, {writetree(root.low)})'
    elif root.high:
        return f'{root}{flag}({writetree(root.high)},)'
    elif root.low:
        return f'{root}{flag}(,{writetree(root.low)})'
    else:
        return f'{root}{flag}'


# Decision tree grammar
node = Regex(rf'\w+[{NEVERFINDFLAG}]?')
LPAREN, COMMA, RPAREN = map(Suppress, '(,)')
tree = Forward()
subtree = Group(Optional(tree))
subtrees = LPAREN + subtree.setResultsName('high') + COMMA + subtree.setResultsName('low') + RPAREN
tree << node.setResultsName('root') + Optional(subtrees)


def readtree(tree_str, graph):
    """Read the strategy encoded in tree_str and build the corresponding decision tree.
    V(H, L) represents the tree with root node V, high subtree H, and low subtree L.
    A node name followed by * indicates that the gusher is being opened solely for information and the Goldie will
    never be found there."""
    def buildtree(tokens):  # recursively convert ParseResults object into GusherNode tree
        findable = tokens.root[-1] is not NEVERFINDFLAG
        rootname = tokens.root if findable else tokens.root.rstrip(NEVERFINDFLAG)
        root = GusherNode(rootname, graph=graph, findable=findable)
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
