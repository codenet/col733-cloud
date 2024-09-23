import tensorflow as tf
import datetime

print("Available devices:", tf.config.list_physical_devices())

x_train = tf.constant([[1.0], [2.0], [3.0], [4.0]], dtype=tf.float32)  
y_train = tf.constant([[2.0], [4.0], [6.0], [8.0]], dtype=tf.float32)  

w = tf.Variable([[1.0]], dtype=tf.float32, name='weight')
b = tf.Variable([0.0], dtype=tf.float32, name='bias')

def activation_function(x):
  with tf.device('/GPU:1'):
    return tf.nn.relu(x) 

def error_function(y_true, y_pred):
  with tf.device('/CPU:0'):
    return tf.square(y_true - y_pred)

optimizer = tf.keras.optimizers.SGD(learning_rate=0.01)

@tf.function
def train_step(x, y_true):
  with tf.device('/GPU:0'): 
    with tf.GradientTape() as tape:
      wx = tf.matmul(x, w)
      wx_plus_b = wx + b 
      z = activation_function(wx_plus_b)
      loss = error_function(y_true, z)
    
    gradients = tape.gradient(loss, [w, b])
    optimizer.apply_gradients(zip(gradients, [w, b]))
  
  return z, loss

log_dir = "logs/single_neuron/" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
writer = tf.summary.create_file_writer(log_dir)

tf.summary.trace_on(graph=True)

outputs, loss = train_step(x_train, y_train)

with writer.as_default():
  tf.summary.trace_export(name="model_trace", step=0)

print("USE `tensorboard --logdir logs/single_neuron` to visualise graph on TensorBoard")
