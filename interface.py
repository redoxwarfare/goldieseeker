import matplotlib.pyplot as plt
from numpy import genfromtxt
import networkx as nx

from GusherMap import GusherMap
from GusherNode import read_tree
from getstrats import get_strat

import argparse
import warnings


# parser for input arguments
parser = argparse.ArgumentParser(add_help=False)
parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS,
                    help='Show this help message.')
parser.add_argument('map_id', nargs='*', help="name(s) of folder in 'gusher graphs'")
parser.add_argument('-p', '--plot', help="display gusher graph", action='store_true')
parser.add_argument('-v', '--verbose', help="display strategy as human-readable instructions", action='store_true')
parser.add_argument('-l', '--log', help="print log of search algorithm's internal process", action='store_true')

IMAGE_WIDTH = 640
IMAGE_HEIGHT = 960
basket_width_in_pixels = {'ap': 25, 'lo': 17, 'mb': 22, 'sg': 22, 'ss': 25}


# TODO - move plotting code to GusherMap.py
def plot_graph(gusher_map, map_id=None):
    graph = gusher_map.connections
    background = plt.imread(f'images/{map_id}.png')

    # convert coordinates from basket widths to pixels
    coords = gusher_map.coordinates * basket_width_in_pixels[map_id]
    pos = {sorted(graph)[i]: tuple(coords[i+1, :]) for i in range(len(graph))}

    plt.figure()
    plt.imshow(background, extent=[0, IMAGE_WIDTH, IMAGE_HEIGHT, 0])
    plt.title(gusher_map.name)
    pos_attrs = {node: (coord[0] - 15, coord[1] + 15) for (node, coord) in pos.items()}
    nx.draw_networkx(graph, pos, node_color='#1a611b', edge_color='#35cc37', font_color='#ffffff', arrows=False)
    # nx.draw_networkx_labels(graph, pos_attrs, labels=gusher_map.weights)
    plt.show()


with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    maps = {map_id: GusherMap(map_id) for map_id in ['sg', 'ss', 'mb', 'lo', 'ap']}

# TODO - start compilation of strategy variants for each gushers
rec_strats = {'sg': 'd(g(a(b, c), f(e,)), g*(h, i))',
              'ap': 'f(g(e, c(d,)), g*(a, b))',
              'ss': 'f(d(b, g), e(c, a))',
              'mb': 'b(c(d(a,), e), c*(f, h(g,)))',
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
    simple_strat = get_strat(gusher_map, distances=False, weights=False)
    distance_strat = get_strat(gusher_map, tuning=0)
    weighted_strat = get_strat(gusher_map, tuning=1)
    full_strat = get_strat(gusher_map, debug=log)

    strats = {"simple": simple_strat,
              "shortest time": distance_strat,
              "lowest risk": weighted_strat,
              "balanced time + risk": full_strat,
              "standard": rec_strat}
    for desc in strats:
        strat = strats[desc]
        if strat:
            try:
                strat.validate()
            except AssertionError as e:
                warnings.warn(f'validate() failed for {desc} strategy with error "{e}"')
            print(f"------------\n"
                  f"{desc} strategy:")
            strat.report(gusher_map, verbose)

    if plot:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            print('(if prompt does not reappear, close plot to continue)')
            plot_graph(gusher_map, map_id)


# TODO - Separate functions into their own scripts
# TODO - Add script for inputting strategies, scoring, and saving to file
# TODO - Add tuning factor as argument
def main():
    plt.ion()
    args, other = parser.parse_known_args()
    stop = False
    while not stop:
        try:
            for map_id in args.map_id:
                report(map_id, args.log, args.plot, args.verbose)
        except (FileNotFoundError, IOError) as e:
            print(e)

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
