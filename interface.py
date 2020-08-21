import matplotlib.pyplot as plt
import networkx as nx

from GusherMap import GusherMap
from GusherNode import read_tree
from getstrats import get_strat, get_strat_greedy

import argparse
import warnings


# parser for input arguments
parser = argparse.ArgumentParser(add_help=False)
parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS,
                    help='Show this help message.')
parser.add_argument("map_id", nargs='*', help="name(s) of folder in 'gusher graphs'")
parser.add_argument("--log", help="print log of search algorithm's internal process", action='store_true')
parser.add_argument("--plot", help="display gusher graph", action='store_true')
parser.add_argument("--verbose", "-V", help="display strategy as human-readable instructions", action="store_true")


def plot_graph(gusher_map):
    graph = gusher_map.connections
    plt.figure()
    plt.title(gusher_map.name)
    pos = nx.kamada_kawai_layout(graph)
    pos_attrs = {node: (coord[0] - 0.08, coord[1] + 0.1) for (node, coord) in pos.items()}
    nx.draw_networkx(graph, pos, edge_color='#888888', font_color='#ffffff')
    nx.draw_networkx_labels(graph, pos_attrs, labels=nx.get_node_attributes(graph, 'penalty'))
    plt.show()


with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    maps = {map_id: GusherMap(map_id) for map_id in ['sg', 'ss', 'mb', 'lo', 'ap']}

# TODO - start compilation of strategy variants for each gushers
rec_strats = {'sg': 'd(g(a(b, c), f(e,)), g*(h, i))',
              'ap': 'f(g(e, c(d,)), g*(a, b))',
              'ss': 'f(d(b, g), e(c, a))',
              'mb': 'c(b(d(a,), f), b*(e, h(g,)))',
              'lo': 'h(f(e, g(i,)), f*(d, a(c(b,),)))'}


def report(map_id, log=False, plot=False, verbose=False):
    if map_id in maps:
        gusher_map = maps[map_id]
    else:
        gusher_map = GusherMap(map_id)
    print(f'\nMap: {gusher_map.name}')

    if map_id in rec_strats:
        rec_strat = read_tree(rec_strats[map_id], gusher_map)
    else:
        rec_strat = None
    greedy_strat = get_strat_greedy(gusher_map)
    simple_strat = get_strat(gusher_map, distances=False, weights=False)
    distance_strat = get_strat(gusher_map, weights=False)
    weighted_strat = get_strat(gusher_map, distances=False)
    full_strat = get_strat(gusher_map, debug=log)

    strats = {"greedy": greedy_strat,
              "equal distance, equal weights": simple_strat,
              "distance only": distance_strat,
              "weights only": weighted_strat,
              "distance + weights": full_strat,
              "recommended": rec_strat}
    for desc in strats:
        strat = strats[desc]
        if strat:
            try:
                strat.validate()
            except AssertionError as e:
                warnings.warn(f'validate() failed for {desc} strat with error "{e}"')
            print(f"------------\n"
                  f"{desc} strat:")
            strat.report(gusher_map, verbose)

    if plot:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            print('(may need to close graph plot to continue)')
            plot_graph(gusher_map)


def main():
    args, other = parser.parse_known_args()
    stop = False
    while not stop:
        try:
            for map_id in args.map_id:
                report(map_id, args.log, args.plot, args.verbose)
        except FileNotFoundError as e:
            print(f"Couldn't find {e.filename}!")

        input_str = input('Input gushers ID(s), "-h" for help, or "quit" to quit: ')
        if input_str == "quit":
            stop = True
        else:
            try:
                args, other = parser.parse_known_args(input_str.split())
            except SystemExit:
                args.map_id = ()


if __name__ == '__main__':
    main()
