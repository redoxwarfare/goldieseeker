import matplotlib.pyplot as plt
import networkx as nx

from GusherNode import writetree, readtree
from getstrats import getstrat, getstratgreedy, load_graph

import argparse
import warnings
from statistics import mean, pstdev


# parser for input arguments
parser = argparse.ArgumentParser(add_help=False)
parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS,
                    help='Show this help message.')
parser.add_argument("map_id", nargs='*', help="name(s) of .txt file(s) in gusher graphs folder for map(s) to analyze")
parser.add_argument("--log", help="print log of search algorithm's internal process", action='store_true')
parser.add_argument("--plot", help="display gusher graph", action='store_true')


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


def report(map_id, log=False, plot=False):
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

    if plot:
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
                report(map_id, args.log, args.plot)
        except FileNotFoundError as e:
            print(f"Couldn't find {e.filename}!")

        input_str = input('Input map ID(s), "-h" for help, or "quit" to quit: ')
        if input_str == "quit":
            stop = True
        else:
            try:
                args, other = parser.parse_known_args(input_str.split())
            except SystemExit:
                args.map_id = ()


if __name__ == '__main__':
    main()
