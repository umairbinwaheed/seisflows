
from glob import glob
from os.path import join

import numpy as np

from seisflows.tools import unix
from seisflows.tools.code import exists
from seisflows.tools.config import ParameterObj

PAR = ParameterObj('SeisflowsParameters')
PATH = ParameterObj('SeisflowsPaths')

import system
import solver
import preprocess


def DotProductLHS(keys, x, y):
    val = 0
    for key in keys:
        a = x[key].flatten()
        b = y[key].flatten()
        val += np.dot(a,b)
    return val


def DotProductRHS(keys, x, y):
    val = 0
    for key in keys:
        a = np.array([])
        b = np.array([])
        for iproc in range(PAR.NPROC):
            a = np.append(a, x[key][iproc])
            b = np.append(b, y[key][iproc])
        val += np.dot(a,b)
    return val



class test_adjoint(object):

    def check(self):
        """ Checks parameters and paths
        """

        # check paths
        if 'GLOBAL' not in PATH:
            raise ParameterError(PATH, 'GLOBAL')

        if 'LOCAL' not in PATH:
            setattr(PATH, 'LOCAL', None)

        if 'OUTPUT' not in PATH:
            raise ParameterError(PATH, 'OUTPUT')

        if 'SOLVER' not in PATH:
            raise ParameterError(PATH, 'SOLVER')

        # check input
        if 'DATA' not in PATH:
            setattr(PATH, 'DATA', None)

        if not exists(PATH.DATA):
            assert 'MODEL_TRUE' in PATH

        if 'MODEL_INIT' not in PATH:
            raise ParameterError(PATH, 'MODEL_INIT')


        # assertions
        if PAR.NSRC != 1:
            raise ParameterError(PAR, 'NSRC')


    def main(self):
        unix.rm(PATH.GLOBAL)
        unix.mkdir(PATH.GLOBAL)
        preprocess.setup()


        print 'SIMULATION 1 OF 3'
        system.run('solver', 'setup',
                   hosts='all')

        print 'SIMULATION 2 OF 3'
        self.prepare_model()
        system.run('solver', 'eval_func',
                   hosts='all',
                   path=PATH.GLOBAL)

        print 'SIMULATION 3 OF 3'
        system.run('solver', 'eval_grad',
                   hosts='all',
                   path=PATH.GLOBAL)


        # collect traces
        obs = join(PATH.SOLVER, self.event, 'traces/obs')
        syn = join(PATH.SOLVER, self.event, 'traces/syn')
        adj = join(PATH.SOLVER, self.event, 'traces/adj')

        obs,_ = preprocess.load(obs)
        syn,_ = preprocess.load(syn)
        adj,_ = preprocess.load(adj, suffix='.su.adj')

        # collect model and kernels
        model = solver.load(PATH.MODEL_INIT)
        kernels = solver.load(PATH.GLOBAL+'/'+'kernels'+'/'+self.event, suffix='_kernel')

        # LHS dot prodcut
        keys = obs.keys()
        LHS = DotProductLHS(keys, syn, adj)

        # RHS dot product
        keys = ['rho', 'vp', 'vs'] # model.keys()
        RHS = DotProductRHS(keys, model, kernels)

        print 
        print 'LHS:', LHS
        print 'RHS:', RHS
        print 'RELATIVE DIFFERENCE:', (LHS-RHS)/RHS
        print


    ### utility functions

    def prepare_model(self):
        model = PATH.OUTPUT +'/'+ 'model_init'
        assert exists(model)
        unix.ln(model, PATH.GLOBAL +'/'+ 'model')

    @property
    def event(self):
        if not hasattr(self, '_event'):
            self._event = unix.basename(glob(PATH.OUTPUT+'/'+'traces/*')[0])
        return self._event

