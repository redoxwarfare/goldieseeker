import networkx as nx
from ast import literal_eval
from numpy import genfromtxt
from GusherNode import GusherNode, writetree
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

    distances_raw = genfromtxt(distances_path, delimiter=', ', comments=COMMENT_CHAR)
    distances = nx.from_numpy_array(distances_raw[:, 1:], create_using=nx.DiGraph)
    assert len(distances) == len(connections) + 1, \
        f'distances matrix is {len(distances)}x{len(distances)} but connections graph has {len(connections)} vertices'
    nx.relabel_nodes(distances, nums_to_alpha(len(connections)), False)
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


def getstrat(connections, distances=None, wide=True, debug=False):
    """Build the optimal decision tree for a gusher graph. Memoized algorithm.
    "Wide" trees may contain nodes where the Goldie can never be found ("unfindable" nodes), which are marked with *.
    "Narrow" trees contain only findable nodes."""
    def printlog(*args, **kwargs):
        if debug:
            print(*args, **kwargs)

    # if not distances:
    #     distances = nx.complete_graph(len(connections)+1)
    #     nx.relabel_nodes(distances, nums_to_alpha(len(connections)), copy=False)
    #     nx.set_edge_attributes(distances, 1, name='distance')

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
            root = GusherNode(list(suspected.nodes)[0], connections)
        elif n > 1:
            if wide:  # Wide strategies consider all unopened gushers
                search_set = set(connections).difference(opened)
            else:  # Narrow strategies consider only suspected gushers
                search_set = set(suspected)
            candidates = dict()  # For each possible root vertex, store objective score for resulting tree
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
                high = recurse(suspect_if_high, opened_new, subgraphs)
                low = recurse(suspect_if_low, opened_new, subgraphs)
                size_h, dist_h, totpath_h, obj_h = 0, 1, 0, 0
                size_l, dist_l, totpath_l, obj_l = 0, 1, 0, 0
                if high:
                    size_h, totpath_h, obj_h = high.size, high.total_path_length, high.obj
                    if distances:
                        dist_h = distances[vertex][high.name]['weight']
                if low:
                    size_l, totpath_l, obj_l = low.size, low.total_path_length, low.obj
                    if distances:
                        dist_l = distances[vertex][low.name]['weight']
                vertex_penalty = connections.nodes[vertex]['penalty']
                cand_obj = obj_h + obj_l + vertex_penalty*(totpath_h + totpath_l + dist_h*size_h + dist_l*size_l)
                candidates[vertex] = (cand_obj, high, low, findable)

            printlog(f'{key_str}; options: \n' +
                     '\n'.join(f'    {V}{flag(t[3])} > ({t[1]}, {t[2]}), score: {t[0]}'
                               for V, t in candidates.items()))
            vertex = min(candidates, key=lambda g: candidates[g][0])  # Choose the vertex that minimizes objective score
            obj, high, low, findable = candidates[vertex]

            # Build tree
            root = GusherNode(vertex, connections, findable=findable)
            root.add_children(high, low)
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
    root = recurse(connections, set(), subgraphs)
    root.update_costs()
    return root


if __name__ == '__main__':
    import cProfile
    G, dist = load_graph('lo')

    strat = getstrat(G, debug=True)
    strat2 = getstrat(G, dist, debug=True)
    print(f'equal travel time: {writetree(strat)}\n    { {node.name: node.cost for node in strat} }')
    print(f'unequal travel time: {writetree(strat2)} \n    { {node.name: node.cost for node in strat2} }')

    def profile(n=1):
        for i in range(n):
            getstrat(G, dist)

    cProfile.run('[profile(10)]', sort='cumulative')
