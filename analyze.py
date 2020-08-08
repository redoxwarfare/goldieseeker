import matplotlib.pyplot as plt
import networkx as nx

from GusherNode import writetree, readtree
from getstrats import getstrat, getstratgreedy

import argparse
import warnings
from ast import literal_eval as l_eval
from statistics import mean, pstdev


# Special characters for parsing files
COMMENT_CHAR = '$'
DEFAULT_CHAR = '.'

# parser for input arguments
parser = argparse.ArgumentParser(add_help=False)
parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS,
                    help='Show this help message.')
parser.add_argument("map_id", nargs='*', help="name(s) of .txt file(s) in gusher graphs folder for map(s) to analyze")
parser.add_argument("-l", "--log", help="print log of search algorithm's internal process", action='store_true')


def load_graph(mapname):  # TODO - separate gusher map and penalty assignment(s) into 2 files
    """Create graph from the gusher layout and penalty values specified in external file."""
    path = f'gusher graphs/{mapname}.txt'
    G = nx.read_adjlist(path, comments=COMMENT_CHAR)

    # Assign penalties
    with open(path) as f:
        # Read the map name from the first line of the file
        name = f.readline().lstrip(COMMENT_CHAR + ' ')
        G.graph['name'] = name.rstrip()

        # Read the penalty dictionary from the second line of the file
        penalties = l_eval(f.readline().lstrip(COMMENT_CHAR + ' '))

        # For each node, check if its name is in any of the penalty groups and assign the corresponding penalty value
        # If no matches are found, assign the default penalty
        for node in G.nodes:
            penalty = penalties[DEFAULT_CHAR]
            for group in penalties:
                if node in group:
                    penalty = penalties[group]
                    break
            G.nodes[node]['penalty'] = penalty

    return G


def plot_graph(graph):
    plt.figure()
    plt.title(graph.graph['name'])
    pos = nx.kamada_kawai_layout(graph)
    pos_attrs = {node: (coord[0] - 0.08, coord[1] + 0.1) for (node, coord) in pos.items()}
    nx.draw_networkx(graph, pos, edge_color='#888888', font_color='#ffffff')
    nx.draw_networkx_labels(graph, pos_attrs, labels=nx.get_node_attributes(graph, 'penalty'))
    plt.show()


# TODO - start compilation of strategy variants for each map
recstrats = {'sg': 'f(e(d(c,),), h(g(a,), i(b,)))',
             'ap': 'f(g(e, c(d,)), g*(a, b))',
             'ss': 'f(d(b, g), e(c, a))',
             'mb': 'b(c(d(a,), e), c*(f, h(g,)))',
             'lo': 'g(h(i,), d(f(e,), a(c(b,),)))'}
mbhybrid = readtree('b(e(d, c(a,)), c*(f, h(g,)))', load_graph('mb'))
lostaysee = readtree('h(f(e, g(i,)), f*(d, a(c(b,),)))', load_graph('lo'))


def report(map_id, log=False):
    G = load_graph(map_id)
    print(f'\nMap: {G.graph["name"]}')

    if map_id in recstrats:
        recstrat = readtree(recstrats[map_id], G)
    else:
        recstrat = None
    greedystrat = getstratgreedy(G)
    narrowstrat = getstrat(G, wide=False, debug=log)
    optstrat = getstrat(G, debug=log)

    strats = {"greedy": greedystrat,
              "narrow": narrowstrat,
              "wide": optstrat,
              "recommended": recstrat}
    for desc in strats:
        strat = strats[desc]
        if strat:
            try:
                strat.validate()
            except AssertionError as e:
                print(f'validate() failed for {desc} strat with error "{e}"')
            strat.updatecost()
            costs = {str(g): g.cost for g in strat if g.findable}
            print(f'{desc} strat: {writetree(strat)}\n'
                  f'    objective score: {strat.obj}\n'
                  f'    costs: {{' + ', '.join(f'{node}: {costs[node]}' for node in costs) + '}\n' +
                  f'    mean cost: {mean(costs.values()):0.2f}, stdev: {pstdev(costs.values()):0.2f}')

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        print('(may need to close graph plot to continue)')
        plot_graph(G)


def main():
    args, other = parser.parse_known_args()
    stop = False
    while not stop:
        try:
            for map_id in args.map_id:
                report(map_id, args.log)
        except FileNotFoundError as e:
            print(f"Couldn't find {e.filename}!")

        input_str = input('Input map ID(s) or "quit" to quit: ')
        if input_str == "quit":
            stop = True
        else:
            try:
                args, other = parser.parse_known_args(input_str.split())
            except SystemExit:
                args.map_id = ()


if __name__ == '__main__':
    main()
