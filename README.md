# goldieseeker
A command-line tool for generating and analyzing strategies for Goldie Seeking in Salmon Run.

Map IDs:
* ap - Ark Polaris
* lo - Lost Outpost
* mb - Marooner's Bay
* sg - Spawning Grounds
* ss - Salmonid Smokeyard

### How to Use
You can install goldieseeker with pip using the command `pip install goldieseeker`, then run `gseek -m [map_id]` using one of the above map IDs. Run `gseek --help` to see all the other options and features. For more customization, you can edit the files in the `goldieseeker/maps` folder. (This should be located wherever you installed the package.)

Requires Python 3.6 or higher.

More extensive documentation coming soon... hopefully?

### Formatting
* Strategies are notated in the form "a(b, c)": open A, go to B if A is high, go to C if A is low
* If a gusher is starred (e.g. a*), the Goldie will never be found in that gusher

### Acknowledgements
* Thanks to Deelatch and RR for help with search algorithm
* Thanks to the Salmon Run server for feedback on features and UI
* Map images from [Salmon Learn](https://github.com/GungeeSpla/salmon_learn)
