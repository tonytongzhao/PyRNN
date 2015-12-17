import numpy as np
import theano
import theano.tensor as T
from lstm import InputPLayer, SoftmaxPLayer, LSTMLayer, SoftmaxLayer
from lib import  floatX, make_caches, get_params, SGD, PerSGD, momentum, one_step_updates,random_weights

class PerRNN:
    def __init__(self, dnodex,inputdim,dim):
        X=T.ivector()
	Y=T.ivector()
	Z=T.lscalar()
	eta = T.scalar()
        temperature=T.scalar()
        self.dnodex=dnodex
        num_input = inputdim
	self.dnodex.umatrix=theano.shared(floatX(np.random.randn(*(self.dnodex.nuser,inputdim, inputdim))))
        self.dnodex.pmatrix=theano.shared(floatX(np.random.randn(*(self.dnodex.npoi,inputdim))))
        num_hidden = dim
        num_output = inputdim
        inputs = InputPLayer(self.dnodex.pmatrix[X,:], self.dnodex.umatrix[Z,:,:], name="inputs")
        lstm1 = LSTMLayer(num_input, num_hidden, input_layer=inputs, name="lstm1")
        lstm2 = LSTMLayer(num_hidden, num_hidden, input_layer=lstm1, name="lstm2")
        #lstm3 = LSTMLayer(num_hidden, num_hidden, input_layer=lstm2, name="lstm3")
        softmax = SoftmaxPLayer(num_hidden, num_output, self.dnodex.umatrix[Z,:,:], input_layer=lstm2, name="yhat", temperature=temperature)

        Y_hat = softmax.output()

        self.layers = inputs, lstm1, lstm2, softmax
        params = get_params(self.layers)
        #caches = make_caches(params)

	cost = T.mean(T.nnet.categorical_crossentropy(Y_hat, T.dot(self.dnodex.pmatrix[Y,:],self.dnodex.umatrix[Z,:,:])))
        updates = PerSGD(cost,params,eta,X,Z,self.dnodex)#momentum(cost, params, caches, eta)

        self.train = theano.function([X,Y,Z, eta, temperature], cost, updates=updates, allow_input_downcast=True)

        predict_updates = one_step_updates(self.layers)
        self.predict_char = theano.function([X, Z, temperature], Y_hat, updates=predict_updates, allow_input_downcast=True)

    def reset_state(self):
        for layer in self.layers:
            layer.reset_state()
