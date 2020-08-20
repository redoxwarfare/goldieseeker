from GusherMap import GusherMap, split, BASKET_LABEL
from GusherNode import GusherNode, write_tree
from GusherNode import NEVER_FIND_FLAG
from copy import deepcopy


def flag(findable):
    if findable:
        return ""
    else:
        return NEVER_FIND_FLAG


def get_strat_greedy(gusher_map):
    """Build a decision tree for the gusher gushers. Greedy algorithm not guaranteed to find the optimal tree,
    but should still return something decent."""
    def recurse(suspected):
        n = len(suspected)
        # Base cases
        if n == 0:
            return None
        if n == 1:
            return GusherNode(list(suspected.nodes)[0], map=gusher_map)

        # Choose vertex V w/ lowest penalty and degree closest to n/2
        min_weight = min(gusher_map.weight(v) for v in suspected)
        candidates = [v for v in suspected if gusher_map.weight(v) == min_weight]
        vertex = min(candidates, key=lambda v: abs(suspected.degree[v] - n/2))

        # Build subtrees
        suspect_if_high, suspect_if_low = split(suspected, vertex)
        high = recurse(suspect_if_high)
        low = recurse(suspect_if_low)

        # Construct optimal tree
        root = GusherNode(vertex, map=gusher_map)
        root.add_children(high, low)
        return root

    return recurse(gusher_map.connections)


def get_strat(gushers, start=BASKET_LABEL, distances=True, weights=True, wide=True, debug=False):
    """Build the optimal decision tree for a gusher map. Memoized algorithm.
    "Wide" trees may contain nodes where the Goldie can never be found ("unfindable" nodes), which are marked with *.
    "Narrow" trees contain only findable nodes."""
    def print_log(*args, **kwargs):
        if debug:
            print(*args, **kwargs)

    def distance(start, end):
        return gushers.distance(start, end) if distances else 1

    def weight(vertex):
        return gushers.weight(vertex) if weights else 1

    def score_candidate(candidate, latest_open):
        cand_dist = distance(latest_open, candidate.name)
        latency = candidate.total_latency + cand_dist
        risk = candidate.total_risk + weight(latest_open)*(candidate.total_latency + cand_dist*candidate.size)
        return latency + risk

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
            return GusherNode(list(suspected.nodes)[0], gushers)

        candidates = list()
        key = (frozenset(suspected), frozenset(opened))
        key_str = f'({", ".join(str(u) for u in suspected)}{" | " if wide else ""}' + \
                  f'{", ".join(f"~{o}" for o in opened)})'
        if key in solved:  # Don't recalculate subtrees for subgraphs we've already solved
            candidates = deepcopy(solved[key])
        else:
            # Generate best subtrees for this subgraph
            if wide:  # Wide strategies consider all unopened gushers
                search_set = set(gushers).difference(opened)
            else:  # Narrow strategies consider only suspected gushers
                search_set = set(suspected)
            for vertex in search_set:
                findable = vertex in suspected
                neighbors = set(gushers.adj(vertex))
                if not findable and (neighbors.issuperset(suspected) or neighbors.isdisjoint(suspected)):
                    continue
                    # Don't open non-suspected gushers that are adjacent to all/none of the suspected gushers
                    # Opening them can neither find the Goldie nor provide additional information about the Goldie
                suspect_if_high, suspect_if_low = split(suspected, vertex, neighbors)
                print_log(f'{key_str}; check gusher {vertex}{flag(findable)}\n'
                          f'    adj: {tuple(suspect_if_high)}\n'
                          f'    non-adj: {tuple(suspect_if_low)}')
                opened_new = opened.union(set(vertex)) if wide else opened
                high = recurse(suspect_if_high, opened_new, vertex, solved)
                low = recurse(suspect_if_low, opened_new, vertex, solved)
                dist_h, dist_l = 1, 1
                if high:
                    dist_h = distance(vertex, high.name)
                if low:
                    dist_l = distance(vertex, low.name)
                root = GusherNode(vertex, map=gushers, findable=findable)
                root.add_children(high, low, dist_h, dist_l)
                candidates.append(root)
                print_log(f'subgraph: {key_str}\n'
                          f'    candidate solution: {write_tree(root)}\n'
                          f'    score: {root.total_latency + root.total_risk:g}\n')
            solved[key] = deepcopy(candidates)

        root = min(candidates, key=lambda cand: score_candidate(cand, latest_open))
        print_log(f'{key_str}; options: \n' +
                  '\n'.join(f'    ~{latest_open}--{distance(latest_open, tree.name):g}--> ' +
                            f'{tree}({tree.high}, {tree.low}), raw score: {tree.total_risk + tree.total_latency:g}, ' +
                            f'final score: {score_candidate(tree, latest_open):g}'
                            for tree in candidates) +
                  f'\n    choose gusher {root}: {write_tree(root)}')
        return root

    print_log(f"\nWIDE SEARCH\n"
              f"(U | ~O) means gushers in U could have Goldie, gushers in O have already been opened\n"
              f"------------------------------------------------------------------------------------" if wide else
              f"\nNARROW SEARCH\n"
              f"(U) means gushers in U could have Goldie\n"
              f"-------------------------------------------")
    root = recurse(gushers.connections, set(), start, solved_subgraphs)
    root.update_costs(gushers, start=start)
    return root


if __name__ == '__main__':
    import cProfile
    G = GusherMap('lo')

    greedy = get_strat_greedy(G)
    greedy.calc_tree_total_cost(G)
    strat = get_strat(G, distances=False, debug=True)
    strat.calc_tree_total_cost(G)
    strat2 = get_strat(G, debug=True)
    print(f'greedy ({greedy.total_risk}): {write_tree(greedy)}\n    { {node.name: node.risk for node in greedy} }')
    print(f'w/o distances ({strat.total_risk}): {write_tree(strat)}\n    { {node.name: node.risk for node in strat} }')
    print(f'w/ distances ({strat2.total_risk}): {write_tree(strat2)}\n' +
          f'    { {node.name: node.risk for node in strat2} }')

    def profile(n=1):
        for i in range(n):
            get_strat(G)

    cProfile.run('[profile(10)]', sort='cumulative')
