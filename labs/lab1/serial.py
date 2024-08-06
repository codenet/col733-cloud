import sys
import os
import pandas as pd

DIR="/home/rohith/col733/data"

abs_files=[os.path.join(pth, f) for pth, dirs, files in os.walk(DIR) for f in files]

wc = {}

for filename in abs_files:
    print(filename)
    df = pd.read_csv(filename, lineterminator='\n')
    df["text"] = df["text"].astype(str)
    for text in df.loc[:,"text"]:
        if text == '\n':
            continue

        for word in text.split(" "):
            if word not in wc:
                wc[word] = 0
            wc[word] = wc[word] + 1

res = []
top_words = sorted(wc, key=wc.get, reverse=True)[:3]
for w in top_words:
    res.append((w, wc[w]))
print(res)