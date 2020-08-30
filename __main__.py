import click
from GusherMap import GusherMap
from GusherNode import read_tree, write_tree, write_instructions
from getstrats import get_strat


@click.command()
@click.argument('map_id')
def main(map_id):
    gusher_map = GusherMap(map_id)
    strat = get_strat(gusher_map)
    strat.report(gusher_map)
    gusher_map.plot()


if __name__ == '__main__':
    main()