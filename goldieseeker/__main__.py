import click
from .GusherMap import GusherMap
from .GusherNode import read_tree
from .getstrats import get_strat


# TODO - start compilation of strategy variants for each gushers

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument('map_id')
@click.option('--tuning', '-t', type=click.FloatRange(0, 1), default=0.5,
              help="""\b
              Set the seeking algorithm's tuning factor (range between 0-1).
              0: fastest time, 1: lowest risk""")
@click.option('--eval', '-E', 'strategy_str', type=str,
              help="""\b
              Evaluate a user-specified strategy.
              example: -E "f(d(b, g), e(c, a))"
              "a(b, c)" means "if a is high, open b, and if a is low, open c\"""")
@click.option('--weights', '-W', type=str,
              help="""\b
              Specify custom gusher weights in dictionary format.
              example: -W "{'d': 4, 'bef': 2, '.': 1}"
              This gives a weight of 4 to gusher D, a weight of 2 to gushers B, E, and F, """
              "and a weight of 1 to the rest.")
@click.option('--suppress', '-s', is_flag=True,
              help="Don't show the plot of the map.")
@click.option('--debug', '-d', is_flag=True,
              help="Print internal process of search algorithm.")
def main(map_id, weights, tuning, strategy_str, suppress, debug):
    """For a given map, generate a Goldie Seeking strategy or evaluate a user-specified strategy."""
    gusher_map = GusherMap(map_id, weights=weights)
    if strategy_str:
        strat = read_tree(strategy_str, gusher_map)
    else:
        strat = get_strat(gusher_map, tuning=tuning, debug=debug)
    click.echo(strat.report(gusher_map))
    if not suppress:
        gusher_map.plot()


if __name__ == '__main__':
    main()
