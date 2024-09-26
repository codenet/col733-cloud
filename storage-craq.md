# Chain Replication with Apportioned Queries

CRAQ's goals are different from GFS. Here, we are interested in building a
key-value store where all the data fits in memory of a single server. But of
course, we will do replication for fault-tolerance. Unlike GFS's large files
with sequential reads/writes, we are interestd in doing small random reads and
writes to keys. Again unlike GFS, we want to provide more "consistent" view of
storage to (possibly) concurrent clients.

CRAQ builds on top of chain replication. Let us first see CR and then
improvements made by CRAQ.

## Linearizability
Let us now formally define what we mean by consistency. When talking about
consistency, we don't want to talk about the internals of a storage system.  We
judge consistency by the behaviors that can be observed by the clients. In
strong consistency, we create an illusion of a single storage server even in the
presence of replication. We want that all execution histories are
*linearizable*, i.e, one can find a *total order* among all read-write
operations such that:
* the total order matches the real time order for non-overlapping histories; and
* reads see last writes.

In particular, we want to find *linearization points* for each request where the
storage must have serviced the operation. Linearization points define the total
order as above. Following shows a linearizable history:

<img width=300 src="assets/figs/craq-linear-1.png">

Following shows a history that is *not* linearizable:

<img width=300 src="assets/figs/craq-linear-2.png">

Note that linearizability does not force an order on concurrent requests. For
example in the following linearizable history, Wx2 started after Wx1 but it was
executed before Wx1.

<img width=250 src="assets/figs/craq-linear-3.png">

The goal of Chain Replication is to only show linearizable histories. 

### Safety and liveness

Note that linearizability is a *safety* property. Safety properties mean "bad
things never happen". We want our storage system to never show non-linearizable
histories.  But safety by itself is trivial to achieve. For example, a useless
storage system that *never* services any reads or writes never shows
non-linearizable histories. 

Therefore, we typically also specify *liveness* properties which means "good
things eventually happen". For our storage system, we want that all read/write
requests are eventually serviced assuming some servers are still alive and
reachable from clients; clients are indefinitely retrying their requests.
Liveness, without safety, is also trivial to achieve. For example, in another
useless storage system, client libraries directly return ok to every write
request and 1 to every read request. The system is live but does not provide
linearizability.

Safety and liveness can be applied to many things. For example, *safety:* do not
fail any course; *liveness:* get the degree. When designing locks, *safety:*
provide mutual exclusion; *liveness:* each lock acquire request (assuming proper
lock releases in the application) is serviced.

## Chain Replication

Under CR, storage servers are organized in a chain. All the write requests go to
the head which forwards it down the chain. Write acknowledgements are sent up
the chain by the tail. All the read requests are serviced directly by the tail.

<img width=300 src="assets/figs/craq-cr.png">

This design clearly provides linearizable histories since the times at which
reads and writes were serviced by the tail directly serve as the linearizable
points.

Fault tolerance is done in a straightforward manner. When a node fails, a system
outside the chain (like an administrator or a more sophisticated heartbeating
system) simply removes the node from the chain. The requests that were in-flight
are retried by the clients.

Why is this correct? Let us say initially x=0 and Wx1 was in-flight. It was seen
by the tail, but head could not acknowledge it to the client since someone in
the chain crashed. Now let us further say tail responded to another client with
Rx1 and crashed. After fault recovery, can the system respond with Rx0 (without
any other Wx in flight).

This is not possible. Since all writes are flowing from head to tail, any write
request that was received by the tail, such as Wx1 above, was seen by *all*
servers in the chain. If there are no other Wx in-flight, new tail is guaranteed
to reply with Rx1.

To tolerate `F` failures, chain replication needs `F+1` systems in the chain.
This is as good as it can get! 

Since tail is solely servicing all the read requests, it is more heavily loaded
than other servers. The overall system's read throughput is equal to that
provided by the tail. To improve system throughput, we can maintain different
chain topologies for different keys as shown below. For example, the follows
shows an example with three servers.

```
A-H: S1 -> S2 -> S3
I-Q: S3 -> S1 -> S2
R-Z: S2 -> S3 -> S1
```

For example, reads to the key `M` will be serviced by S2; reads to the key `R`
will be serviced by S1.

## CRAQ design

The above sharding was possible only because we were providing a get/set
interface for just single keys: each key is being get/set independently.
However, we may be interested in setting multiple keys together in a
"mini-transaction" such as atomically write `M=10, R=20` like in a bank account
transfer. If `M` and `R` flow through two different chains, it makes atomicity
complicated.

The idea of CRAQ is that we can improve read throughput of a single chain by
allowing reads from *non-tail* servers. The difficulty is that we want to
preserve linearizability.

In CRAQ, for each key, each server maintains *multiple versions*. When a write
request flows through a server, it writes the key's value at the next version.
This value is currently *dirty*. We have not seen acknowledgement back from the
tail. When we see a write acknowledgement back from the tail, we can delete all
the older versions of the key and mark the acknowledged version *clean*. Tail
never has dirty version of keys.

To service read request, if a server only has one clean version (that means
there are no in-flight writes downstream), it can directly respond with the
clean version. Otherwise, it asks the tail about its version and responds with
that version. Because of this check with the tail, the system is again
linearizable.