# Bayou

In this lab, we implement Bayou. We do several simplifications over Bayou. 

**No Lamport clocks:** The weakly-connected distributed Bayou servers are just
processes on a single system. Therefore, there is no question of clock drift
between the servers. We need not use Lamport clocks in our setup. However,
system clocks *can go back* in time due to NTP syncs. This can be a problem 
since Bayou's design assumes monotonic clocks. We therefore use monotonic clocks
using Python's `time.monotonic` instead of system clocks.

**Separate committed/tentative states and logs:** Bayou maintains a database
where each row has two bits to signify whether the row is tentative/committed.
This is done to de-duplicate states for reduced memory consumption. We are not
going to store very large states in this lab. Therefore, for simplicity, every
server simply maintain two different states: one committed and one tentative.
Similarly, for simplicity, every server maintains two different logs: one
committed and one tentative.

**No conflict resolution:** Bayou does automatic conflict resolution. In each
write, applications provide a conflict detection and a conflict resolution
function. In the paper's calendar example, users specify multiple meeting start
times. A conflict is detected if the room is booked by someone else at an
overlapping slot. Conflict is resolved by booking at an alternate time. Writes
in this lab never have a conflict and therefore conflicts never need to be
resolved.

**Invertible writes:** Bayou maintains a separate *undo log* so that tentative
logs can be rolled back. For example, let us say `x=0` in the tentative state
before we do a tentative write of `x=4`. Bayou will remember `x=4` in the
tentative portion of the log.  Tentative logs can be exchanged between servers.
In undo log, it needs to remember `x=0` to be able to rollback `x=4`. Undo logs
are never exchanged; each server locally maintains its own undo logs. In our lab
setup, we will not maintain undo logs.  We assume that the writes are
invertible. For example, if writes are of the form `x+=1`, we can undo it by
subtracting `1`.

**No garbage collection, FT, persistence:** We never garbage collect logs so we
need not maintain the `O` timestamp. We also don't crash servers so we don't
want to think about persistence. We keep all states and logs in memory.

All these simplifications leaves us with implementing the crux of Bayou. We
still need to maintain `C` and `F` timestamps to do anti-entropy between
servers. Our writes are non-commutative so that simple CRDTs can not work, i.e,
rolling back is necessary. Our tests will send special messages to create and
heal network partitions.

To fulfill the above simplifications, our state is going to simply be a string.
Clients send operations to append a character to the state. Appends are
invertible: remove last character from the string. Appends can always be
applied, i.e, they never conflict with other appends. Appends are not
commutative.

Other states and operations can also fulfill above simplifications. For example,
the state can be a natural number and clients can send arithmetic operations
like `+` and `*` (assuming client never tries to multiply with zero).


## System Design
### Core Components
We have same system core components as in lab3. Namely:-
1. Cluster:- Knows the connection topology of the servers and is responsible for starting and stopping the servers.
2. Server:- It is responsible for handling requests from clients. Owns a connection_stub in order to communicate with the other servers if required.
3. ConnectionStub:- Responsible for falicitating sending/receiving messages between servers.
4. Client:- Represents the interface for the end user of the system.

Simulating network partition:- Bayou is meant to be used in an unreliable network connections. So in order to simulate the partition we have added
additional methods in ConnectionStub (`sever_connection`, `unsever_connection`).  `sever_connection("a")` will not actually close the tcp connection to `a`, it will
just blacklist `a`, and any attempt to send messages to `a` using the `connection_stub` will result in failure.

### BayouSpecific Components
1. BayouServer:- In addition to process requests from the clients, the server also needs to perform `anti_entropy` with other servers once in a while.
2. BayouStorage:- Storage encapsulates `committed_logs`, `tentative_logs`, `committed_state`, `tentative_state`, `c` and `f`, as discussed above and in the paper.
The interfaces provided by the storage is as follows, read their docstrings for more details:-
  1. `commit(list[LogEntry])`
  2. `tentative(SortedList[LogEntry])`
  3. `apply(list of committed LogEntry, sorted list of tentative LogEntry)`
  4. `anti_entropy(c, f)`
In this lab we are basically asking you to implement these interfaces.
3. BayouAppServer:- Bayou can be used to implement any kind of app in contrast to CRAQ that is exclusively a key-value store, e.g in Bayou paper they implement meeting booking app and biblography app.
However there will be some components in all these apps, we have pulled the common components in `BayouServer` and moved application specific stuff in `BayouAppServer`. In lab4 the app is basically
a string appender.
4. BayouAppClient:- Similarly, the client will also be application specific. Since our app is string appender the client provides two interface `append_char()` and `get_string()`
5. AppLogEntry and AppState:- Similarly, log's data structure and state's data structure is also app specific. 


## Setup

```bash
pip install -e '.'

make test_storage        # Test Storage's implementation
make test_client         # End-to-End testing from client to server
```


## Deliverables
1. Methods that are to be implemented are marked as #TODO. Just implementing those methods is enough to pass this lab.
Feel free to create new helper methods to be used in those methods.
You can find the required TODOs using `grep -rni --include="*.py" "TODO" ./bayou`
2. Restrict all your changes to `app.py`, `storage.py`, and `server.py`.
3. Zip your submission using `bash create_submission <entry_num>`.
4. Run the evaluation script provided to be sure that the evaluation script is compatible with your submission:-
   1. cd `evaluation`
   2. Run `python evaluate.py <path_to_submission_zip>`
   3. Check scores in `scores/<entry_num>.csv`.
   4. Note that the tests are not exhaustive, more hidden tests will be added during evaluation.
5. Sumbit on moodle.
   
Recommended way to complete the assignment:-
1. Make all the tests in `test_storage` pass.
2. Make all the tests in `test_client` pass.
3. Note that the tests provided by us are not exhaustive and sucessfully passing them doesn't guarantee correctness, they merely act as
sanity checks. Keep in mind that your system must provide eventual consistency in any scenario it finds itself in.
So writing good quality tests is very crucial.
