
import os
import csv
from collections import Counter
import time
import json

start_time = time.time()

csv_files_folder = 'csv_files'

word_counts = Counter()

for filename in os.listdir(csv_files_folder):
    if filename.endswith('.csv'):
        csv_file_path = os.path.join(csv_files_folder, filename)
        with open(csv_file_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                text = row['text']
                tokens = text.split()
                word_counts.update(tokens)



end_time = time.time()

elapsed_time = (end_time - start_time) * 1000
print(f'Time taken: {elapsed_time:.2f} milliseconds')

word_counts = json.dumps(word_counts)
open("seq.txt", "w").write(word_counts)

