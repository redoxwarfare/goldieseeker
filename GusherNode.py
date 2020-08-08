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
        self.size = 1 if findable else 0  # number of findable nodes in subtree rooted at this node
        if graph:
            self.penalty = graph.nodes[name]['penalty']  # penalty for opening this gusher
        else:
            self.penalty = penalty
        self.cost = 0  # if Goldie is in this gusher, total penalty incurred by following decision tree
        self.obj = 0  # objective function evaluated on subtree with this node as root

    def __str__(self):
        return self.name+(NEVERFINDFLAG if not self.findable else "")

    def __repr__(self):
        return f'{{{str(self)} > ({self.high}, {self.low}), '+ \
               f'p: {self.penalty}, c: {self.cost}, o: {self.obj}}}'

    def __iter__(self):
        yield self
        if self.high:
            yield from self.high.__iter__()
        if self.low:
            yield from self.low.__iter__()

    def __eq__(self, other):
        if not other:
            return False
        else:
            return self.name == other.name and self.penalty == other.penalty and self.findable == other.findable

    def sametree(self, other):
        if not other:
            return False
        if not (self == other):
            return False
        if self.high:
            samehigh = self.high.sametree(other.high)
        else:
            samehigh = not other.high
        if self.low:
            samelow = self.low.sametree(other.low)
        else:
            samelow = not other.low
        return samehigh and samelow

    def addchildren(self, high, low, n=0):
        objL, objH = 0, 0
        sizeL, sizeH = 0, 0
        if low:
            assert not self.low, f'gusher {self} already has low child {self.low}'
            assert not low.parent, f'gusher {low} already has parent {low.parent}'
            self.low = low
            self.low.parent = self
            objL = self.low.obj
            sizeL = self.low.size
        if high:
            assert not self.high, f'gusher {self} already has high child {self.high}'
            assert not high.parent, f'gusher {high} already has parent {high.parent}'
            self.high = high
            self.high.parent = self
            objH = self.high.obj
            sizeH = self.high.size
        if n:
            self.obj = self.penalty * (n - 1) + objL + objH
        self.size = sizeL+sizeH+(1 if self.findable else 0)

    def updatecost(self):
        """Update costs of node and its children."""
        for node in self:
            if node.parent:
                node.cost = node.parent.cost + node.parent.penalty

    def calc_tree_obj(self):
        """Calculate and store the objective score of the tree rooted at this node."""
        self.updatecost()
        self.obj = sum(node.cost for node in self if node.findable)

    def validate(self):
        """Check that tree is a valid strategy."""
        def recurse(node, predecessors):
            # can't open the same gusher twice
            assert str(node) not in predecessors, f'node {node} found in own predecessors: {predecessors}'

            if node.high or node.low:
                pred_new = predecessors.copy()
                pred_new.add(str(node))

                # make sure parent/child references are consistent
                if node.high:
                    assert node.high.parent == node, f'node {node}, node.high {node.high}, ' \
                                                     f'node.high.parent {node.high.parent}'
                    recurse(node.high, pred_new)
                if node.low:
                    assert node.low.parent == node, f'node {node}, node.low {node.high}, ' \
                                                    f'node.low.parent {node.low.parent}'
                    recurse(node.low, pred_new)
        recurse(self, set())


def writetree(root):
    """Write the strategy encoded by the subtree rooted at 'root' in modified Newick format.
    V(H, L) represents the tree with root node V, high subtree H, and low subtree L.
    A node name followed by * indicates that the gusher is being opened solely for information and the Goldie will
    never be found there."""
    if root.high and root.low:
        return f'{root}({writetree(root.high)}, {writetree(root.low)})'
    elif root.high:
        return f'{root}({writetree(root.high)},)'
    elif root.low:
        return f'{root}(,{writetree(root.low)})'
    else:
        return f'{root}'


# Decision tree grammar
node = Regex(rf'\w+[{NEVERFINDFLAG}]?')
LPAREN, COMMA, RPAREN = map(Suppress, '(,)')
tree = Forward()
subtree = Group(Optional(tree))
subtrees = LPAREN + subtree.setResultsName('high') + COMMA + subtree.setResultsName('low') + RPAREN
tree << node.setResultsName('root') + Optional(subtrees)


def readtree(tree_str, graph, obj=0):
    """Read the strategy encoded in tree_str and build the corresponding decision tree.
    V(H, L) represents the tree with root node V, high subtree H, and low subtree L.
    A node name followed by * indicates that the gusher is being opened solely for information and the Goldie will
    never be found there."""
    def buildtree(tokens):  # recursively convert ParseResults object into GusherNode tree
        findable = tokens.root[-1] is not NEVERFINDFLAG
        root = GusherNode(tokens.root.rstrip(NEVERFINDFLAG), graph=graph, findable=findable)
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
    if obj:
        root.obj = obj
    else:
        root.calc_tree_obj()
    return root
