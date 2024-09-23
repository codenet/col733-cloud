import time

import ray
ray.init()

@ray.remote
def lcs(X, Y, bleft, bup, bsize, Lleft, Lup, Ldiag):
	"""
		:param X, Y: input strings
		:param (bleft, bup): block index
		:param bsize: size of the block: bsize*bsize
		:param Lleft: left block
		:param Lup: up block
		:param Ldiag: diagonal block

		:return: outputs block at the input block index
	"""
	# Declaring the array for storing the dp values
	L = [[None] * bsize for i in range(bsize)]

	def l(i, j):
		# print(bleft, bup, bsize, i, j)
		if i >= 0 and j >= 0:
			return L[i][j]
		if i < 0 and j < 0:
			return Ldiag[bsize+i][bsize+j] if Ldiag is not None else 0
		if i < 0:
			return Lleft[bsize+i][j] if Lleft is not None else 0
		return Lup[i][bsize+j] if Lup is not None else 0

	# Following steps build L[m+1][n+1] in bottom up fashion
	# Note: L[i][j] contains length of LCS of X[0..i-1]
	# and Y[0..j-1]
	for i in range(bsize):
		for j in range(bsize):
			left = bleft*bsize + i
			up = bup*bsize + j
			if left == 0 or up == 0:
				L[i][j] = 0
			if X[left-1] == Y[up-1]:
				L[i][j] = l(i-1, j-1) + 1
			else:
				L[i][j] = max(l(i-1, j), l(i, j-1))

	return L

# Driver code
if __name__ == '__main__':
	# S1 = "CLASS"
	# S2 = "LABS"
	S1 = "A"*3000
	S2 = "A"*3000

	m = len(S1)
	n = len(S2)
	# bsize = 1
	bsize = 15
	assert m % bsize == 0
	assert n % bsize == 0

	X = ray.put(S1)
	Y = ray.put(S2)

	f = [[None] * (n//bsize + 1) for i in range(m//bsize + 1)]

	start = time.time()
	for bleft in range(0, m//bsize):
		for bup in range(0, n//bsize):
			fleft = f[bleft-1][bup] if bleft > 0 else None
			fup = f[bleft][bup-1] if bup > 0 else None
			fdiag = f[bleft-1][bup-1] if bleft > 0 and bup > 0 else None

			f[bleft][bup] = lcs.remote(X, Y, bleft, bup, bsize, fleft, fup, fdiag)

	L = ray.get(f[m//bsize-1][n//bsize-1])
	elapsed = time.time() - start
	print(f"Length of LCS is {L[bsize-1][bsize-1]} bsize: {bsize} time: "
				f"{elapsed:.2f}")

# This repeats the Figure 10 of CIEL. We see that the optimum block size is
# somewhere in the middle. When we have high block size, the workers sit idle.
# When we have low block size, the co-ordination overhead starts to matter.
#
# 10 -> 10.83
# 15 -> 5.10
# 30 -> 1.33
# 50 -> 1.24
# 60 -> 0.70
# 100 -> 0.46
# 300 -> 0.53
# 600 -> 0.75
# 1000 -> 1.11
# 1500 -> 1.36
# 3000 -> 1.63