# Spanner

- [Spanner](#spanner)
	- [Strict serializability / external consistency](#strict-serializability--external-consistency)
		- [Optimistic concurrency control](#optimistic-concurrency-control)
		- [Pessimistic concurrency control](#pessimistic-concurrency-control)
			- [Two-phase commit](#two-phase-commit)
	- [Snapshot reads](#snapshot-reads)
		- [Multi-version concurrency control](#multi-version-concurrency-control)
	- [Troubles due to clock skew](#troubles-due-to-clock-skew)
- [Summary](#summary)

## Strict serializability / external consistency
In Zookeeper, Raft, CR/CRAQ, we have been assuming that the entire-key value
store fits within the memory/storage of a single machine. In Dynamo, we sharded
the objects, but there we assumed that all keys are being read/written
independently.

These storage systems cannot service applications such as banking.  Here, all
bank account information cannot fit into a single machine, therefore requiring
sharding of accounts. We might want to modify multiple bank account balances
together in *transactions*.

We focus on two ACID properties: 
* Atomicity: Either all writes happen or none of them happen
* Isolation: Execute like no other transactions were running

Assume x=y=$100 and we are doing the following two transactions:

| T1: transfer | T2: audit   |
| ------------ | ----------- |
| x = get_x()  | x = get_x() |
| y = get_y()  | y = get_y() |
| put_x(x+10)  | print(x+y)  |
| put_y(y-10)  |

Atomicity is broken if T1 crashes after put_x(x+10). We magically created $10 in
our bank. Isolation is broken if T2 executes between T1's `put_x(x+10)` and
`put_y(y-10)`. T2 will then print 210. If T1 executes between T2's `get_x()` and
`get_y()`, T2 will print 190.

To get isolation, what we want is *serializabilty*. Observed effect of
transaction executions can be rearranged in a serial order: T1 before T2 or T2
before T1.  For the example above, in both rearrangements, x=110, y=90, and 200
is printed.

Note that serializability is different from linearizability. Linearizability
only talks about operations on a *single* object whereas serializability is about
transactions: multiple operations on multiple objects.

<img width=300 src="assets/figs/spanner-linear-serial.png">

Serializability does not say anything about real-time order. For example, no
matter when T2 is run, let us say if it just reads initial values of `x` and
`y`, we can still arrange transactions into a serial order. *Strict
serializability* additionally enforces *real-time order*: if T2 *started* after
T1 *committed*, only T1 before T2 is strictly serializable.

If a system can realize strict serializability, it can easily realize
linearizability: make all transactions do just one operation (read or write) on
just one object. Strict serializability is easy to realize in Raft/chain
replication by throwing entire transactions into the replicated log. Systems
ensure that they will run one transaction at a time; the log forces the
real-time order.

However, this may not perform very well. Non-conflicting transactions, such as a
bank transfer from x to y, is unnecessarily serialized with another bank
transfer from p to q. Moreover, all bank accounts do not fit in a single
machine; e.g. x and y bank accounts can be sharded on two different machines.

### Optimistic concurrency control

OCC assumes most transactions do not conflict with each other. Transactions
setup watch for different variables. If any variable changes before transaction
could commit, the transaction is aborted. For example in the following, if T1
gets to exec first, T2 is aborted and retried. If T2 gets to exec first, T1 is
*not* aborted since T2 did not change x, y.

| T1: transfer | T2: audit   |
| ------------ | ----------- |
| watch x      | watch x     |
| watch y      | watch y     |
| multi        | multi       |
| x = get_x()  | x = get_x() |
| y = get_y()  | y = get_y() |
| put_x(x+10)  | exec        |
| put_y(y-10)  | print(x+y)  |
| exec         |

### Pessimistic concurrency control

PCC assumes most transactions conflict with each other, so they upfront lock
variables. If transactions were not conflicting, we unnecessarily pay the
locking overhead.

| T1: transfer | T2: audit   |
| ------------ | ----------- |
| rlock(x)     | rlock(x)    |
| rlock(y)     | rlock(y)    |
| x = get_x()  | x = get_x() |
| y = get_y()  | y = get_y() |
| wlock(x)     | release(x)  |
| wlock(y)     | release(y)  |
| put_x(x+10)  | print(x+y)  |
| put_y(y-10)  |
| release(x)   |
| release(y)   |

We can easily get into deadlocks with multiple ongoing transactions. For
example, if one transaction is transfering from x to y and another is
transfering from y to x then both of them may have taken read locks and no-one
is able to take the write locks.

PCC typically have some mechanisms for breaking deadlocks. For example, in
wound-wait deadlock avoidance scheme, the transaction that reaches wlock first
aborts the other transaction that is deadlocking with it.

Now let us see how to do PCC when x and y are distributed on multiple machines.

#### Two-phase commit

In two-phase commits, RW transactions are executed in two phases. Transaction
coordinator (TC) asks all shards to return all relevant values and *prepare* to write
by taking the write locks. The values are sent back to the client.  The client
sends back the new values to write. TC asks all shards to commit the values and
release all locks.

<img width=300 src="assets/figs/spanner-2pc-phases.png">

How does it give atomicity? TC says prepare is complete iff *all* shards said
YES to prepare phase. If shard B couldn't get the lock, for example, it replies
NO. TC will abort the transaction.

What if B crashes *before* it could send YES? TC will timeout the prepare and
abort the transaction. It will send abort to A, A will release the locks without
writing anything.

What if B crashes *after* it already sent YES? TC may have sent commit to A!
TC will keep retrying commit(T1) forever with B.  When B reboots, it must
*remember* that it was in the middle of transaction T1, and must re-acquire
wlock(y). It must not say YES to another conflicting transaction! Therefore,
shards must do write-ahead-logging of prepare(T1, YES) before replying to TC. 

What if TC crashes? If participants replied YES, they are blocked. They must
keep waiting for commit/abort! After restart, TC must commit/abort all pending
transactions. Therefore, TC does write-ahead logging of 
* transaction details,
* sent prepare message for transaction T to shard X, 
* sent commit/abort message for transaction T to shard X, 
* received second phase ACK for transaction T from shard X.

Why is it ok to not log prepare responses from shards? TC can unilaterally abort
if it has not committed/aborted a transaction. 

Spanner does two-phase commits of RW transactions. However, each shard and TC is
a Paxos group (like a Raft group). Instead of doing write-ahead logging to disk,
to handle restarts, the write-ahead logging is done in the replicated log (and
the disk) so that majority within a given shard knows which transactions have we
prepared for.

## Snapshot reads

Pessimistic concurrency control is not great for large read-only transactions.
For example, if we are auditting all bank accounts, we will have to
simultaneously acquire read locks on all bank accounts! It may take a long time
to take these locks and further, it prevents all writes while the locks are
held! We would like to execute such read-only transactions without taking any
locks.

| T0: transfer | T1: transfer | T2: audit   |
| ------------ | ------------ | ----------- |
| rlock(x)     | rlock(x)     | x = get_x() |
| rlock(y)     | rlock(y)     | y = get_y() |
| x = get_x()  | x = get_x()  | print(x+y)  |
| y = get_y()  | y = get_y()  |
| wlock(x)     | wlock(x)     |
| wlock(y)     | wlock(y)     |
| put_x(x-3)   | put_x(x+10)  |
| put_y(y+3)   | put_y(y-10)  |
| release(x)   | release(x)   |
| release(y)   | release(y)   |

Even though, read-only transactions are executed without locks, we still want to
uphold strict serializability! It is unacceptable to run T2 in between `put_x`
and `put_y` of T1 thereby getting wrong total account balance!

### Multi-version concurrency control

The idea to support snapshot reads is to keep multiple *timestamped versions* of
each value. Each RW transaction is given a *commit timestamp* and all the values
written by it are written at this timestamp version. Each RO transaction is
given a *start timestamp*, it reads latest values at this timestamp. 

Even though there may be other ongoing RW transactions, their writes do not
interfere with what an earlier RO transaction is reading! This allows lock-free
reads in RO transactions without giving up strict serializability: timestamps
create the serial order among transactions.

For example in the following, T1 is committed at time 2, T2 starts at time 5 and
reads the values written by T1. If T0 was ongoing, it does not affect the reads
of T2.

<img width=350 src="assets/figs/spanner-mvcc.png">

However, there is a problem. Commit timestamp is decided by TC. What if the
shard has not yet written the value at committed timestamp. In the following
example, `y@2=120` is written *after* `Ry@5` request came to the shard Y.  If
shard Y responds with the latest value of y (y@0 = 100), we broke strict
serializability!

<img width=350 src="assets/figs/spanner-late-commit.png">

Y must not serve y@0 at Ry@5. Once a shard has taken a wlock, it may be
committed with a future timestamp at any time in the future. Shards must not
service reads at a future time until they release the wlock via commit/abort.
Notice that this is a problem only because we are doing *lock-free* reads. This
is managed by *safe time*: only reads *before* safe time can be serviced, reads
*after* safe time are *blocked*.

In the following example, shards X and Y pause their safe time to time 1 when
they take the wlock. When shard X sees the commit and unlocks, it can advance
its safe time to the clock time and service Rx@5. When shard Y gets Ry@5, its
safe time is still stuck at 1. Therefore, this request is blocked! Finally, when
shard Y commits, it advances its safe time and services Ry@5 with y@2=120.

<img width=350 src="assets/figs/spanner-safe-time.png">

## Troubles due to clock skew

However, servers' local clocks may not reflect "true" real-time with each other.

Let us say, an RO transaction T3, reading x and y, starts at true real-time 2.
Further, say two RW transactions, T1 writing x, and T2 writing y, commit at true
real-time 1. Since T3 starts *after* RW transactions T1 and T2, it must read
both the writes: from T1 and T2. However, let us say T1's TC clock was running
*ahead* and it sets the commit timestamp as 3 (the true real-time is only 1).
Therefore, T3 will read the new value from T2 but *not* from T1, thereby
breaking strict serializability!

<img width=250 src="assets/figs/spanner-skew-prob.png">

The *big idea* in spanner is to *expose* the clock uncertainty interval to
servers. Spanner guarantees that the true real-time falls within this
uncertainty interval.

<img width=200 src="assets/figs/spanner-uncertainty.png">

Google servers have access to a `TrueTime` API:
* TrueTime.earliest: earliest in the uncertainty interval (0 in above example)
* TrueTime.latest: latest in the uncertainty interval (4 in above example)

Google measured worst-case clock drifts in their servers as 200us per second.
They put *time masters* in each data center equipped with atomic clocks/GPS
receivers which do not have such clock drifts. Each server in the data center
gets the time from time servers every 30 seconds. After every 30 seconds, the
uncertainty interval shrinks to RTT (~1ms), and then it again grows at the rate
of 200us per second to ~7ms until the next sync with time master.

<img width=250 src="assets/figs/spanner-sawtooth.png">

Equipped with TrueTime API, the commit timestamps of RW transactions and the
start timestamps of RO transactions can be set to TrueTime.latest. This
guarantees that by the time commit is applied/read happens the true real time is
indeed that much (since true real time is guaranteed to be *before*
TrueTime.latest).

When a RW transactions comes to TC, TC starts the prepare phase of two-phase
commit. When everyone is prepared, TC picks TrueTime.latest as the commit
timestamp. It then *waits* until its TrueTime.earliest is beyond the commit
timestamp. This is what the paper calls *commit-wait*. After commit wait, TC is
sure that the true real-time has surpassed commit timestamp. It responds to the
client that the transaction was committed at the commit timestamp and starts the
second phase of the two-phase commit asking everyone to commit at the commit
timestamp. Other shards run the second phase of two-phase commit normally: apply
the writes, release all the locks, and advance safe time.

# Summary
Spanner is a geo-distributed sharded database supporting atomic cross-shard
transactions with strict serializability while allowing snapshot reads, i.e,
lock-free read-only transactions. Read-write transactions are done atomically
using two-phase commits (pessimistic concurrency control).  Snapshot reads are
done by putting a monotonic timestamp version on every update (multi-version
concurrency control). Network delays between deciding the commit timestamp and
writing the committed value is handled by blocking lock-free reads at timestamps
after *safe time*. 

Clock skew across different servers is handled by exposing clock uncertainty to
each server using the TrueTime API. Each RW transaction is given TrueTime.latest
timestamp; transaction coordinator does a *commit wait* to ensure real time has
indeed passed commit timestamp before replying to client/actually committing.
Commit-wait duration directly depends on time uncertainty interval. Time
uncertainty is controlled using per-datacenter time masters equipped with atomic
clocks and GPS receivers that do not drift as such. 

Two-phase commits can block for a long time if transaction coordinator crashes
after the participants have said YES for a prepare. Spanner makes all the
shards, including transaction coordinators for RW transactions, replicated state
machines on top of Paxos (consensus protocol like [Raft](./storage-raft.md)).
All the cross shard communication is driven by Paxos leaders. If Paxos leader
crashes, another follower becomes the leader and continues the transaction. This
largely relieves the blocked two-phase commit due to crashed transaction
coordinator.

Spanner actually allows lock-free reads from Paxos followers as well to improve
read-throughput. Followers also maintain safe time. Follower safe time can never
go beyond leader's safe time. Follower's safe time is similar, in principle, to
blocking reads in [zookeeper](./storage-zookeeper.md) until the server has
caught up on the request's zxid.

The paper talks about many other interesting details such as how to ensure
uncorrelated failures in time masters, what to do about clock skew at the time
of leader replacement since leaders also given [leases](./storage-zookeeper.md),
how leases help in keeping timestamp of writes in replicated log monotonic, how
two-phase commits are completed after a new Paxos leader is elected, how data is
sharded across Paxos groups, how can we provide an earlier timestamp than
TrueTime.latest in some cases, etc.

Spanner has a popular open-source incarnation called CockroachDB that provides
the same guarantees (strict serializability and snapshot reads) without
requiring time masters! They use *hybrid logical clocks*.
