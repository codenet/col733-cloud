# TensorFlow

Let us now build the TensorFlow's dataflow graph for a very simple
*single-neuron* ML model training task. Let us say we have an ML model with one
neuron that takes a single input vector $x$ and outputs a single output vector
$z=f(wx+b)$.  The ground truth is a single output vector $y$. This gets
expressed in TensorFlow as:

```mermaid
graph LR
  w["Var(w)"]
	wr[Read]
  b["Var(b)"]
	br[Read]

	x ==> Mul
	w --o wr
	wr ==> Mul
	Mul ==> |wx| Add
	b --o br
	br ==> Add

	Add ==> |l=wx+b| f
	f ==> |"z=f(wx+b)"| error
	y ==> error
	error ==> |"(z-y)^2"| A:::hidden

	classDef hidden display: none;
```

All the functions in TensorFlow are *primitive* operators like multiplication
and addition with known differentiations. TensorFlow can apply chain rule on the
dataflow graph to find gradients:

$\frac{de}{db} = \frac{de}{dz}*\frac{dz}{dl}*\frac{dl}{db};\frac{de}{dw} = \frac{de}{dz}*\frac{dz}{dl}*\frac{dl}{dw}$

$\frac{de}{db} = 2(z-y)*f'(l)*1;\frac{de}{dw} = 2(z-y)*f'(l)*x$

Gradient calculation operators are auto-generated and added to the dataflow
graph (highlighted in orange). Gradients are used to update model parameters $w$
and $b$. `AssignAdd` has a control edge to `Read` to start next iteration.

```mermaid
graph LR
  w["Var(w)"]
	wr[Read]

  b["Var(b)"]
	br[Read]

	dedz["de/dz=2(z-y)"]:::autodiff
	dzdl["dz/dl=f'"]:::autodiff
	dedb[de/db]:::autodiff
	dedw[de/dw]:::autodiff
	ba[AssignAdd]:::autodiff
	wa[AssignAdd]:::autodiff
  w2["Var(w)"]:::autodiff
  b2["Var(w)"]:::autodiff

	x ==> Mul
	w --o wr
	wr ==> Mul
	Mul ==> |wx| Add
	b --o br
	br ==> Add

	Add ==> |l=wx+b| f
	Add ==> |l=wx+b| dzdl
	f ==> |"z=f(wx+b)"| dedz
	y ==> dedz

	dedz ==> dedb
	dzdl ==> dedb
	dedb ==> dedw
	x ==> dedw

	dedb ==> ba
	b2 ==> ba
	dedw ==> wa
	w2 ==> wa

	wa -...-> wr
	ba -.-> br

	classDef hidden display: none;
	classDef autodiff fill: orange;
```

After preparing the unified dataflow graph, TensorFlow *lowers* the graph on
available heterogenous devices. While lowering, operators using the same
variable reference such as `Read` and `Assign-f` must come to the same *device*.
Therefore, variable edges never cross device boundaries. If there is a data edge
crossing device boundary, special `Send` and `Recv` operators are inserted.
These operators have customized implementations for fast data transfer:
`cudaMemCpyAsync` if workers are CPU/GPU on same machine, DMA to transfer
between two GPUs on same machine, and TCP/RDMA for transfer between remote
machines.

```mermaid
graph LR
  w["Var(w)"]
	wr[Read]

  b["Var(b)"]
	br[Read]

	dedz["de/dz=2(z-y)"]:::autodiff
	dzdl["dz/dl=f'"]:::autodiff
	dedb[de/db]:::autodiff
	dedw[de/dw]:::autodiff
	ba[AssignAdd]:::autodiff
	wa[AssignAdd]:::autodiff
  w2["Var(w)"]:::autodiff
  b2["Var(b)"]:::autodiff

	sm[Send]:::sendrcv
	rm[Recv]:::sendrcv
	sdedb[Send]:::sendrcv
	rdedb[Recv]:::sendrcv

	subgraph Worker-1
		x ==> Mul
		w --o wr
		wr ==> Mul
		Mul ==> |wx| sm

		rdedb ==> dedw
		x ==> dedw
		dedw ==> wa
		w2 --o wa
		wa -.-> wr
	end

	sm ==> rm
	sdedb ==> rdedb

	subgraph Worker-2
		b --o br

		br ==> Add
		rm ==> |wx| Add
		Add ==> |l=wx+b| f
		Add ==> |l=wx+b| dzdl

		f ==> |"z=f(wx+b)"| dedz
		y ==> dedz

		dedz ==> dedb
		dzdl ==> dedb
		dedb ==> ba
		dedb ==> sdedb

		b2 --o ba
		ba -.-> br
	end

	classDef hidden display:none;
	classDef autodiff fill:orange;
	classDef sendrcv fill:cyan;
```

