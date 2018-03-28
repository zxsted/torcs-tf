import tensorflow as tf
import math

# Hyper Parameters
LAYER1_SIZE = 300
LAYER2_SIZE = 600
LEARNING_RATE = 1e-4
TAU = 0.001
BATCH_SIZE = 32

class ActorNetwork:
    """docstring for ActorNetwork"""
    def __init__(self, sess, action_dim, img_dim):

        self.sess = sess
        self.action_dim = action_dim
        
        self.img_input, self.action_output, self.net = self.create_network(action_dim, img_dim)
        self.target_img_input, self.target_action_output, \
            self.target_update, self.target_net = self.create_target_network(action_dim, self.net, img_dim)

        # define training rules
        self.create_training_method()

        self.sess.run(tf.initialize_all_variables())

        self.update_target()
        #self.load_network()

    def create_training_method(self):
        self.q_gradient_input = tf.placeholder(dtype=tf.float32, shape=[None, self.action_dim])
        self.parameters_gradients = tf.gradients(self.action_output, self.net, -self.q_gradient_input)
        self.optimizer = tf.train.AdamOptimizer(LEARNING_RATE).apply_gradients(list(zip(self.parameters_gradients, self.net)))
    
    def create_network(self, action_dim, img_dim):

        layer1_size = LAYER1_SIZE
        layer2_size = LAYER2_SIZE

        # Image input
        img_input = tf.placeholder(dtype=tf.float32, shape=[None, img_dim[0], img_dim[1], img_dim[2]])
        img_w1 = tf.Variable(tf.random_uniform(([5, 5, 12, 16]), -1e-4, 1e-4))
        img_b1 = tf.Variable(tf.random_uniform([16], 1e-4, 1e-4))
        img_layer1 = tf.nn.relu(tf.nn.conv2d(img_input, img_w1, [1, 1, 1, 1], "VALID") + img_b1)
        img_layer2 = tf.nn.max_pool(img_layer1, [1, 2, 2, 1], [1, 2, 2, 1], "VALID")

        img_w2 = tf.Variable(tf.random_uniform(([5, 5, 16, 32]), -1e-4, 1e-4))
        img_b2 = tf.Variable(tf.random_uniform([32], 1e-4, 1e-4))
        img_layer3 = tf.nn.relu(tf.nn.conv2d(img_layer2, img_w2, [1, 1, 1, 1], "VALID") + img_b2)
        img_layer4 = tf.nn.max_pool(img_layer3, [1, 2, 2, 1], [1, 2, 2, 1], "VALID")

        img_w3 = tf.Variable(tf.random_uniform(([3, 3, 32, 32]), -1e-4, 1e-4))
        img_b3 = tf.Variable(tf.random_uniform([32], 1e-4, 1e-4))
        img_layer5 = tf.nn.relu(tf.nn.conv2d(img_layer4, img_w3, [1, 1, 1, 1], "VALID") + img_b3)
        img_layer6 = tf.nn.max_pool(img_layer5, [1, 2, 2, 1], [1, 2, 2, 1], "VALID")

        flatten = int(img_layer6.shape[1] * img_layer6.shape[2] * img_layer6.shape[3])
        img_layer7 = tf.reshape(img_layer6, [-1, flatten])

        img_w4 = tf.Variable(tf.random_uniform([flatten, layer1_size], -1e-4, 1e-4))
        img_b4 = tf.Variable(tf.random_uniform([layer1_size], -1e-4, 1e-4))
        img_layer8 = tf.nn.relu(tf.matmul(img_layer7, img_w4) + img_b4)

        img_w5 = tf.Variable(tf.random_uniform([layer1_size, layer2_size], -1e-4, 1e-4))
        img_b5 = tf.Variable(tf.random_uniform([layer2_size], -1e-4, 1e-4))
        img_layer9 = tf.nn.relu(tf.matmul(img_layer8, img_w5) + img_b5)

        steer_w = tf.Variable(tf.random_uniform([layer2_size, 1], -1e-4, 1e-4))
        steer_b = tf.Variable(tf.random_uniform([1], -1e-4, 1e-4))
        steer = tf.tanh(tf.matmul(img_layer9, steer_w) + steer_b)

        # accel_w = tf.Variable(tf.random_uniform([layer2_size, 1], -1e-4, 1e-4))
        # accel_b = tf.Variable(tf.random_uniform([1], -1e-4, 1e-4))
        # accel = tf.sigmoid(tf.matmul(layer2, accel_w) + accel_b)

        # brake_w = tf.Variable(tf.random_uniform([layer2_size, 1], -1e-4, 1e-4))
        # brake_b = tf.Variable(tf.random_uniform([1], -1e-4, 1e-4))
        # brake = tf.sigmoid(tf.matmul(layer2, brake_w) + brake_b)
        
        # action_output = tf.concat([steer, accel, brake], 1)
        action_output = steer
        return img_input, action_output, \
               [img_w1, img_b1, img_w2, img_b2, img_w3, img_b3, img_w4, img_b4, img_w5, img_b5, steer_w, steer_b]

    def create_target_network(self, action_dim, net, img_dim):
        ema = tf.train.ExponentialMovingAverage(decay=1-TAU)
        target_update = ema.apply(net)
        target_net = [ema.average(x) for x in net]

        img_input = tf.placeholder(dtype=tf.float32, shape=[None, img_dim[0], img_dim[1], img_dim[2]])
        img_layer1 = tf.nn.relu(tf.nn.conv2d(img_input, target_net[0], [1, 1, 1, 1], "VALID") + target_net[1])
        img_layer2 = tf.nn.max_pool(img_layer1, [1, 2, 2, 1], [1, 2, 2, 1], "VALID")
        img_layer3 = tf.nn.relu(tf.nn.conv2d(img_layer2, target_net[2], [1, 1, 1, 1], "VALID") + target_net[3])
        img_layer4 = tf.nn.max_pool(img_layer3, [1, 2, 2, 1], [1, 2, 2, 1], "VALID")
        img_layer5 = tf.nn.relu(tf.nn.conv2d(img_layer4, target_net[4], [1, 1, 1, 1], "VALID") + target_net[5])
        img_layer6 = tf.nn.max_pool(img_layer5, [1, 2, 2, 1], [1, 2, 2, 1], "VALID")
        flatten = int(img_layer6.shape[1] * img_layer6.shape[2] * img_layer6.shape[3])
        img_layer7 = tf.reshape(img_layer6, [-1, flatten])
        img_layer8 = tf.nn.relu(tf.matmul(img_layer7, target_net[6]) + target_net[7])
        img_layer9 = tf.nn.relu(tf.matmul(img_layer8, target_net[8]) + target_net[9])
        steer = tf.tanh(tf.matmul(img_layer9, target_net[10]) + target_net[11])
        # accel = tf.sigmoid(tf.matmul(layer2,target_net[6]) + target_net[7])
        # brake = tf.sigmoid(tf.matmul(layer2,target_net[8]) + target_net[9])
        # action_output = tf.concat([steer, accel, brake], 1)

        action_output = steer
        return img_input, action_output, target_update, target_net

    def update_target(self):
        self.sess.run(self. target_update)

    def train(self, q_gradient_batch, img_batch):
        self.sess.run(self.optimizer, feed_dict={
            self.q_gradient_input : q_gradient_batch,
            self.img_input : img_batch
            })

    def actions(self, img_batch):
        return self.sess.run(self.action_output, feed_dict={
            self.img_input : img_batch
            })

    def action(self, img):
        return self.sess.run(self.action_output, feed_dict={
            self.img_input : [img]
            })[0]


    def target_actions(self, img_batch):
        return self.sess.run(self.target_action_output, feed_dict={
            self.target_img_input : img_batch
            })

    # f fan-in size
    def variable(self, shape, f):
        return tf.Variable(tf.random_uniform(shape, -1/math.sqrt(f), 1/math.sqrt(f)))


