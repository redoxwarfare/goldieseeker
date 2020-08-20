from pyparsing import Regex, Forward, Suppress, Optional, Group

NEVER_FIND_FLAG = '*'


# TODO - try implementing threaded binary tree to improve performance?
class GusherNode:
    def __init__(self, name, weight=1, findable=True):
        self.name = name
        self.low = None  # next gusher to open if this gusher is low
        self.high = None  # next gusher to open if this gusher is high
        self.parent = None  # gusher previously opened in sequence
        self.findable = findable  # whether it is possible to find the Goldie at this gusher
        # if findable is False, the gusher is being opened solely for information (e.g. gusher C on Marooner's Bay)
        # non-findable nodes still count towards their children's costs, but don't count towards tree's objective score
        self.weight = weight  # penalty weight for this gusher
        self.distance = 1  # distance from parent gusher
        self.size = 1 if findable else 0  # number of findable nodes in subtree rooted at this node
        self.total_path_length = 0  # sum of lengths of each path between this node and one of its findable descendants
        self.cost = 0  # if Goldie is in this gusher, total penalty incurred by following decision tree
        self.total_cost = 0  # objective function evaluated on subtree with this node as root

    def __str__(self):
        return self.name + (NEVER_FIND_FLAG if not self.findable else "")

    def __repr__(self):
        return f'{{{str(self)} > ({self.high}, {self.low}), ' + \
               f'time: {self.total_path_length}, cost: {self.total_cost}}}'

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
            return self.name == other.name and self.weight == other.weight and self.findable == other.findable

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

    def add_children(self, high, low, dist_h=1, dist_l=1):
        size_h, size_l = 0, 0
        totpath_h, totpath_l = 0, 0
        obj_h, obj_l = 0, 0
        if high:
            assert not self.high, f'gusher {self} already has high child {self.high}'
            assert not high.parent, f'gusher {high} already has parent {high.parent}'
            self.high = high
            self.high.parent = self
            self.high.distance = dist_h
            size_h = self.high.size
            totpath_h = self.high.total_path_length
            obj_h = self.high.total_cost
        if low:
            assert not self.low, f'gusher {self} already has low child {self.low}'
            assert not low.parent, f'gusher {low} already has parent {low.parent}'
            self.low = low
            self.low.parent = self
            self.low.distance = dist_l
            size_l = self.low.size
            totpath_l = self.low.total_path_length
            obj_l = self.low.total_cost
        self.size = size_l + size_h + (1 if self.findable else 0)
        self.total_path_length = totpath_l + dist_l*size_l + totpath_h + dist_h*size_h
        self.total_cost = obj_l + obj_h + self.weight*self.total_path_length

    def update_costs(self, distances=None):
        """Update costs of this node's descendants. Should be called on root of tree."""
        def recurse(node, predecessor_penalties):
            if node.parent:
                node.cost = node.parent.cost + predecessor_penalties*node.distance
            else:
                node.cost = 0
            if node.high:
                if distances:
                    node.high.distance = distances[node.name][node.high.name]['weight']
                recurse(node.high, predecessor_penalties + node.weight)
            if node.low:
                if distances:
                    node.low.distance = distances[node.name][node.low.name]['weight']
                recurse(node.low, predecessor_penalties + node.weight)
        recurse(self, 0)

    def calc_tree_obj(self, distances=None):
        """Calculate and store the objective score of the tree rooted at this node."""
        self.update_costs(distances)
        self.total_cost = sum(node.cost for node in self if node.findable)

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
node = Regex(rf'\w+[{NEVER_FIND_FLAG}]?')
LPAREN, COMMA, RPAREN = map(Suppress, '(,)')
tree = Forward()
subtree = Group(Optional(tree))
subtrees = LPAREN + subtree.setResultsName('high') + COMMA + subtree.setResultsName('low') + RPAREN
tree << node.setResultsName('root') + Optional(subtrees)


def readtree(tree_str, connections, distances=None):
    """Read the strategy encoded in tree_str and build the corresponding decision tree.
    V(H, L) represents the tree with root node V, high subtree H, and low subtree L.
    A node name followed by * indicates that the gusher is being opened solely for information and the Goldie will
    never be found there."""

    def buildtree(tokens):  # recursively convert ParseResults object into GusherNode tree
        findable = tokens.root[-1] is not NEVER_FIND_FLAG
        rootname = tokens.root.rstrip(NEVER_FIND_FLAG)
        root = GusherNode(rootname, connections=connections, findable=findable)
        if tokens.high or tokens.low:
            high, low = None, None
            dist_h, dist_l = 1, 1
            if tokens.high:
                high = buildtree(tokens.high)
                if distances:
                    dist_h = distances[rootname][high.name]['weight']
            if tokens.low:
                low = buildtree(tokens.low)
                if distances:
                    dist_l = distances[rootname][low.name]['weight']
            root.add_children(high=high, low=low, dist_h=dist_h, dist_l=dist_l)
        return root

    tokens = tree.parseString(tree_str)
    root = buildtree(tokens)
    root.calc_tree_obj(distances)
    return root
