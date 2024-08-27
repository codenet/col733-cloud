import os
import pandas as pd
import random

def generate_random_sentence(word_list, num_words=10):
    return ' '.join(random.choice(word_list) for _ in range(num_words))

def generate_csv_files(folder_path, n, file_size_mb, num_words_per_row=10):
    os.makedirs(folder_path, exist_ok=True)

    word_list = [
        'the', 'quick', 'brown', 'fox', 'jumps', 'over', 'lazy', 'dog',
        'hello', 'world', 'python', 'code', 'generate', 'csv', 'file',
        'random', 'sentence', 'data', 'test', 'example', 'text', 'string',
        'physics', 'machine', 'working', 'macbook', 'cloud', 'system',
        'logic', 'chandy', 'lamport', 'teams', 'master', 'architect',
        'destination', 'song'
    ]

    rows_per_file = int(file_size_mb * 1024 / 1) 

    for i in range(n):
        # Generate random English sentences
        data = {
            'text': [generate_random_sentence(word_list, num_words_per_row) for _ in range(rows_per_file)]
        }
        df = pd.DataFrame(data)
        filename = os.path.join(folder_path, f'file_{i+1}.csv')
        df.to_csv(filename, index=False)

        print(f'Generated {filename} with approximately {file_size_mb} MB.')

folder_path = 'csv_files'
n = 5000  # Number of CSV files to generate
file_size_mb = 1 

generate_csv_files(folder_path, n, file_size_mb)
