# Introduction

## What is cloud?

Cloud is a collection of resources like storage, network, and compute; and
services like pre-built applications, frameworks, and libraries like Google
photos and databases. Cloud offer a flexible "pay-as-you-go" model to its users.

### Why cloud?

As software developers, we just want to focus on developing software. We don't 
want to **manage resources** since managing resources is extremely boring. Let
us say your laptop crashes after 5 years, i.e, ~1800 days. If you were running
your application on 200 laptops, one of them is crashing every 9 days on
average.  Every 9 days, you're forced to do the boring tasks of recovering your
crashed laptop.

Crashed laptops and servers is not just boring; it is also very expensive. Let
us say Amazon's servers crash for an hour during prime day. Within 1 hour,
Amazon loses millions of dollars. Loss of data can severely break user trust:
imagine a bank that loses last 100 transactions of an account.

There are a variety of reasons why servers crash: overheating, broken CPU fan,
disk motor gives up, etc. There can be a variety of reasons beyond the server
such as disconnected network or electricity; tornadoes and earthquakes.

Cloud tries to provide **fault tolerance**. A cloud provider typically maintains
multiple geo-distributed data centers to shield itself from natural disasters
like tornadoes and earthquakes. When some servers crash or become unreachable,
cloud providers can seamlessly move your resources to another server within the
same data center or across data centers. Using the techniques shown in this
course, the software layers ensure that you do not lose your data or your
computation when such moves happen.

For example, [AWS EC2 SLA](https://aws.amazon.com/compute/sla/) promises the 
following:

Instance-Level Uptime Percentage | Service Credit Percentage
---------------------------------|--------------------------
Less than 99.5% but equal to or greater than 99.0% | 10%
Less than 99.0% but equal to or greater than 95.0% | 30%
Less than 95.0% | 100%

In other words, AWS will give all your money back if your "instance" was down
for >5% of the time during each month. Companies buying lots of instances
typically negotiate stronger SLAs.

Cloud also provides **elasticity**. Let us say your web app gets posted on
Hacker News and suddenly your daily average users spike from 100 to 100k.  But
because of this load, your laptop hosting the web app crashed and you missed the
chance of gaining traffic. We could have purchased 1,000 laptops anticipating
this traffic but then we have paid a huge upfront cost for an imaginary traffic
while bearing the resource management pain. With cloud's pay-as-you-go model,
you can pay for 1000 servers when you actually have increased traffic to your
web app.

Let us say you are trying to target users in Canada. But your laptop is located 
in India giving an RTT of >1 second. In a study from Google, they found that
with every 100 ms increase in page load time, you lose ~7% of your users. With
cloud, you can rent a VM in close **promity** to the users reducing the RTT.
See [region-wise ping times](https://cloudpingtest.com/aws) for a comparison of
RTTs.

So, why take this course?
1. We will study real systems deployed in real companies serving millions of
customers 24x7.
2. You will work with these cloud systems at some point. 
   1. If you are building a startup or doing other personal projects, there is a
   high chance that you will use cloud infrastructure.
	 2. If you work at AWS, Google Cloud, Microsoft Azure, you might be managing
	 data centers and providing cloud services.
	 3. If you work at large companies with private data centers, you will again be
	 doing the same as above; just that your users are internal to the company.
	 4. If you are an ML researcher, you might want to run large ML experiments on
	 cloud.
	 5. If you enter research, you will find many interesting problems in this area.
3. The course is hands-on. We will recreate some systems from scratch that we study
in the course.

There are three topics that we cover
* Distributed computation
* Virtualization
* Distributed storage

## Why distributed computation?

You might want to spread your program onto multiple machines if you require
lower runtime than what is possible with one machine. Programs on a single
machine have higher-than-required runtimes because:
1. Data does not fit in memory and therefore we need to keep going to disk
(local or remote) to fetch data, or
2. We are bottlenecked by computational units available on a single machine.

One needs to carefully think about these requirements. It might be easier to buy
a bigger server with more memory and more powerful GPUs/CPUs. Today, you can buy
very powerful servers with 12TB of DRAM! *If possible, avoid distributed
computation altogether*.

The holy grail of distributed computation is to **build abstractions** such that
the programmer is only thinking about their own program logic to solve their
business problem. Ideally, the programmer writes a (serial?) program, tests it
on their computer with toy datasets, and just gives to cloud to run with larger
datasets. Such abstractions are super important because otherwise the programmer
has to deal with a number of difficult issues:

1. **Parallelization, scalability, resource utilization, and load balancing.** There
   can be thousands of machines available to the programmer, but using all of
   them efficiently is not trivial. Hopefully, you've realized this in your
   parallel programming course. The program needs to scale. 
   
   Scalability is formally captured using *speedup*, $S= T_s/T_p$ and
   *efficiency* $E= T_s/pT_p$ where $T_s$ is the serial runtime of the program,
   and $T_p$ is the parallel runtime of the program running on $p$ processors. A
   perfect program has $E=1$ i.e, it achieves linear speedups: doubling the
   number of processors halves the runtime.

2. **Straggler mitigation.** Data center environments are typically
   heterogenous. Different machines can be bought at different points-of-time so
   some machines may have older CPUs, HDDs instead of SSDs, etc. These machines
   may run slower than all the other machines. Even in a homogenous environment,
   machines may become slow over time because of having full disks, faulty
   configurations, or OS bugs. Finally, machines may be slow only intermittently
   due to being overloaded. We club all of these situations together and call
   slow machines as *stragglers*. Stragglers can severely elongate job
   completion times:
	```mermaid
	gantt
	    title A running program
	    dateFormat HH:mm
	    axisFormat %H:%M
	    section Machine 1
	        Task          : 18:00, 2m
	    section Machine 2
	        Task          : 18:00, 1.5m
	    section Straggler
	        Task          : 18:00, 5m
	```
   A good abstraction completes programs quickly even in the presence of stragglers.

3. **Fault tolerance.** When a program is spread across 100s of machines, it 
   becomes more likely that some machines will crash, or become unreachable due 
	 to crashes in network, etc.  Since these programs can be long-running, we do
	 not want to start all over again when things crash. We would like to somehow
	 continue running the program keeping the programmer oblivious to these
	 crashes. 

	 There are three primary approaches for fault tolerance:
	 1. Checkpoint regularly and recover from checkpoint. Checkpointing too
	 frequently may hurt performance. Checkpointing less frequently will lose too
	 much program progress; we will have to rollback to much older point in the 
	 program after a crash.
	 2. Replicated state machines. Multiple machines simultaneously run the same
	 program. This is costly in the common case- when nothing is crashing, and
	 therefore should be avoided whenever possible.
	 3. Rerun tasks. Break the program into small idempotent deterministic tasks.
	 The fastest approach is to just rerun the failed tasks.
	 
   We will discuss these approaches in the course.

## Virtualization

Virtualization is an act of virtualizing physical resources and is the driving
technology that enabled the cloud revolution. Virtualization is hard to define
without being circular so let us understand it with an example instead. 

Let us say that we want to invest into gold, so we buy 10 grams of gold which we
plan to sell 20 years later. However, this brings management and security
overhead. We now need to keep it safe to avoid theft, protect it from severe
temperature, pressure, and humidity. So instead of buying and managing physical
gold, we can buy "virtual gold" in the form of "gold bonds". A gold bond is just
a certificate validated by the government. The government promises that this 
bond can be sold at any time at the same rate as physical gold. Buying virtual
gold takes away all the management overhead of physical gold.

In similar terms, renting virtual machines takes away management overhead of
buying physical machines such as power outages, earthquakes, protecting from
DDoS attacks, etc. There is little upfront cost due to pay-as-you-go model: rent
more VMs as required. Cloud provider SLAs guarantee that we can use VMs whenever
we want them.

From sellers perspective, we can now **overprovision** our physical resources.
Let's say we had 10kg of gold reserves. If we are selling physical gold, we can
only sell 10kg worth of gold. But with gold bonds, we can actually sell 100kg of
gold bonds with the hope that not everyone will want to trade virtual gold for
physical gold at the same time. Of course, these ratios have to be carefully
controlled and regulated.

Large companies like Amazon and Google are anyways buying physical machines for
themselves. Buying more machines brings incremental management overhead for
them. They rent out unused physical machines by providing cloud services,
supported by VMs, to third-parties.

Virtualization brings several management advantages:

1. **Snapshot**: VMs can be snapshotted into a file. The snapshot includes the
application and the OS state. The VM can be later recovered from the snapshot at
the same or different physical machine. This helps cloud providers in
overprovisioning: they can snapshot and pause instances when they are not being
used.
2. **Migration**: A running VM can be moved from one physical machine to another
with almost zero downtime seen by the client. Migration helps with load
balancing, planned maintenance, and consolidation for power saving.
3. **Isolation**: Cloud providers can run VMs from competitor businesses on the
same physical machine. This is because VMs are isolated from each other. This
isolation tends to be stronger than the isolation provided to processes by the
OS.

Cloud providers write logic to overprovision their physical machines without 
violaiting SLAs. This logic manages VMs: where to place VMs, when to migrate,
where to migrate, etc. To the best of our knowledge, details of this is not
fully open so we do not cover these aspects.

Virtualization is supported by hypervisors also called virtual machine monitors
(VMM). VMM sits between OS and the hardware. Operating systems fool apps into 
thinking that they own the hardware. Apps can directly manipulate (a limited set
of) CPU registers and have full control over (virtual address space) memory.
Similarly, VMMs fool OS into thinking that they own the hardware. OS believes
that it can directly manipulate all CPU registers and have full control over
physical memory. However, of course, the VMM virtualizes the physical memory and
virtualizes key registers and hardware data structures without causing too much
performance overhead.

## Distributed storage

Storage is a key abstraction for building stateful applications. We will spend
majority of our time with storage. Distributed storage is hard to build because:

* For high performance, we shard our data into multiple disks over multiple server
* Due to multiple servers, we get constant faults
* For fault tolerance, we need to do replication
* Replication can lead to inconsistent replicas
* For consistency between replicas, we need to do network chit chat
* Network chit-chat lowers performance

Various definitions of consistency are explored while designing distributed
storage.  The most obvious one is where our distributed storage behaves just
like a single server. The storage applies one write at a time (even if they are
concurrent) and reads return the latest write.

For example, let us say we have 4 clients. C1 and C2 concurrently write to `x`, 
C3 and C4 later read `x`:

```
C1: |----Wx10-----|
C2: |----Wx10-----|
C3:                 |----Rx??-----|
C4:                 |----Rx??-----|
```

In this history, C3 and C4 can read 10 or 20, but they must be the same. This is
trivial behavior for single server, but single server has poor fault tolerance 
and can not fit large states.

