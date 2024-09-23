import numpy as np
import ray
import time

# Start Ray.
ray.init()


@ray.remote
class ParameterServer(object):
    def __init__(self, dim):
        # Alternatively, params could be a dictionary mapping keys to arrays.
        self.params = np.zeros(dim)

    def get_params(self):
        return self.params

    def update_params(self, grad):
        self.params += grad


@ray.remote
def worker(*parameter_servers):
    for _ in range(100):
        # Get the latest parameters.
        parameter_shards = ray.get(
          [ps.get_params.remote() for ps in parameter_servers])
        params = np.concatenate(parameter_shards)

        # Compute a gradient update. Here we just make a fake
        # update, but in practice this would use a library like
        # TensorFlow and would also take in a batch of data.
        grad = np.ones(10)
        time.sleep(0.2)  # This is a fake placeholder for some computation.
        grad_shards = np.split(grad, len(parameter_servers))

        # Send the gradient updates to the parameter servers.
        for ps, grad in zip(parameter_servers, grad_shards):
            ps.update_params.remote(grad)


# Start two parameter servers, each with half of the parameters.
parameter_servers = [ParameterServer.remote(5) for _ in range(2)]

# Start 2 workers.
workers = [worker.remote(*parameter_servers) for _ in range(2)]

# Inspect the parameters at regular intervals.
for _ in range(5):
    time.sleep(1)
    print(ray.get([ps.get_params.remote() for ps in parameter_servers]))
