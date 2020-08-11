# Optimizing Goldie Seeking for Fun and Profit(?)
In which we attempt to dissect a children's video game using discrete math.

## The Problem
There are several gushers on the map, one of which is hiding a Goldie. You can open gushers to check if the Goldie is inside, but each wrong gusher spawns hordes of fish. If an opened gusher is adjacent to the Goldie, it will be high; otherwise, it will be low. How can you find the Goldie as quickly as possible without spawning too many fish in the wrong places?

## Diving a Little Deeper
(WIP)
### What Are Graphs?
### What Are Decision Trees?
#### Some Notation
To make it easier to describe Goldie Seeking strategies (and because I'm too lazy to make nice diagrams), we'll use a standard notation to write a decision tree as a string of characters. The string G(H, L) represents a decision tree where G is the name of the gusher opened first, and H and L are the subtrees to follow depending on whether gusher G is high or low.

Here's what the recommended Salmonid Smokeyard strategy looks like: ```f(d(b, g), e(c, a))```

The advantage of this notation is that groups of adjacent gushers that all appear high when the Goldie hides in one of them will appear consecutively from left to right in the order that they should be opened. If a gusher is low, you skip to the next group in the string, just as you "skip" across the map to open a remote gusher.

## The Problem, but With More Math
Now that we understand the math behind Goldie Seeking a little better, we can restate our initial question in a more mathematically exact form.

Let G be a graph whose vertices represent the gushers on a map and whose edges represent connections between gushers. To each vertex V, we assign a penalty value p(V) that describes how risky we think opening that gusher is. Our problem is to construct a valid decision tree T that minimizes the total cost of all gushers and therefore minimizes the expected cost in an average seeking round.

## The Algorithm's Strategy
(WIP)

## Run, Squiddo, Run
(WIP)
