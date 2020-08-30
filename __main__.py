import click
from GusherMap import GusherMap
from GusherNode import read_tree, write_tree
from getstrats import get_strat


CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument('map_id')
@click.option('--weights', '-W', type=str,
              help="dictionary for specifying custom gusher weights")
@click.option('--tuning', '-t', type=click.FloatRange(0, 1), default=0.5,
              help="set seeking algorithm tuning factor\n"
                   "(between 0-1, 0: take least amount of time, 1: take least amount of risk")
@click.option('--evaluate', '-E', 'strategy_str', type=str,
              help="evaluate a user-specified strategy")
@click.option('--suppress', '-s', is_flag=True,
              help="don't show plot of the map")
@click.option('--debug', '-d', is_flag=True,
              help="print internal process of search algorithm")
def main(map_id, weights, tuning, strategy_str, suppress, debug):
    gusher_map = GusherMap(map_id, weights=weights)
    if strategy_str:
        strat = read_tree(strategy_str, gusher_map)
    else:
        strat = get_strat(gusher_map, tuning=tuning, debug=debug)
    strat.report(gusher_map)
    if not suppress:
        gusher_map.plot()


if __name__ == '__main__':
    main()
