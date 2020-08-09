import networkx as nx
from ast import literal_eval
from GusherNode import GusherNode, writetree
from GusherNode import NEVER_FIND_FLAG
from copy import deepcopy


# Special characters for parsing files
COMMENT_CHAR = '$'
DEFAULT_CHAR = '.'


def flag(findable):
    if findable:
        return ""
    else:
        return NEVER_FIND_FLAG


def load_graph(mapname):  # TODO - separate gusher map and penalty assignment(s) into 2 files
    """Create graph from the gusher layout and penalty values specified in external file."""
    path = f'gusher graphs/{mapname}.txt'
    graph = nx.read_adjlist(path, comments=COMMENT_CHAR)

    # Assign penalties
    with open(path) as f:
        # Read the map name from the first line of the file
        name = f.readline().lstrip(COMMENT_CHAR + ' ')
        graph.graph['name'] = name.rstrip()

        # Read the penalty dictionary from the second line of the file
        penalties = literal_eval(f.readline().lstrip(COMMENT_CHAR + ' '))

        # For each node, check if its name is in any of the penalty groups and assign the corresponding penalty value
        # If no matches are found, assign the default penalty
        for node in graph.nodes:
            penalty = penalties[DEFAULT_CHAR]
            for group in penalties:
                if node in group:
                    penalty = penalties[group]
                    break
            graph.nodes[node]['penalty'] = penalty

    return graph


def splitgraph(graph, vertex, adj=None):
    """Split graph into two subgraphs: nodes adjacent to vertex V, and nodes not adjacent to V."""
    if not adj:
        adj = graph.adj[vertex]
    adj_subgraph = graph.subgraph(adj)  # subgraph of vertices adjacent to V

    nonadj = set(graph).difference(adj_subgraph)
    nonadj = nonadj.difference(set(vertex))
    nonadj_subgraph = graph.subgraph(nonadj)  # subgraph of vertices non-adjacent to V (excluding V)

    return adj_subgraph, nonadj_subgraph


def getstratgreedy(suspected):
    """Build a decision tree for the gusher graph. Greedy algorithm not guaranteed to find the optimal tree,
    but should still return something decent."""
    n = len(suspected)
    # Base cases
    if n == 0:
        return None
    if n == 1:
        return GusherNode(list(suspected.nodes)[0], graph=suspected)

    # Choose vertex V w/ lowest penalty and degree closest to n/2
    minpenalty = min([suspected.nodes[g]['penalty'] for g in suspected])
    candidates = [v for v in suspected if suspected.nodes[v]['penalty'] == minpenalty]
    vertex = min(candidates, key=lambda v: abs(suspected.degree[v] - n/2))

    # Build subtrees
    suspect_if_high, suspect_if_low = splitgraph(suspected, vertex)
    high = getstratgreedy(suspect_if_high)
    low = getstratgreedy(suspect_if_low)

    # Construct optimal tree
    root = GusherNode(vertex, graph=suspected)
    root.addchildren(high, low, n)
    return root


def getstrat(graph, wide=True, debug=False):
    """Build the optimal decision tree for a gusher graph. Memoized algorithm.
    "Wide" trees may contain nodes where the Goldie can never be found ("unfindable" nodes), which are marked with *.
    "Narrow" trees contain only findable nodes."""

    def printlog(*args, **kwargs):
        if debug:
            print(*args, **kwargs)

    subgraphs = dict()
    # dict for associating subgraphs with their corresponding optimal subtrees and objective scores
    # stores optimal subtrees as strings to avoid entangling references between different candidate subtrees

    def recurse(suspected, opened, subgraphs):
        # suspected = subgraph of unopened gushers that might have the Goldie
        # opened = set of opened gushers
        key = (frozenset(suspected), frozenset(opened))
        if key in subgraphs:  # don't recalculate optimal trees for subgraphs we've already solved
            return deepcopy(subgraphs[key])
        key_str = f'({", ".join(str(u) for u in suspected)}{" | " if wide else ""}{", ".join(f"~{o}" for o in opened)})'

        root = None
        obj = 0
        n = len(suspected)
        if n == 1:  # Base case
            root = GusherNode(list(suspected.nodes)[0], graph)
        elif n > 1:
            if wide:  # Wide strategies consider all unopened gushers
                search_set = set(graph).difference(opened)
            else:  # Narrow strategies consider only suspected gushers
                search_set = set(suspected)
            candidates = dict()  # For each possible root vertex, store objective score for resulting tree
            for vertex in search_set:
                findable = vertex in suspected
                adj = set(graph.adj[vertex])
                # Don't open non-suspected gushers that are adjacent to all/none of the suspected gushers
                # Opening them can neither find the Goldie nor provide additional information about the Goldie
                if not findable and (adj.issuperset(suspected) or adj.isdisjoint(suspected)):
                    continue
                suspect_if_high, suspect_if_low = splitgraph(suspected, vertex, adj)
                printlog(f'{key_str}; check gusher {vertex}{flag(findable)}\n'
                         f'    adj: {tuple(suspect_if_high)}\n'
                         f'    non-adj: {tuple(suspect_if_low)}')
                opened_new = opened.union(set(vertex)) if wide else opened
                high = recurse(suspect_if_high, opened_new, subgraphs)
                low = recurse(suspect_if_low, opened_new, subgraphs)
                obj_h, size_h = 0, 0
                obj_l, size_l = 0, 0
                if high:
                    obj_h, size_h = high.obj, high.size
                if low:
                    obj_l, size_l = low.obj, low.size
                vertex_penalty = graph.nodes[vertex]['penalty']
                cand_obj = (size_h + size_l)*vertex_penalty + obj_h + obj_l
                candidates[vertex] = (cand_obj, high, low, findable)

            printlog(f'{key_str}; options: \n' +
                     '\n'.join(f'    {V}{flag(t[3])} > ({t[1]}, {t[2]}), score: {t[0]}'
                               for V, t in candidates.items()))
            vertex = min(candidates, key=lambda g: candidates[g][0])  # Choose the vertex that minimizes objective score
            obj, high, low, findable = candidates[vertex]

            # Build tree
            root = GusherNode(vertex, graph, findable=findable)
            root.addchildren(high, low)
            printlog(f'    choose gusher {root}')

        if root:
            root.obj = obj  # Don't need calc_tree_obj since calculations are done as part of tree-finding process
            if root.high or root.low:  # Only store solutions for subgraphs of size 2 or more
                solution = deepcopy(root)
                subgraphs[key] = solution
                printlog(f'subgraph #{len(subgraphs):4d}: {key_str}\n'
                         f'     solution: {writetree(root)}\n'
                         f'        score: {root.obj}\n')
        return root

    printlog(f"\nWIDE SEARCH\n"
             f"(U | ~O) means gushers in U could have Goldie, gushers in O have already been opened\n"
             f"------------------------------------------------------------------------------------" if wide else
             f"\nNARROW SEARCH\n"
             f"(U) means gushers in U could have Goldie\n"
             f"-------------------------------------------")
    root = recurse(graph, set(), subgraphs)
    root.updatecost()
    return root


if __name__ == '__main__':
    import cProfile
    from analyze import load_graph
    G = load_graph('sg')

    def profile(n=1):
        for i in range(n):
            getstrat(G)

    cProfile.run('[profile(10)]', sort='cumulative')
