from numpy import genfromtxt, around, savetxt
from scipy.spatial import distance_matrix
from GusherMap import COMMENT_CHAR, GUSHER_LABELS

# TODO - for AP and MB, try calculating climb-up distances using 1-norm and drop-down distances using 2-norm
maps = {'ap': "Ruins of Ark Polaris",
        'lo': "Lost Outpost",
        'mb': "Marooner's Bay",
        'sg': "Spawning Grounds",
        'ss': "Salmonid Smokeyard"}
norms = {'ap': 1.5, 'lo': 1.25, 'mb': 1.5, 'sg': 2, 'ss': 1.5}

for map_id in maps:
    coords = genfromtxt(f"gusher graphs/{map_id}/gushers.csv", delimiter=', ')
    adjacency_matrix = around(0.25*distance_matrix(coords[:, 1:], coords[:, 1:], p=norms[map_id]), decimals=3)
    header_str = maps[map_id] + '\n' + \
                 'row: gusher you are coming from\n' + \
                 'column: gusher you are going to\n' + \
                 '    ' + ',      '.join(GUSHER_LABELS[:len(adjacency_matrix)])
    # noinspection PyTypeChecker
    savetxt(f"gusher graphs/{map_id}/distances.txt", adjacency_matrix,
            fmt='% 7.3f', delimiter=',', header=header_str, comments=COMMENT_CHAR+' ')
