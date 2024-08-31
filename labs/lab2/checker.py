import json

r1 = open("checkpoints/Reducer_0_0.txt").read()
r2 = open("checkpoints/Reducer_1_0.txt").read()
r1 = json.loads(r1)
r2 = json.loads(r2)
r = r1 | r2

correct = json.loads(open("seq.txt").read())

if r == correct:
  print("CORRECT")
else:
  print("INCORRECT")
