# Lecture notes 
For COL733: cloud computing technology fundamentals, taught at IIT Delhi.

1. [Introduction](./why-cloud.md): resource management overheads, SLAs,
elasticity, proximity; distributed computations: stragglers, resource
utilization, fault tolerance; virtualization: overprovisioning, snapshot,
migration, isolation; distributed storage: replication for FT, consistency.

### Distributed compute
1. [Scalability](./compute-scalability.md): speedup, efficiency, iso-efficiency,
scalability, task DAGs.
2. [Distributed shared memory](./compute-dsm.md): design of paging-based DSM,
difficulties due to memory coherence, false sharing, replication in DSM for
faults, stragglers.
3. [MapReduce](./compute-mr.md): give up on general purpose programs, restricted
but useful programming model, locality, scalability, rerunning idempotent
deterministic tasks for FT/stragglers.
4. [Spark](./compute-rdd.md): lineage-based reexecution for FT/stragglers,
coarse-grained transformations for small lineage graphs, immutable distributed
data for consistent replication, wide/narrow dependencies.
5. [Spark streaming](./compute-dstreams.md): Freshness objective, continuous
operator model, FT challenges due to stateful operators, micro-batching to make
computations stateless.
6. [Vector clocks](./compute-vc.md): consistent asynchronous checkpointing
algorithm, inconsistent checkpoints due to clock drifts, vector clocks,
isomorphism with causality.
7. [Flink](./compute-flink.md): Flink's asynchronous consistent checkpointing
algorithm enabling real-time stateful streaming.
8. [TensorFlow Part I](./compute-tf-graph.md): Requirements from ML training
workloads, parameter servers, unified dataflow graph.
9. [TensorFlow Part II](./compute-tf): heterogenous execution, leveraging weak
consistency: async parameter updates, inconsistent checkpoints for FT, M/N
updates for stragglers.
10. [Ray](./compute-ray): Dynamic task DAGs using tasks/futures, stateful actor
methods in lineage, distributed scheduler. 

### Distributed storage
1. [Google File System](./storage-gfs.md): Distributed storage challenges, file
system interface for large files, GFS design, weak consistency guarantees, FT of
chunkservers/master.
2. [Chain Replication with Apportioned Queries](./storage-craq.md): safety/liveness,
linearizability, CRAQ read throughput improvements over chain replication, chain
replication can replicate state machines.
3. [Dynamo](./storage-dynamo.md): CAP theorem, decentralized storage design,
consistent hashing, gossip protocol using vector clocks, sloppy quorums with
hinted replicas, version reconciliations.
4. [Bayou/CRDT](./storage-ec.md): State-based CRDTs: monotonic operations on a 
semilattice; Operations-based CRDTs: commutative operations; Bayou for handling
conflicting writes by putting them in a replicated log; anti-entropy; eventual
consistency.
5. [Raft](./storage-raft.md): Raft's safety properties: state-machine safety,
election safety, leader completeness property; liveness properties: majority
within bounded delay implies progress; automated failover via leader election:
idea of majority, consensus, FLP impossibility. 
6. [Zookeeper](./storage-zookeeper.md): Improving read throughput of Raft-like
consensus system by allowing stale reads, Zookeeper API: znodes, ephemeral and 
sequential znodes, watches; usecases: configuration management, rendezvous,
group membership, distributed locking; distributed locks: herd effect, using
fencing tokens.
7. [Spanner](./storage-spanner.md): Serializability, strict serializability,
optimistic, pessimistic, multi-version concurrency control, two phase commits,
snapshot isolation, commit/start timestamps.
