# Zookeeper

## Relaxed consistency
We saw that linearizability can be easily realized via Raft's replicated log by
throwing all reads and writes into the log.

<img width=300 src="assets/figs/raft-linear.png">

To recover from more failures, I am advised to increase servers; `2f+1` servers
are required to handle `f` faults. However, adding servers slows down reads and
writes. More server => More network chit-chat. Each log entry can be applied as
fast as the fastest `f+1` servers.

Can we skip putting reads in the logs as reads do not modify the state machine?
Replicating entries in the log is a *heavy* operation requiring persistence and
consensus. Skipping putting reads into the log will help performance since
typical workloads tend to be read-heavy. 

<img width=200 src="assets/figs/zk-rw.png">

Can we allow reads directly from followers without breaking linearizability?
No. The follower may be in the minority and may not know about the latest write.

Can we allow reads from leader directly? Without replicating read in the log and
without breaking linearizability? No! What if the new leader accepted a write
and the old leader serviced the read.

<img width=250 src="assets/figs/zk-stale-read.png">

One way to fix the above situation is by using *leases*. Old leader keeps
renewing its lease via building majority quorum in every heartbeat. New leader
cannot be elected until the lease expires: server does not vote until the lease
extension it allowed to the old leader has expired. Therefore, the above
situation cannot happen. Old leader safely services local reads until lease
timeout. New leader cannot apply the problematic Wx1 within the lease timeout.
Therefore, we *can* service reads without replicating reads in the log!

Can we further improve read throughput by sending reads to followers? Ideally,
Nx servers should give Nx throughput. Zookeeper does this by relaxing
consistency. Stale reads shown above are allowed! A useless storage system shows
all reads as initial values (say 0). Zookeeper places some restrictions on what
kind of stale reads are allowed:

1. Writes are linearizable, i.e, they follow a total order. If a client has read
   `y=4`, then it must read `x=2`. If another client has only read `y=3`, then it
   is ok for it to read `x=1`. In other words, stale reads are allowed but by
   reading a write, all previous writes become *visible*.
   
   <img width=250 src="assets/figs/zk-linear-writes.png">

2. Clients always see their own writes. When reading after a write, all previous
   writes become visible.

   <img width=250 src="assets/figs/zk-fifo.png">

## Implementation in terms of Raft

Now, clients are talking to the closest server. Writes have to go through the log
for replicated state machine; reads are served locally by the server.

How to implement GFS master in zookeeper?
How to implement leader election in zookeeper?
How to implement CRAQ's chain configuration in zookeeper?