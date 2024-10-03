# Lecture notes 
For COL733: cloud computing technology fundamentals, taught at IIT Delhi.

1. [Introduction](./why-cloud.md): resource management overheads, SLAs,
elasticity, proximity; distributed computations: stragglers, resource
utilization, fault tolerance; virtualization: overprovisioning, snapshot,
migration, isolation; distributed storage: replication and consistency.

### Distributed compute
1. [Scalability](./compute-scalability.md): speedup, efficiency, iso-efficiency,
scalability, task DAGs.
2. [Distributed shared memory](./compute-dsm.md): memory coherence, false
sharing, faults and stragglers, replication in paging-based DSM.
3. [MapReduce](./compute-mr.md): give up on general purpose programs, restricted
but useful programming model, locality, scalability, idempotent and
deterministic tasks are rerun for FT/stragglers.
4. [Spark](./compute-rdd.md): lineage-based reexecution for FT and stragglers,
coarse-grained transformations for small lineage graphs, immutable distributed
data for consistent replication, wide and narrow dependencies.
5. [Spark streaming](./compute-dstreams.md): Freshness objective, continuous
operator model, FT challenges due to state, micro-batching to make computations
stateless.
6. [Asynchronous checkpointing using vector clocks](./compute-vc.md): consistent
checkpointing algorithm, inconsistent checkpoints due to clock drifts, vector
clocks.
7. [Flink](./compute-flink.md)
8. [TensorFlow Part I](./compute-tf-graph.md)
9. [TensorFlow Part II](./compute-tf)
10. [Ray](./compute-ray)

### Distributed storage
1. [Google File System](./storage-gfs.md)
2. [Chain Replication with Apportioned Queries](./storage-craq.md)
3. [Dynamo](./storage-dynamo.md)