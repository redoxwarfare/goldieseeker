import timeit
from getstrats import getstrat
from getstrats import load_graph
from statistics import mean, stdev

s = 'from __main__ import getstrat, G'
maps = ('sg', 'ss', 'mb', 'lo', 'ap')

for m in maps:
    G = load_graph(m)
    times = [timeit.timeit('getstrat(G)', setup=s, number=1) for i in range(100)]
    print(f'{m}: {mean(times):0.3f} s, {stdev(times):0.3f} s')
