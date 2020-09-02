import click
import pathlib
from os import scandir
from . import __version__
from .GusherMap import GusherMap
from .GusherNode import read_tree
from .strats import get_strat


# TODO - start compilation of strategy variants for each gushers

# Settings for Click
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

# Get list of available map IDs
HERE = pathlib.Path(__file__).parent.resolve()
maps = [f.name for f in scandir(HERE/'maps/') if f.is_dir()]


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option('--map', '-m', 'map_id', required=True,
              type=click.Choice(maps, case_sensitive=False),
              help="""Map ID. Must be the name of a folder in 'goldieseeker/maps'.""")
@click.option('--tuning', '-t', type=click.FloatRange(0, 1), default=0.5,
              help="""\b
              Set the seeking algorithm's tuning factor (range between 0-1).
              0: fastest time, 1: lowest risk""")
@click.option('--squad', '-s', is_flag=True,
              help="""\b
              Turn on "squad" mode (experimental).
              This tells the seeking algorithm to assume that traveling to a gusher never takes longer than it would 
              take when coming from spawn (i.e. the basket).""")
@click.option('--eval', '-E', 'strategy_str', type=str,
              help="""\b
              Evaluate a user-specified strategy.
              example: -E "f(d(b, g), e(c, a))"
              "a(b, c)" means "if A is high, open B, and if A is low, open C\"""")
@click.option('--weights', '-W', type=str,
              help="""\b
              Specify custom gusher weights in dictionary format.
              example: -W "{'d': 4, 'bef': 2, '.': 1}"
              This gives a weight of 4 to gusher D, a weight of 2 to gushers B, E, and F, """
              "and a weight of 1 to the rest.")
@click.option('--quiet', '-q', count=True,
              help="""\b
              Don't show the map plot.
              Use '-qq' to also suppress reporting strategy details.
              Use '-qqq' to only output the string representation of the strategy tree.""")
@click.option('--debug', '-d', is_flag=True,
              help="Print internal process of search algorithm.")
@click.version_option(__version__, '--version', '-v', prog_name="goldieseeker")
def main(map_id, tuning, squad, strategy_str, weights, quiet, debug):
    """\b
    For a given map, generate a Goldie Seeking strategy or evaluate a user-specified strategy.
    To customize default distances and weights, edit the corresponding files in goldieseeker/maps/[MAP_ID]."""
    try:
        gusher_map = GusherMap(map_id, weights=weights, squad=squad)
    except IOError as err:
        click.echo(f"Couldn't load map '{map_id}'!", err=True)
        click.echo(str(err), err=True)
    else:
        if strategy_str:
            strat = read_tree(strategy_str, gusher_map)
            strat.validate(gusher_map)  # TODO -- catch ValidationErrors and suggest corrections
        else:
            strat = get_strat(gusher_map, tuning=tuning, debug=debug)
            # strat.validate(gusher_map)
        click.echo(strat.report(gusher_map, quiet=quiet))
        if quiet < 1:
            gusher_map.plot()


if __name__ == '__main__':
    main()
