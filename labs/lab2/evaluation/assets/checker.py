import json
import os
import re
import sys

checkpoint_dir = sys.argv[1]
seq_file = sys.argv[2]
final_cp = 0

try:
    r1 = open(f"{checkpoint_dir}/Reducer_0_{final_cp}.txt").read()
    r2 = open(f"{checkpoint_dir}/Reducer_1_{final_cp}.txt").read()
except FileNotFoundError:
    print("INCORRECT")
    exit()

r1 = json.loads(r1)
r2 = json.loads(r2)
r = r1 | r2

try:
    correct = json.loads(open(seq_file).read())
except FileNotFoundError:
    print("NOSEQ")
    exit()

if r == correct:
    print("CORRECT")
else:
    print("INCORRECT")
