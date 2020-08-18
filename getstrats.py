import networkx as nx
from ast import literal_eval
from numpy import genfromtxt
from GusherNode import GusherNode, writetree, readtree
from GusherNode import NEVER_FIND_FLAG
from copy import deepcopy


# Special characters for parsing files
COMMENT_CHAR = '$'
DEFAULT_CHAR = '.'
BASKET_LABEL = '@'


# Function for converting node labels from numbers to letters
def nums_to_alpha(size):
    return lambda i: 'abcdefghijklmnopqrstuvwxyz'[i] if i < size else BASKET_LABEL


def flag(findable):
    if findable:
        return ""
    else:
        return NEVER_FIND_FLAG


# TODO - separate penalty assignments into their own files
def load_graph(mapname):
    """Create connections graph from the gusher layout and penalty values specified in mapname/connections.txt, and
    create distances weighted digraph from the adjacency matrix specified in mapname/distances.txt."""
    connections_path = f'gusher graphs/{mapname}/connections.txt'
    distances_path = f'gusher graphs/{mapname}/distances.txt'

    connections = nx.read_adjlist(connections_path, comments=COMMENT_CHAR)
    # Assign penalties
    with open(connections_path) as f:
        # Read the map name from the first line of the file
        name = f.readline().lstrip(COMMENT_CHAR + ' ')
        connections.graph['name'] = name.rstrip()

        # Read the penalty dictionary from the second line of the file
        penalties = literal_eval(f.readline().lstrip(COMMENT_CHAR + ' '))

        # For each node, check if its name is in any of the penalty groups and assign the corresponding penalty value
        # If no matches are found, assign the default penalty
        for node in connections.nodes:
            penalty = penalties[DEFAULT_CHAR]
            for group in penalties:
                if node in group:
                    penalty = penalties[group]
                    break
            connections.nodes[node]['penalty'] = penalty

    try:
        distances_raw = genfromtxt(distances_path, delimiter=', ', comments=COMMENT_CHAR)
        distances = nx.from_numpy_array(distances_raw[:, 1:], create_using=nx.DiGraph)
        assert len(distances) == len(connections) + 1, \
            f'distances matrix is {len(distances)}x{len(distances)} ' + \
            f'but connections graph has {len(connections)} vertices'
        # noinspection PyTypeChecker
        nx.relabel_nodes(distances, nums_to_alpha(len(connections)), False)
    except:
        distances = None
    return connections, distances


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
        return GusherNode(list(suspected.nodes)[0], connections=suspected)

    # Choose vertex V w/ lowest penalty and degree closest to n/2
    minpenalty = min([suspected.nodes[g]['penalty'] for g in suspected])
    candidates = [v for v in suspected if suspected.nodes[v]['penalty'] == minpenalty]
    vertex = min(candidates, key=lambda v: abs(suspected.degree[v] - n/2))

    # Build subtrees
    suspect_if_high, suspect_if_low = splitgraph(suspected, vertex)
    high = getstratgreedy(suspect_if_high)
    low = getstratgreedy(suspect_if_low)

    # Construct optimal tree
    root = GusherNode(vertex, connections=suspected)
    root.add_children(high, low)
    return root


def getstrat(connections, distances=None, wide=True, start=BASKET_LABEL, debug=False):
    """Build the optimal decision tree for a gusher graph. Memoized algorithm.
    "Wide" trees may contain nodes where the Goldie can never be found ("unfindable" nodes), which are marked with *.
    "Narrow" trees contain only findable nodes."""
    def printlog(*args, **kwargs):
        if debug:
            print(*args, **kwargs)

    def penalty(gusher):
        if gusher != BASKET_LABEL:
            return connections.nodes[gusher]['penalty']
        else:
            return 0

    def distance(start, end):
        if distances:
            return distances[start][end]['weight']
        else:
            return 1

    def score_candidate(candidate, latest_open):
        return candidate.obj + penalty(latest_open)*(candidate.total_path_length +
                                                     distance(latest_open, candidate.name))

    solved_subgraphs = dict()
    # dict that associates a subgraph with its solution subtrees and their objective scores
    # stores deep copies of trees to avoid entangling references between different candidates

    def recurse(suspected, opened, latest_open, solved):
        """Return the optimal subtree to follow given a set of suspected gushers, a set of opened gushers,
        and the most recently opened gusher."""
        # First 3 arguments refer to gushers using strings, but recurse() returns a GusherNode
        # suspected = subgraph of unopened gushers that might have the Goldie
        # opened = set of opened gushers
        # latest_open = most recently opened gusher

        # Base cases
        n = len(suspected)
        if n == 0:
            return None
        if n == 1:
            return GusherNode(list(suspected.nodes)[0], connections)

        candidates = list()
        key = (frozenset(suspected), frozenset(opened))
        key_str = f'({", ".join(str(u) for u in suspected)}{" | " if wide else ""}' + \
                  f'{", ".join(f"~{o}" for o in opened)})'
        if key in solved:  # Don't recalculate subtrees for subgraphs we've already solved
            candidates = deepcopy(solved[key])
        else:
            # Generate best subtrees for this subgraph
            if wide:  # Wide strategies consider all unopened gushers
                search_set = set(connections).difference(opened)
            else:  # Narrow strategies consider only suspected gushers
                search_set = set(suspected)
            for vertex in search_set:
                findable = vertex in suspected
                adj = set(connections.adj[vertex])
                if not findable and (adj.issuperset(suspected) or adj.isdisjoint(suspected)):
                    continue
                    # Don't open non-suspected gushers that are adjacent to all/none of the suspected gushers
                    # Opening them can neither find the Goldie nor provide additional information about the Goldie
                suspect_if_high, suspect_if_low = splitgraph(suspected, vertex, adj)
                printlog(f'{key_str}; check gusher {vertex}{flag(findable)}\n'
                         f'    adj: {tuple(suspect_if_high)}\n'
                         f'    non-adj: {tuple(suspect_if_low)}')
                opened_new = opened.union(set(vertex)) if wide else opened
                high = recurse(suspect_if_high, opened_new, vertex, solved)
                low = recurse(suspect_if_low, opened_new, vertex, solved)
                dist_h, dist_l = 1, 1
                if distances:
                    if high:
                        dist_h = distance(vertex, high.name)
                    if low:
                        dist_l = distance(vertex, low.name)
                root = GusherNode(vertex, connections, findable=findable)
                root.add_children(high, low, dist_h, dist_l)
                candidates.append(root)
                printlog(f'subgraph #{len(solved):4d}: {key_str}\n'
                         f'    candidate solution: {writetree(root)}\n'
                         f'    score: {root.obj}\n')
            solved[key] = deepcopy(candidates)

        root = min(candidates, key=lambda cand: score_candidate(cand, latest_open))
        printlog(f'{key_str}; options: \n' +
                 '\n'.join(f'    {tree} > ({tree.high}, {tree.low}), ' +
                           f'score: {tree.obj}, {latest_open}-{tree.name} distance: {distance(latest_open, tree.name)}'
                           for tree in candidates) +
                 f'\n    choose gusher {root}')
        return root

    printlog(f"\nWIDE SEARCH\n"
             f"(U | ~O) means gushers in U could have Goldie, gushers in O have already been opened\n"
             f"------------------------------------------------------------------------------------" if wide else
             f"\nNARROW SEARCH\n"
             f"(U) means gushers in U could have Goldie\n"
             f"-------------------------------------------")
    root = recurse(connections, set(), start, solved_subgraphs)
    root.update_costs(distances)
    return root


if __name__ == '__main__':
    import cProfile
    G, dist = load_graph('lo')

    greedy = getstratgreedy(G)
    greedy.calc_tree_obj(dist)
    strat = getstrat(G, debug=True)
    strat.calc_tree_obj(dist)
    strat2 = getstrat(G, dist, debug=True)
    lo_fh = readtree('f(d(e, h), h*(g(i,), a(c(b,),)))', G, dist)
    lo_min = readtree('h(e(f(,i), g), a(c(b,), d))', G, dist)
    print(f'greedy ({greedy.obj}): {writetree(greedy)}\n    { {node.name: node.cost for node in greedy} }')
    print(f'w/o distances ({strat.obj}): {writetree(strat)}\n    { {node.name: node.cost for node in strat} }')
    print(f'w/ distances ({strat2.obj}): {writetree(strat2)} \n    { {node.name: node.cost for node in strat2} }')
    print(f'FH ({lo_fh.obj}): {writetree(lo_fh)} \n    { {node.name: node.cost for node in lo_fh} }')
    print(f'min ({lo_min.obj}): {writetree(lo_min)} \n    { {node.name: node.cost for node in lo_min} }')

    def profile(n=1):
        for i in range(n):
            getstrat(G, dist)

    cProfile.run('[profile(10)]', sort='cumulative')
