import subprocess
zen_of_python = subprocess.check_output(["python", "-c", "import this"])
corpus = zen_of_python.split()
# print(zen_of_python)

num_partitions = 3
chunk = len(corpus) // num_partitions
# print(chunk)
partitions = [ corpus[i * chunk: (i + 1) * chunk] for i in range(num_partitions) ]
# print(partitions)

def map_function(document):
  for word in document.lower().split():
    yield word, 1

import ray
ray.init()

@ray.remote
def apply_map(corpus, num_partitions=3):
    map_results = [list() for _ in range(num_partitions)]
    for document in corpus:
        for result in map_function(document):
            first_letter = result[0].decode("utf-8")[0]
            word_index = ord(first_letter) % num_partitions
            map_results[word_index].append(result)
    return map_results

map_results = [
    apply_map.options(num_returns=num_partitions)
    .remote(data, num_partitions)
    for data in partitions
]
# print(map_results)

# for i in range(num_partitions):
#     mapper_results = ray.get(map_results[i])
#     for j, result in enumerate(mapper_results):
#         print(f"Mapper {i}, return value {j}: {result}")

@ray.remote
def apply_reduce(*results):
    reduce_results = dict()
    for res in results:
        for key, value in res:
            if key not in reduce_results:
                reduce_results[key] = 0
            reduce_results[key] += value

    return reduce_results

outputs = []
for i in range(num_partitions):
    outputs.append(
        apply_reduce.remote(*[partition[i] for partition in map_results])
    )
# print(outputs)

counts = {k: v for output in ray.get(outputs) for k, v in output.items()}

sorted_counts = sorted(counts.items(), key=lambda item: item[1], reverse=True)
for count in sorted_counts:
    print(f"{count[0].decode('utf-8')}: {count[1]}")