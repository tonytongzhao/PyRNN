import numpy as np
import theano
import theano.tensor as T
from lstm import InputPLayer, SoftmaxPLayer, LSTMLayer, SoftmaxLayer
from lib import  floatX, make_caches, get_params, SGD, PerSGD, momentum, one_step_updates,random_weights, sigmoid

class PerRNN:
    def __init__(self, dnodex,inputdim,dim):
        X=T.ivector()
	Y=T.ivector()
	Z=T.lscalar()
	NP=T.ivector()
	lambd = T.scalar()
	eta = T.scalar()
        temperature=T.scalar()
        num_input = inputdim
	dnodex.umatrix=theano.shared(floatX(np.random.randn(*(dnodex.nuser,inputdim, inputdim))))
        dnodex.pmatrix=theano.shared(floatX(np.random.randn(*(dnodex.npoi,inputdim))))
        dnodex.p_l2_norm=(dnodex.pmatrix**2).sum()
        dnodex.u_l2_norm=(dnodex.umatrix**2).sum()
        num_hidden = dim
        num_output = inputdim
        inputs = InputPLayer(dnodex.pmatrix[X,:], dnodex.umatrix[Z,:,:], name="inputs")
        lstm1 = LSTMLayer(num_input, num_hidden, input_layer=inputs, name="lstm1")
        #lstm2 = LSTMLayer(num_hidden, num_hidden, input_layer=lstm1, name="lstm2")
        #lstm3 = LSTMLayer(num_hidden, num_hidden, input_layer=lstm2, name="lstm3")
        softmax = SoftmaxPLayer(num_hidden, num_output, dnodex.umatrix[Z,:,:], input_layer=lstm1, name="yhat", temperature=temperature)

        Y_hat = softmax.output()

        self.layers = inputs, lstm1,softmax
        params = get_params(self.layers)
        #caches = make_caches(params)

        tmp_u=T.mean(T.dot(dnodex.pmatrix[X,:],dnodex.umatrix[Z,:,:]),axis=0)
        tr=T.dot(tmp_u,(dnodex.pmatrix[X,:]-dnodex.pmatrix[NP,:]).transpose())
        pfp_loss1=sigmoid(tr)
        pfp_loss=pfp_loss1*(T.ones_like(pfp_loss1)-pfp_loss1)
        tmp_u1=T.reshape(T.repeat(tmp_u,X.shape[0]),(inputdim,X.shape[0])).T
        pfp_lossv=T.reshape(T.repeat(pfp_loss,inputdim),(inputdim,X.shape[0])).T
	cost = lambd*10*T.mean(T.nnet.categorical_crossentropy(Y_hat, T.dot(dnodex.pmatrix[Y,:],dnodex.umatrix[Z,:,:])))+lambd*dnodex.p_l2_norm+lambd*dnodex.u_l2_norm
        updates = PerSGD(cost,params,eta,X,Z,dnodex)#momentum(cost, params, caches, eta)

        rlist=T.argsort(T.dot(tmp_u,dnodex.pmatrix.T))[::-1]
        n_updates=[(dnodex.pmatrix, T.set_subtensor(dnodex.pmatrix[NP,:],dnodex.pmatrix[NP,:]-eta*pfp_lossv*tmp_u1-eta*lambd*dnodex.pmatrix[NP,:]))]
	p_updates=[(dnodex.pmatrix, T.set_subtensor(dnodex.pmatrix[X,:],dnodex.pmatrix[X,:]+eta*pfp_lossv*tmp_u1-eta*lambd*dnodex.pmatrix[X,:])),(dnodex.umatrix, T.set_subtensor(dnodex.umatrix[Z,:,:],dnodex.umatrix[Z,:,:]+eta*T.mean(pfp_loss)*(T.reshape(tmp_u,(tmp_u.shape[0],1))*T.mean(dnodex.pmatrix[X,:]-dnodex.pmatrix[NP,:],axis=0)))-eta*lambd*dnodex.umatrix[Z,:,:])]
        
        self.train = theano.function([X,Y,Z, eta, lambd, temperature], cost, updates=updates, allow_input_downcast=True)
        self.trainpos=theano.function([X,NP,Z,eta, lambd],tmp_u, updates=p_updates,allow_input_downcast=True)
        self.trainneg=theano.function([X,NP,Z,eta, lambd],T.mean(pfp_loss), updates=n_updates,allow_input_downcast=True)
        
        
        self.predict_pfp = theano.function([X,Z], rlist, allow_input_downcast=True)

    def reset_state(self):
        for layer in self.layers:
            layer.reset_state()
