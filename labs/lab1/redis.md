# Redis data structures for Lab

Redis started as a simple key-value store. 
```
$ redis-cli
127.0.0.1:6379> keys *
(empty array)
127.0.0.1:6379> set a b
OK
127.0.0.1:6379> get a
"b"
```

But it has been evolving to support more fancy data structures. In Lab 1, we
will be using sorted sets, streams, and functions.

## Sorted sets
Let's create a sorted set `words` with two entries `{world: 25, hello: 10}`.
```
127.0.0.1:6379> zadd words 25 "world"
(integer) 1
127.0.0.1:6379> zadd words 10 "hello"
(integer) 1
```

We can look at top words using `zrevrange`. `0 0` means show just one entry with
highest count.

```
127.0.0.1:6379> zrevrange words 0 1 WITHSCORES
1) "world"
2) "25"
3) "hello"
4) "10"
127.0.0.1:6379> zrevrange words 0 0 WITHSCORES
1) "world"
2) "25"
```

We can also modify any key by incrementing its value.
```
127.0.0.1:6379> zincrby words 23 hello
"33"
127.0.0.1:6379> zrevrange words 0 0 WITHSCORES
1) "hello"
2) "33"
```

> You can learn more about sorted sets at https://redis.io/commands/ZADD


## Redis streams
```
127.0.0.1:6379> xadd tweets * tweet "hello world"
"1643000413845-0"
```

This creates a stream `tweets` and adds an entry with key `tweet` and value
`hello world`. Doing so prints out the `id` of the added entry. `*`  suggests
that redis should auto-generate the ID.  Almost always, this is the right
choice.

We can verify the added entry.
```
127.0.0.1:6379> xrange tweets - +
1) 1) "1643000413845-0"
   2) 1) "tweet"
      2) "hello world"
``` 

`-` says that print entries from the beginning, `+` says that print till the
end.  This combo prints all the entries in the stream.

```
127.0.0.1:6379> xadd tweets * tweet "small world"
"1643000476853-0"
127.0.0.1:6379> xrange tweets - +
1) 1) "1643000413845-0"
   2) 1) "tweet"
      2) "hello world"
2) 1) "1643000476853-0"
   2) 1) "tweet"
      2) "small world"
``` 

We can also delete entries with xtrim. 
```
127.0.0.1:6379> xtrim tweets MAXLEN 0
(integer) 2
127.0.0.1:6379> xrange tweets - +
(empty array)
```
We passed `MAXLEN 0` meaning delete all entries.

A entry is basically a hashtable in itself. One entry can have multiple keys
and values.
```
127.0.0.1:6379> xadd tweets * tweet "small world" action "add"
"1643000547320-0"
127.0.0.1:6379> xadd tweets * tweet "small world" action "del"
"1643000554452-0"
127.0.0.1:6379> xadd tweets * tweet "hello world" action "del"
"1643000562588-0"
127.0.0.1:6379> xrange tweets - +
1) 1) "1643000547320-0"
   2) 1) "tweet"
      2) "small world"
      3) "action"
      4) "add"
2) 1) "1643000554452-0"
   2) 1) "tweet"
      2) "small world"
      3) "action"
      4) "del"
3) 1) "1643000562588-0"
   2) 1) "tweet"
      2) "hello world"
      3) "action"
      4) "del"
```

If we don't want all the values, we can specify `COUNT` in `xrange`. 
```
127.0.0.1:6379> xrange tweets - + COUNT 1
1) 1) "1643000547320-0"
   2) 1) "tweet"
      2) "small world"
      3) "action"
      4) "add"
```

We can change `-` to a particular ID and look at tweets starting from that id.  If 
we changed `+` to a particular ID, we would get tweets ending at that ID.

```
127.0.0.1:6379> xrange tweets 1643000562588-0 + COUNT 1
1) 1) "1643000562588-0"
   2) 1) "tweet"
      2) "hello world"
      3) "action"
      4) "del"
```

We can also count number of messages in a stream.
```
127.0.0.1:6379> xlen tweets
(integer) 3
```

### Consumer groups

Create a consumer group `gname` on the `tweets` stream. 

```
127.0.0.1:6379> xgroup create tweets gname 0
OK
```
`0` signifies that we are reading the stream from its beginning. 

Now two consumers `c0` and `c1` can read entries as part of the consumer group `gname`.

```
127.0.0.1:6379> xreadgroup GROUP gname c0 COUNT 1 STREAMS tweets >
1) 1) "tweets"
   2) 1) 1) "1643000547320-0"
         2) 1) "tweet"
            2) "small world"
            3) "action"
            4) "add"
127.0.0.1:6379> xreadgroup GROUP gname c1 COUNT 1 STREAMS tweets >
1) 1) "tweets"
   2) 1) 1) "1643000554452-0"
         2) 1) "tweet"
            2) "small world"
            3) "action"
            4) "del"
127.0.0.1:6379> xreadgroup GROUP gname c0 COUNT 1 STREAMS tweets >
1) 1) "tweets"
   2) 1) 1) "1643000562588-0"
         2) 1) "tweet"
            2) "hello world"
            3) "action"
            4) "del"
```

`>` symbolizes that give me the latest entry. Redis guarantees that both `c0` and
`c1` receive different entries. We could also give `COUNT`.

You can also provide timeout to determine idle streams. These may be used to switch 
worker to perfom other tasks (useful in case of load imbalance).

Now, what happens if `c0` crashes after reading from Redis. Another worker can
later examine the messages sent to `c0` using the `xpending` command.  Similar
to RabbitMQ, Redis is storing unacked entries in `Pending entries list`.

```
127.0.0.1:6379> xpending tweets gname - + 10 c0
1) 1) "1643000547320-0"
   2) "c0"
   3) (integer) 380609
   4) (integer) 1
2) 1) "1643000562588-0"
   2) "c0"
   3) (integer) 361830
   4) (integer) 1
```

This shows the entry id, consumer name, idle time in ms, and number of
deliveries. For example, the first entry has been delivered once to `c0` ~380
seconds earlier.

If `c0` were to acknowledge an entry, the entry will disappear from pending list.
```
127.0.0.1:6379> xack tweets gname 1643000547320-0
(integer) 1
127.0.0.1:6379> xpending tweets gname - + 10 c0
1) 1) "1643000562588-0"
   2) "c0"
   3) (integer) 1281175
   4) (integer) 1
```

`c1` can steal entries that were given if they have not been acknowledged since
the last 2 seconds.

```
127.0.0.1:6379> xautoclaim tweets gname c1 2000 - COUNT 1
1) 1) "1643000562588-0"
   2) "c1"
   3) (integer) 6593
   4) (integer) 2
```

> Read more about streams: https://redis.io/topics/streams-intro

## Functions
Redis also supports writing lua functions that are run atomically. We can call
other redis commands in the function and register it with redis.

```lua
#!lua name=mylib

local function my_hset(keys, args)
  local hash = keys[1]
  local time = redis.call('TIME')[1]
  return redis.call('HSET', hash, '_last_modified_', time, unpack(args))
end

redis.register_function('my_hset', my_hset)
```

We can let Redis know about the function.

```commandline
$ cat mylib.lua | redis-cli -a pass -x FUNCTION LOAD REPLACE
```

Finally, we can call the function from the command line.
```
127.0.0.1:6379> FCALL my_hset 1 myhash myfield "some value" another_field "another value"
(integer) 3
127.0.0.1:6379> HGETALL myhash
1) "_last_modified_"
2) "1640772721"
3) "myfield"
4) "some value"
5) "another_field"
6) "another value"
```

> Learn more about Redis
function: https://redis.io/docs/latest/develop/interact/programmability/functions-intro/

## Redis transactions
Redis also supports transactions that are run atomically. We will NOT be using
them in Lab 1 (you can learn about them and think why they cannot be used
instead of functions).

```
127.0.0.1:6379> MULTI
OK
127.0.0.1:6379(TX)> zincrby words 1 hello
QUEUED
127.0.0.1:6379(TX)> zincrby words 10 world
QUEUED
127.0.0.1:6379(TX)> EXEC
1) "34"
2) "35"
```

This is done ***atomically***. Another write/read to `words` cannot come in the
middle.

```
127.0.0.1:6379> WATCH words
OK
127.0.0.1:6379> MULTI
OK                                                    "In another tab"
127.0.0.1:6379(TX)> zincrby words 1 hello             127.0.0.1:6379> zincrby words 2 hello
QUEUED                                                "38"
127.0.0.1:6379(TX)> EXEC
(nil)
```

Transaction was rejected. Verify value with `zrevrange words 0 1 WITHSCORES`.

> Read more about transactions. https://redis.io/topics/transactions
>
> You can do all Redis interactions from its Python SDK: https://redis-py.readthedocs.io/en/stable/commands.html#core-commands