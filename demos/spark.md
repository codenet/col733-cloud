# Running page rank on Spark

#### Starting Spark container

`docker run -p 8888:8888 jupyter/pyspark-notebook`

```sh
$ docker ps
CONTAINER ID   IMAGE                      COMMAND                  CREATED          STATUS                    PORTS                              NAMES
2a191ba288e7   jupyter/pyspark-notebook   "tini -g -- start-no…"   11 minutes ago   Up 11 minutes (healthy)   4040/tcp, 0.0.0.0:8888->8888/tcp   keen_thompson
```


This starts notebook with some logs as follows.  Open the URL in chrome.

```[I 2023-08-07 05:51:45.439 ServerApp]     http://127.0.0.1:8888/lab?token=ece4bbb30e4f6d13207b9ab52b154b34cb671b8c6fbcad75```

#### Setting up input and running Spark code
Create a dummy graph in an input file `in`:

```sh
$ cat in
u1 u2
u3 u2
u2 u4
u1 u1
u3 u3
u4 u4
u2 u2
u2 u4
``` 

> Self-loops are important otherwise page rank code doesn't work properly (each
node should have atleast one incoming edge and at least one outgoing edge)

Download [pagerank.py](https://github.com/apache/spark/blob/master/examples/src/main/python/pagerank.py) into the container. You can run the page rank code as follows.

```sh
$ spark-submit pagerank.py in 10
```

#### Walkthrough
We can also run the same code line-by-line to see what is going on.

```py
lines = spark.read.text("in").rdd.map(lambda r: r[0])
## what is lines? does it contain the content of file "in"?

lines.collect()
# ['u1 u2', 'u3 u2', 'u2 u4', 'u1 u1', 'u3 u3', 'u4 u4', 'u2 u2', 'u2 u4']
# lines yields a list of strings, one per line of input
# if we run lines.collect() again, it re-reads file "in"

import re
def parseNeighbors(urls):
    """Parses a urls pair string into urls pair."""
    parts = re.split(r'\s+', urls)
    return parts[0], parts[1]

# Loads all URLs from input file and initialize their neighbors.
neigh = lines.map(lambda urls: parseNeighbors(urls))
neigh.collect()
# [('u1', 'u2'), ('u3', 'u2'), ('u2', 'u4'), ('u1', 'u1'), ('u3', 'u3'), ('u4', 'u4'), ('u2', 'u2'), ('u2', 'u4')]
# map, split, tuple -- acts on each line in turn
# parses each string "x y" into tuple ( "x", "y" )

dlinks = neigh.distinct()
dlinks.collect()
# [('u1', 'u2'), ('u3', 'u2'), ('u2', 'u4'), ('u1', 'u1'), ('u3', 'u3'), ('u4', 'u4'), ('u2', 'u2')]
# wide dependency
# distinct() sorts or hashes to bring duplicates together and eliminates them

links = dlinks.groupByKey()
links.collect()
# [('u1', <pyspark.resultiterable.ResultIterable object at 0x7f81d4e9ad00>), ('u3', <pyspark.resultiterable.ResultIterable object at 0x7f81d4e9af10>), ('u2', <pyspark.resultiterable.ResultIterable object at 0x7f81d4e74730>), ('u4', <pyspark.resultiterable.ResultIterable object at 0x7f81d4e746d0>)]
# narrow dependency since it's already partitioned by key after distinct
# groupByKey() sorts or hashes to bring instances of each key together

# Let us see what is inside each link
for i in links.collect():
  print(f'\n{i[0]} --', end=" ")
  for j in i[1]:
     print(j, end=" ")
# u1 --u2 u1
# u3 --u2 u3
# u2 --u4 u2
# u4 --u4
# For each source URL, we now have their destination URLs

links = links.cache()
# cache() == persist in memory
links.__dict__
# shows is_cached: True
# {'func': <function PipelinedRDD.__init__.<locals>.pipeline_func at 0x7f81d4e67700>, 'preservesPartitioning': True, '_prev_jrdd': JavaObject id=o74, '_prev_jrdd_deserializer': BatchedSerializer(PickleSerializer(), -1), 'is_cached': True, 'has_resource_profile': False, 'is_checkpointed': False, 'ctx': <SparkContext master=local[*] appName=PySparkShell>, 'prev': PythonRDD[15] at RDD at PythonRDD.scala:53, '_jrdd_val': JavaObject id=o83, '_id': None, '_jrdd_deserializer': AutoBatchedSerializer(PickleSerializer()), '_bypass_serializer': False, 'partitioner': <pyspark.rdd.Partitioner object at 0x7f81d4e9adf0>, 'is_barrier': False}

ranks = links.map(lambda url_neighbors: (url_neighbors[0], 1.0))
# Another map function. Iterate over all links and give each url a score of 1.0

# now for first loop iteration
# Calculates URL contributions to the rank of other URLs.
jj = links.join(ranks)
# the join brings each page's link list and current rank together

def computeContribs(urls, rank):
    """Calculates URL contributions to the rank of other URLs."""
    num_urls = len(urls)
    for url in urls:
        yield (url, rank / num_urls)

contribs = jj.flatMap(lambda url_urls_rank: computeContribs(url_urls_rank[1][0], url_urls_rank[1][1]))
contribs.collect()
# This splits the current rank of a URL equally into the URL's destination URLs.
# [('u2', 0.5), ('u1', 0.5), ('u2', 0.5), ('u3', 0.5), ('u4', 0.5), ('u2', 0.5), ('u4', 1.0)]

from operator import add
r = contribs.reduceByKey(add)
r.collect()
# [('u2', 1.5), ('u1', 0.5), ('u3', 0.5), ('u4', 1.5)]
# reduceByKey() brings together equal keys; add sums them up.

# Finally re-calculate URL ranks based on neighbor contributions.
ranks = r.mapValues(lambda rank: rank * 0.85 + 0.15)
ranks.collect()
# [('u2', 1.4249999999999998), ('u1', 0.575), ('u3', 0.575), ('u4', 1.4249999999999998)]
```

We saw the demo by calling many collect() calls. collect() is an "action". In
general, the code does not execute line-by-line. The code including the loop in
page rank just creates a lineage graph. It does not do any real work.  When an
action like collect() is executed, only then it causes the prepared graph to
execute.