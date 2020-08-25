from GusherMap import GusherMap, split, BASKET_LABEL
from GusherNode import GusherNode, NEVER_FIND_FLAG, write_tree
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
            return GusherNode(list(suspected.nodes)[0], gusher_map=gusher_map)

        # Choose vertex V w/ lowest penalty and degree closest to n/2
        min_weight = min(gusher_map.weight(v) for v in suspected)
        candidates = [v for v in suspected if gusher_map.weight(v) == min_weight]
        vertex = min(candidates, key=lambda v: abs(suspected.degree[v] - n/2))

        # Build subtrees
        suspect_if_high, suspect_if_low = split(suspected, vertex)
        high = recurse(suspect_if_high)
        low = recurse(suspect_if_low)

        # Construct optimal tree
        root = GusherNode(vertex, gusher_map=gusher_map)
        root.add_children(high, low)
        return root

    return recurse(gusher_map.connections)


def get_strat(gushers, start=BASKET_LABEL, tuning=0.5, distances=True, weights=True, debug=False):
    """Build the optimal decision tree for a gusher map. Memoized algorithm."""
    def print_log(*args, **kwargs):
        if debug:
            print(*args, **kwargs)

    def distance(start, end):
        return gushers.distance(start, end) if distances else 1

    def weight(vertex):
        return gushers.weight(vertex) if weights else 1

    def score(latency, risk):
        return tuning*risk + (1-tuning)*latency

    def candidate_cost(candidate, latest_open):
        latency = candidate.total_latency + distance(latest_open, candidate.name)*candidate.size
        risk = candidate.total_risk + weight(latest_open)*latency
        return latency, risk

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
        key_str = f'({", ".join(str(u) for u in suspected)} | {", ".join(f"~{o}" for o in opened)})'
        if key in solved:  # Don't recalculate subtrees for subgraphs we've already solved
            candidates = deepcopy(solved[key])
        else:
            # Generate best subtrees for this subgraph
            search_set = set(gushers).difference(opened)
            for vertex in search_set:
                findable = vertex in suspected
                neighborhood = set(gushers.adj(vertex))
                if not findable and (neighborhood.issuperset(suspected) or neighborhood.isdisjoint(suspected)):
                    continue
                    # Don't open non-suspected gushers that are adjacent to all/none of the suspected gushers
                    # Opening them can neither find the Goldie nor provide additional information about the Goldie
                suspect_if_high, suspect_if_low = split(suspected, vertex, neighborhood)
                print_log(f'{key_str}; check gusher {vertex}{flag(findable)}\n'
                          f'    adj: {tuple(suspect_if_high)}\n'
                          f'    non-adj: {tuple(suspect_if_low)}')
                opened_new = opened.union({vertex})
                high = recurse(suspect_if_high, opened_new, vertex, solved)
                low = recurse(suspect_if_low, opened_new, vertex, solved)
                dist_h, dist_l = 1, 1
                if high:
                    dist_h = distance(vertex, high.name)
                if low:
                    dist_l = distance(vertex, low.name)
                root = GusherNode(vertex, gusher_map=gushers, findable=findable)
                root.add_children(high, low, dist_h, dist_l)
                candidates.append(root)
                print_log(f'subgraph: {key_str}\n'
                          f'    candidate solution: {write_tree(root)}\n'
                          f'    score: {score(root.total_latency, root.total_risk):g}\n')
            solved[key] = deepcopy(candidates)

        root = min(candidates, key=lambda tree: score(*candidate_cost(tree, latest_open)))
        print_log(f'{key_str}; options: \n' +
                  '\n'.join(f'    ~{latest_open}--{distance(latest_open, tree.name):g}--> ' +
                            f'{tree}({tree.high}, {tree.low}), ' +
                            f'raw score: {score(tree.total_latency, tree.total_risk):g}, ' +
                            f'final score: {score(*candidate_cost(tree, latest_open)):g}'
                            for tree in candidates) +
                  f'\n    choose gusher {root}: {write_tree(root)}')
        return root

    print_log(f"(U | ~O) means gushers in U could have Goldie, gushers in O have already been opened\n"
              f"------------------------------------------------------------------------------------")
    root = recurse(gushers.connections, set(), start, solved_subgraphs)
    root.update_costs(gushers, start=start)
    return root


if __name__ == '__main__':
    import cProfile
    G = GusherMap('lo')

    greedy = get_strat_greedy(G)
    strat = get_strat(G, debug=True)
    greedy.report(G, verbose=True)
    strat.report(G, verbose=True)

    def profile(n=1):
        for i in range(n):
            get_strat(G)

    cProfile.run('[profile(10)]', sort='cumulative')
