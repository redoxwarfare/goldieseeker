from numpy import genfromtxt, around, savetxt
from scipy.spatial import distance_matrix
from GusherMap import COMMENT_CHAR, BASKET_LABEL

maps = {'ap': "Ruins of Ark Polaris",
        'lo': "Lost Outpost",
        'mb': "Marooner's Bay",
        'sg': "Spawning Grounds",
        'ss': "Salmonid Smokeyard"}
labels = BASKET_LABEL + 'abcdefghijklmnopqrstuvwxyz'

for map_id in maps:
    coords = genfromtxt(f"gusher graphs/{map_id}/gushers.csv", delimiter=', ')
    adjacency_matrix = around(distance_matrix(coords, coords), decimals=2)
    header_str = maps[map_id] + '\n    ' + ',      '.join(labels[:len(adjacency_matrix)])
    savetxt(f"gusher graphs/{map_id}/distances.txt", adjacency_matrix,
            fmt='% 7.2f', delimiter=',', header=header_str, comments=COMMENT_CHAR+' ')
