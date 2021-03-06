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
    def __init__(self, sess, state_dim, action_dim, img_dim):

        self.sess = sess
        self.state_dim  = state_dim
        self.action_dim = action_dim
        
        self.img_input, self.state_input, self.action_output, self.net = self.create_network(state_dim, action_dim, img_dim)
        self.target_img_input, self.target_state_input, self.target_action_output, \
            self.target_update, self.target_net = self.create_target_network(state_dim, action_dim, self.net, img_dim)

        # define training rules
        self.create_training_method()

        self.sess.run(tf.initialize_all_variables())

        self.update_target()
        #self.load_network()

    def create_training_method(self):
        self.q_gradient_input = tf.placeholder(dtype=tf.float32, shape=[None, self.action_dim])
        self.parameters_gradients = tf.gradients(self.action_output, self.net, -self.q_gradient_input)
        self.optimizer = tf.train.AdamOptimizer(LEARNING_RATE).apply_gradients(list(zip(self.parameters_gradients, self.net)))
    
    def create_network(self, state_dim, action_dim, img_dim):

        layer1_size = LAYER1_SIZE
        layer2_size = LAYER2_SIZE

        # Image input
        img_input = tf.placeholder(dtype=tf.float32, shape=[None, img_dim[0], img_dim[1], img_dim[2]])
        img_w1 = tf.Variable(tf.random_uniform(([5, 5, 3, 16]), -1e-4, 1e-4))
        img_b1 = tf.Variable(tf.random_uniform([16], 1e-4, 1e-4))
        img_layer1 = tf.nn.relu(tf.nn.conv2d(img_input, img_w1, [1, 1, 1, 1], "VALID") + img_b1)
        img_layer2 = tf.nn.max_pool(img_layer1, [1, 3, 3, 1], [1, 3, 3, 1], "VALID")

        img_w2 = tf.Variable(tf.random_uniform(([5, 5, 16, 32]), -1e-4, 1e-4))
        img_b2 = tf.Variable(tf.random_uniform([32], 1e-4, 1e-4))
        img_layer3 = tf.nn.relu(tf.nn.conv2d(img_layer2, img_w2, [1, 1, 1, 1], "VALID") + img_b2)
        img_layer4 = tf.nn.max_pool(img_layer3, [1, 3, 3, 1], [1, 3, 3, 1], "VALID")

        img_w3 = tf.Variable(tf.random_uniform(([3, 3, 32, 64]), -1e-4, 1e-4))
        img_b3 = tf.Variable(tf.random_uniform([64], 1e-4, 1e-4))
        img_layer5 = tf.nn.relu(tf.nn.conv2d(img_layer4, img_w3, [1, 1, 1, 1], "VALID") + img_b3)
        img_layer6 = tf.nn.max_pool(img_layer5, [1, 3, 3, 1], [1, 3, 3, 1], "VALID")

        flatten = int(img_layer6.shape[1] * img_layer6.shape[2] * img_layer6.shape[3])
        img_layer7 = tf.reshape(img_layer6, [-1, flatten])

        img_w4 = tf.Variable(tf.random_uniform([flatten, layer1_size], -1e-4, 1e-4))
        img_b4 = tf.Variable(tf.random_uniform([layer1_size], -1e-4, 1e-4))
        img_layer8 = tf.nn.relu(tf.matmul(img_layer7, img_w4) + img_b4)

        # Scalar state input
        state_input = tf.placeholder(dtype=tf.float32, shape=[None, state_dim])
        state_w1 = self.variable([state_dim, layer1_size], state_dim)
        state_b1 = self.variable([layer1_size], state_dim)

        layer1 = tf.nn.relu(tf.matmul(state_input, state_w1) + state_b1)
        layer2 = tf.concat([img_layer8, layer1], 1)

        state_w2 = self.variable([layer1_size * 2, layer2_size], layer1_size * 2)
        state_b2 = self.variable([layer2_size], layer1_size * 2)
        layer3 = tf.nn.relu(tf.matmul(layer2, state_w2) + state_b2)

        steer_w = tf.Variable(tf.random_uniform([layer2_size, 1], -1e-4, 1e-4))
        steer_b = tf.Variable(tf.random_uniform([1], -1e-4, 1e-4))
        steer = tf.tanh(tf.matmul(layer3, steer_w) + steer_b)

        # accel_w = tf.Variable(tf.random_uniform([layer2_size, 1], -1e-4, 1e-4))
        # accel_b = tf.Variable(tf.random_uniform([1], -1e-4, 1e-4))
        # accel = tf.sigmoid(tf.matmul(layer2, accel_w) + accel_b)

        # brake_w = tf.Variable(tf.random_uniform([layer2_size, 1], -1e-4, 1e-4))
        # brake_b = tf.Variable(tf.random_uniform([1], -1e-4, 1e-4))
        # brake = tf.sigmoid(tf.matmul(layer2, brake_w) + brake_b)
        
        # action_output = tf.concat([steer, accel, brake], 1)
        action_output = steer
        return img_input, state_input, action_output, \
               [state_w1, state_b1, state_w2, state_b2, steer_w, steer_b, img_w1, img_b1, img_w2, img_b2, img_w3, img_b3, img_w4, img_b4]

    def create_target_network(self, state_dim, action_dim, net, img_dim):
        state_input = tf.placeholder(dtype=tf.float32, shape=[None, state_dim])
        ema = tf.train.ExponentialMovingAverage(decay=1-TAU)
        target_update = ema.apply(net)
        target_net = [ema.average(x) for x in net]

        img_input = tf.placeholder(dtype=tf.float32, shape=[None, img_dim[0], img_dim[1], img_dim[2]])
        img_layer1 = tf.nn.relu(tf.nn.conv2d(img_input, target_net[6], [1, 1, 1, 1], "VALID") + target_net[7])
        img_layer2 = tf.nn.max_pool(img_layer1, [1, 3, 3, 1], [1, 3, 3, 1], "VALID")
        img_layer3 = tf.nn.relu(tf.nn.conv2d(img_layer2, target_net[8], [1, 1, 1, 1], "VALID") + target_net[9])
        img_layer4 = tf.nn.max_pool(img_layer3, [1, 3, 3, 1], [1, 3, 3, 1], "VALID")
        img_layer5 = tf.nn.relu(tf.nn.conv2d(img_layer4, target_net[10], [1, 1, 1, 1], "VALID") + target_net[11])
        img_layer6 = tf.nn.max_pool(img_layer5, [1, 3, 3, 1], [1, 3, 3, 1], "VALID")
        flatten = int(img_layer6.shape[1] * img_layer6.shape[2] * img_layer6.shape[3])
        img_layer7 = tf.reshape(img_layer6, [-1, flatten])
        img_layer8 = tf.nn.relu(tf.matmul(img_layer7, target_net[12]) + target_net[13])
        layer1 = tf.nn.relu(tf.matmul(state_input, target_net[0]) + target_net[1])
        layer2 = tf.concat([img_layer8, layer1], 1)
        layer3 = tf.nn.relu(tf.matmul(layer2, target_net[2]) + target_net[3])
        steer = tf.tanh(tf.matmul(layer3, target_net[4]) + target_net[5])
        # accel = tf.sigmoid(tf.matmul(layer2,target_net[6]) + target_net[7])
        # brake = tf.sigmoid(tf.matmul(layer2,target_net[8]) + target_net[9])
        # action_output = tf.concat([steer, accel, brake], 1)

        action_output = steer
        return img_input, state_input, action_output, target_update, target_net

    def update_target(self):
        self.sess.run(self. target_update)

    def train(self, q_gradient_batch, state_batch, img_batch):
        self.sess.run(self.optimizer, feed_dict={
            self.q_gradient_input : q_gradient_batch,
            self.state_input : state_batch,
            self.img_input : img_batch
            })

    def actions(self, state_batch, img_batch):
        return self.sess.run(self.action_output, feed_dict={
            self.state_input : state_batch,
            self.img_input : img_batch
            })

    def action(self, state, img):
        return self.sess.run(self.action_output, feed_dict={
            self.state_input : [state],
            self.img_input : [img]
            })[0]


    def target_actions(self, state_batch, img_batch):
        return self.sess.run(self.target_action_output, feed_dict={
            self.target_state_input : state_batch,
            self.target_img_input : img_batch
            })

    # f fan-in size
    def variable(self, shape, f):
        return tf.Variable(tf.random_uniform(shape, -1/math.sqrt(f), 1/math.sqrt(f)))


