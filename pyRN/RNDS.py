#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jul  8 14:07:20 2022

@author: pmaldona

Reaction Network Decomposition Class 
"""
from .RNIRG import RNIRG
import numpy as np
from bitarray import bitarray as bt
from bitarray import frozenbitarray as fbt
from scipy.optimize import linprog
import networkx as nx
from itertools import chain, combinations
from typing import List, Any, Iterable
from functools import reduce
from bitarray.util import subset
from pulp import *
import re

class RNDS(RNIRG):

    # Verifies which species of a reaction network (not necessarily an organization) 
    # are overproducible. Inputs are species sp_set and process vector pr, 
    # returns a list of overproducible species
    def getOpSpBt(self,sp_set,opsp_set=None,pr=None,only_ver=False):     
        # Checks if input is bitarray, if it is not, it make the 
        # transformation
        if not (isinstance(sp_set,bt)):
            sp=bt(self.MpDf.shape[0])
            sp.setall(0)
            
            for i in sp_set:
                if i in self.MpDf.index.values:
                    ind=self.MpDf.index.get_loc(i)
                    sp[ind]=1
        else:
            sp=sp_set
        
        if opsp_set is None:
            opts=sp.copy()
        else:
            if not (isinstance(opsp_set,bt)):
                opts=bt(self.MpDf.shape[0])
                opts.setall(0)
                
                for i in opsp_set:
                    if i in self.MpDf.index.values:
                        ind=self.MpDf.index.get_loc(i)
                        opts[ind]=1
            else:
                opts=opsp_set
        
        if pr is None:
            v=bt(self.MpDf.shape[1])
            v.setall(1)    
            
        elif not (isinstance(pr,bt)):
            v=bt(self.MpDf.shape[1])
            v.setall(0)
            
            for i in pr:
                v[i]=1
        else:
            v=pr
            
        # If it's only one species and self mantained, the reuturns the specie
        # itself
        if sp.count()==1 and self.isSmFromSp(sp):
            return sp
        
        Ns=sp.count() # number of species (rows)
        nsp=list(set(range(len(sp)))-set(self.getIndArrayFromBt(sp))) #species no present
        
        rc =[] # creating variable of available reaction 
        for j in self.getIndArrayFromBt(v):
            if (all(self.MpDf.iloc[nsp,j]==0) and all(self.MrDf.iloc[nsp,j]==0)):
                rc.append(j) # selecting reactions that can be trigger with available species
        
        if len(rc)==0:
            sp.setall(0)
            return sp
        
        
        # stoichiometric matrix of rn with prepended destruction reactions
        S=self.MpDf.iloc[self.getIndArrayFromBt(sp),rc]-self.MrDf.iloc[self.getIndArrayFromBt(sp),rc]
        print("shape",S.shape)
        sp_names=S.index
        S=S.to_numpy()
        S=np.column_stack((-np.identity(Ns),S))
        S=S.tolist()
        
        # flow vector constraint: production of every species = 0
        f=np.zeros(Ns) #norm of porcess vector for minimization 
        f=f.tolist()


        # cost 0 for every reaction
        cost=np.zeros(Ns+len(rc)) #norm of porcess vector for minimization 
        cost=cost.tolist()
        
        # overproducible status for species (initially False, until proven to be True).
        o=[]
        for i in range(len(sp)):
            o.append(False)
            # cost[i]=1
        
        op_ind=np.empty(opts.count())
        k=0
        for i in opts.search(1):
            op_ind[k]=np.where(self.SpIdStrArray[i] == sp_names)[0]
            k+=1
        op_ind=op_ind.astype(int)
        
        for p in op_ind:
            print("p",p)
            S[p][p]=1 # creation instead of destruction for p
            f[p]=1 # production of p = 1 instead of 0, if it is possible with creation rate 0, then it is overproducible
            cost[p]=1  # cost for creation of p = 1 instead of 0
        # print("f",f)
        # print("S",S)
        # lineal programing calculation of existance of a solution to be 
        # self-mantainend
        
        res = linprog(cost, A_eq=S, b_eq=f,method='highs')
        # The unknown is the process vector v. The equations are S v = f with the inequality constraint v>=0 (rates can be 0).
        # Only the creation reaction for p is penalized in Cost (the rate should be 0 if p is overproducible).
        
        opsp=opts.copy()
        
        for i in range(Ns):
            if res.x[i]>0:
                opsp[i]=1
        # print("opsp",opsp)
        # print("opts",opts)
        print("solution",res.x)
        
        if all(res.x[op_ind]==0) and (not only_ver):
            return(opsp,res.x[self.MpDf.shape[0]:(self.MpDf.shape[0]+self.MpDf.shape[1])])
        
        elif all(res.x[op_ind]==0) and only_ver and (opsp==opts):
            return(opsp,res.x[self.MpDf.shape[0]:(self.MpDf.shape[0]+self.MpDf.shape[1])])
        
        else:
            opsp.setall(0)
            v=res.x[self.MpDf.shape[0]:(self.MpDf.shape[0]+self.MpDf.shape[1])]
            for ind,value in enumerate(v):
                v[ind]=0
            return(opsp,v)
        
    
    def getOpOrgProcess(self,sp_set,opsp_set=None,pr=None):
        '''
        

        Parameters
        ----------
        sp_set : Numpy arrary or Bitarray
            Species Id array or bitarray of species of an organization.
        opsp_set : Numpy arrary or Bitarray, 
            Species Id Array or species bitarray of species that must be 
            overproduced. The default is None.
        pr : Numpy array ot bitarray, optional
            indexes of active reactions. The default is None.

        Returns
        -------
        sp : list
            A feasible procees vector for a organization that also overproduce at least opsp_set.

        '''
        # Checks if input is bitarray, if it is not, it make the 
        # transformation
        if not (isinstance(sp_set,bt)):
            sp=bt(self.MpDf.shape[0])
            sp.setall(0)
            
            for i in sp_set:
                if i in self.MpDf.index.values:
                    ind=self.MpDf.index.get_loc(i)
                    sp[ind]=1
        else:
            sp=sp_set
        
        if opsp_set is None:
            opts=sp.copy()
        else:
            if not (isinstance(opsp_set,bt)):
                opts=bt(self.MpDf.shape[0])
                opts.setall(0)
                
                for i in opsp_set:
                    if i in self.MpDf.index.values:
                        ind=self.MpDf.index.get_loc(i)
                        opts[ind]=1
            else:
                opts=opsp_set
        
        if pr is None:
            v=bt(self.MpDf.shape[1])
            v.setall(1)    
            
        elif not (isinstance(pr,bt)):
            v=bt(self.MpDf.shape[1])
            v.setall(0)
            
            for i in pr:
                v[i]=1
        else:
            v=pr
            
        # If it's only one species and self mantained, the reuturns the specie
        # itself
        if sp.count()==1 and self.isSmFromSp(sp):
            return sp
        
        Ns=sp.count() # number of species (rows)
        nsp=list(set(range(len(sp)))-set(self.getIndArrayFromBt(sp))) #species no present
        
        rc =[] # creating variable of available reaction 
        for j in self.getIndArrayFromBt(v):
            if (all(self.MpDf.iloc[nsp,j]==0) and all(self.MrDf.iloc[nsp,j]==0)):
                rc.append(j) # selecting reactions that can be trigger with available species
        
        if len(rc)==0:
            sp.setall(0)
            return sp
        
        
        # stoichiometric matrix of rn with prepended destruction reactions
        S=self.MpDf.iloc[self.getIndArrayFromBt(sp),rc]-self.MrDf.iloc[self.getIndArrayFromBt(sp),rc]
        sp_names=S.index
        S=-S.to_numpy()
        S=S.tolist()
        
        # opverprodcible index respect a reduced stochimetric matrix
        op_ind=np.empty(opts.count())
        k=0
        for i in opts.search(1):
            op_ind[k]=np.where(self.SpIdStrArray[i] == sp_names)[0]
            k+=1
        op_ind=op_ind.astype(int)
        
        
        # flow vector constraint: production of every species = 0
        f=np.zeros(Ns) #norm of porcess vector for minimization 
        f[op_ind]=-1 # condition for the overproducied species
        f=f.tolist()
        
        # lower bound for all reaction, so all have to take place
        bounds=[]
        for i in range(len(rc)):
            bounds.append((1,None))
           
        # cost 0 for every reaction
        cost=np.ones(len(rc)) #norm of porcess vector for minimization 
        cost=cost.tolist()
        
        # Resloving the Lp under the organization condition 
        res = linprog(cost, A_ub=S, b_ub=f, bounds=bounds, method='highs')
        
        # creating result vector
        v=np.zeros(self.MpDf.shape[1])
        if res.status==0:
            k=0
            for i in rc:
               v[i]=res.x[k]
               k+=1
            return(v)
        
        else:
            return(None)

    
    def verifiyOp(self,sp_set,opsp_set,pr=None):     
        '''
        

        Parameters
        ----------
        sp_set : bitarray
            Set of species to check.
        opsp_set : bitarray
            Set of overproduced whitin sp_set to check..
        pr : list of integers or numpy array of integers, optional
            Indexes of active reactions. The default is None.

        Returns
        -------
        bool
            True if opsp are overproduced in the set sp_set, and reaction pr. Else False.
        numpy array
            If latter condition is True, returns related process vector. If False, return vector of zeros.

        '''
        # Checks if input is bitarray, if it is not, it make the 
        # transformation
        if not (isinstance(sp_set,bt)):
            sp=bt(self.MpDf.shape[0])
            sp.setall(0)
            
            for i in sp_set:
                if i in self.MpDf.index.values:
                    ind=self.MpDf.index.get_loc(i)
                    sp[ind]=1
        else:
            sp=sp_set
        
        if opsp_set is None:
            opts=sp.copy()
        else:
            if not (isinstance(opsp_set,bt)):
                opts=bt(self.MpDf.shape[0])
                opts.setall(0)
                
                for i in opsp_set:
                    if i in self.MpDf.index.values:
                        ind=self.MpDf.index.get_loc(i)
                        opts[ind]=1
            else:
                opts=opsp_set
        
        if pr is None:
            v=bt(self.MpDf.shape[1])
            v.setall(1)    
            
        elif not (isinstance(pr,bt)):
            v=bt(self.MpDf.shape[1])
            v.setall(0)
            
            for i in pr:
                v[i]=1
        else:
            v=pr
        
        opsp=self.SpIdStrArray[opsp_set.search(1)]
        
        nsp=list(set(range(len(sp)))-set(self.getIndArrayFromBt(sp))) #species no present
           
        rc =[] # creating variable of available reaction 
        for j in self.getIndArrayFromBt(v):
            if (all(self.MpDf.iloc[nsp,j]==0) and all(self.MrDf.iloc[nsp,j]==0)):
                rc.append(j) # selecting reactions that can be trigger with available species
           
        if len(rc)==0:
            sp.setall(0)
        
        else:   
               
            # stoichiometric matrix of rn with prepended destruction reactions
            S=self.MpDf.iloc[self.getIndArrayFromBt(sp),rc]-self.MrDf.iloc[self.getIndArrayFromBt(sp),rc]
            # S=np.column_stack((-np.identity(Ns),S))
            # S=S.tolist()
               
            # flow vector constraint: production of every species = 0
            # f=np.zeros(Ns) #norm of porcess vector for minimization 
            # f=f.tolist()
               
            # Name and type of problem
            prob = LpProblem("LP_Org_test", LpMinimize)
               
            # Definition of problem warabiles
            x = LpVariable.dicts("process", S.iloc[3].index, lowBound=0, cat='Continuous')
            # y = LpVariable.dicts("y", range(Ns+len(rc)), cat='Binary')
            
            # We define the objective function
            prob += lpSum([x[i] for i in x])
            for j in S.index:
                    if j in opsp:
                        prob +=lpSum([S.loc[j][i] * x[i] for i in S.loc[j].index]) >= 1
                    else:
                        prob +=lpSum([S.loc[j][i] * x[i] for i in S.loc[j].index]) == 0            

                  
            # Resolver el problema
            prob.solve()
               
            v_result=np.zeros(self.MpDf.shape[1])
            for v in prob.variables():        
                ind=int(re.search(r'\d+', v.name).group())
                v_result[ind]=v.varValue
        
            print("production:",S @ v_result[rc])
            
            if LpStatus[prob.status]=='Optimal':
                return True, v_result
            else:
                return False, np.zeros(self.MpDf.shape[1])
            
            
    # Verifies which species of a reaction network (not necessarily an organization) 
    # are overproducible. Inputs are species sp_set and process vector pr, 
    # returns a list of overproducible species
    def getallOpSpBt(self,sp_set,pr=None,):     
        # Checks if input is bitarray, if it is not, it make the 
        # transformation
        if not (isinstance(sp_set,bt)):
            sp=bt(self.MpDf.shape[0])
            sp.setall(0)
            
            for i in sp_set:
                if i in self.MpDf.index.values:
                    ind=self.MpDf.index.get_loc(i)
                    sp[ind]=1
        else:
            sp=sp_set
        
        
        if pr is None:
            v=bt(self.MpDf.shape[1])
            v.setall(1)    
            
        elif not (isinstance(pr,bt)):
            v=bt(self.MpDf.shape[1])
            v.setall(0)
            
            for i in pr:
                v[i]=1
        else:
            v=pr
            
        # If it's only one species and self mantained, the reuturns the specie
        # itself
        if sp.count()==1 and self.isSmFromSp(sp):
            return sp
        
        Ns=sp.count() # number of species (rows)
        nsp=list(set(range(len(sp)))-set(self.getIndArrayFromBt(sp))) #species no present
        
        rc =[] # creating variable of available reaction 
        for j in self.getIndArrayFromBt(v):
            if (all(self.MpDf.iloc[nsp,j]==0) and all(self.MrDf.iloc[nsp,j]==0)):
                rc.append(j) # selecting reactions that can be trigger with available species
        
        if len(rc)==0:
            sp.setall(0)
            return sp
        
        
        # stoichiometric matrix of rn with prepended destruction reactions
        S=self.MpDf.iloc[self.getIndArrayFromBt(sp),rc]-self.MrDf.iloc[self.getIndArrayFromBt(sp),rc]
        S=S.to_numpy()
        S=np.column_stack((-np.identity(Ns),S))
        S=S.tolist()
        
        # flow vector constraint: production of every species = 0
        f=np.zeros(Ns) #norm of porcess vector for minimization 
        f=f.tolist()
        
        # cost 0 for every reaction
        cost=np.zeros(Ns+len(rc)) #norm of porcess vector for minimization 
        cost=cost.tolist()
        
        # overproducible status for species (initially False, until proven to be True).
        o=[]
        for i in range(len(sp)):
            o.append(False)
        
        for p in range(Ns):
            if not (o[p]):  # already known overproducible species are skipped 
                
                S[p][p]=1 # creation instead of destruction for p
                f[p]=1 # production of p = 1 instead of 0, if it is possible with creation rate 0, then it is overproducible
                cost[p]=1  # cost for creation of p = 1 instead of 0
            
                # lineal programing calculation of existance of a solution to be 
                # self-mantainend
                
                res = linprog(cost, A_eq=S, b_eq=f,method='highs')
                # The unknown is the process vector v. The equations are S v = f with the inequality constraint v>=0 (rates can be 0).
                # Only the creation reaction for p is penalized in Cost (the rate should be 0 if p is overproducible).
                
                
                if(res.x[p]==0):
                
                    o[p] = True # no need of creation implies p is overproducible
                    for i in range(Ns):
                        if res.x[i]>0:
                            o[i]=True
            
                S[p][p] = -1 
                f[p] = 0
                cost[p] = 0  # original destruction reaction and zero values for next iteration
            
        
        opsp=bt(len(sp))
        opsp.setall(0)
        for i in range(len(o)):
            if o[i]:
                opsp[self.getIndArrayFromBt(sp)[i]]=1
                
        return(opsp)
    
    # Verifies which species of a reaction network (not necessarily an organization) 
    # are overproducible. Inputs are species sp_set and process vector pr, 
    # returns a list of overproducible species
    def getSpNeededToOrg(self,sp_set,pr=None,destruct=False):     
        # Checks if input is bitarray, if it is not, it make the 
        # transformation
        if not (isinstance(sp_set,bt)):
            sp=bt(self.MpDf.shape[0])
            sp.setall(0)
            
            for i in sp_set:
                if i in self.MpDf.index.values:
                    ind=self.MpDf.index.get_loc(i)
                    sp[ind]=1
        else:
            sp=sp_set
        
        if pr is None:
            v=bt(self.MpDf.shape[1])
            v.setall(1)    
            
        elif not (isinstance(pr,bt)):
            v=bt(self.MpDf.shape[1])
            v.setall(0)
            
            for i in pr:
                v[i]=1
        else:
            v=pr
            
        # If it's only one species and self mantained, the reuturns the specie
        # itself
        if sp.count()==1 and self.isSmFromSp(sp):
            return sp
        
        Ns=sp.count() # number of species (rows)
        nsp=list(set(range(len(sp)))-set(self.getIndArrayFromBt(sp))) #species no present
        
        rc =[] # creating variable of available reaction 
        for j in self.getIndArrayFromBt(v):
            if (all(self.MpDf.iloc[nsp,j]==0) and all(self.MrDf.iloc[nsp,j]==0)):
                rc.append(j) # selecting reactions that can be trigger with available species
       
        # stoichiometric matrix of rn with prepended creation and destruction reactions 
        S=self.MpDf.iloc[self.getIndArrayFromBt(sp),rc]-self.MrDf.iloc[self.getIndArrayFromBt(sp),rc]
        S=S.to_numpy()
        S=np.column_stack((np.identity(Ns),np.column_stack((-np.identity(Ns),S))))
        #print("S:",S)
        S=S.tolist()
       
        
        # production of every species = 0, always possible because of additional creation and destruction reactions
        f=np.zeros(Ns) 
        f=f.tolist()
        #print("f:",f)
        # original reactions with rate>=1 (any positive), prepended reactions with rate>=0
        h=-np.ones(2*Ns+len(rc))
        h[0:2*Ns]=0
        h=h.tolist()
        #print("h:",h)
        
        # cost 0 for every reaction
        cost=np.zeros(2*Ns+len(rc)) #norm of porcess vector for minimization
        cost[0:Ns+Ns*destruct]=1
        cost=cost.tolist()
        #print("cost:",cost)
        
        G=-np.identity(2*Ns+len(rc))
        #print("G:",G)
        G=G.tolist()
        
        res = linprog(cost, A_eq=S, b_eq=f, A_ub=G, b_ub=h, method='highs')
        # The unknown to be solved is the process column vector v = [vc,vd,vo] (creation/destruction/original network).
        # The result for v is stored in the variable rn.linp.r$X (vc is X[1:Ns], vd is X[Ns+(1:Ns)]).
        # The equations are S v = f (with f=0), G v >= h (i.e. [vc,vd,vo] >= [0,0,1] because G is the identity matrix).
        # Only the original network reactions are constrained to be strictly positive (here arbitrarily vo >= 1).
        # The cost is  Cost . vc  (dot product) or  Cost . vd  when destruction is penalized instead of creation.
        # The linear programming ideal result is every prepended creation reaction with rate 0 (minimal Cost 0).
        # It implies that there is at least one original process vector that can sustain every species (and even increase
        # them if destruction reactions have positive rate). In that case the reaction network is a proper organization.
        # If not it can be converted into one by adding the extra inflow of species with creation rate > 0.
        # Returns the indexes of species needed as extra inflow and overproduced species in the particular solution found.        
        
        return(dict(inf=np.where(res.x[0:Ns]>0)[0],ovp=np.where(res.x[Ns+1:2*Ns]>0)[0],v=res.x[0:Ns]))


    # Generates a base of overproduced species of a reaction network 
    # (not necessarily an organization). Inputs are species sp_set and 
    # process vector pr, returns a list of minium overproducible species sets.    
    def getOpBaseBtList(self,sp_set,pr=None):     
        # Checks if input is bitarray, if it is not, it make the 
        # transformation
        if not (isinstance(sp_set,bt)):
            sp=bt(self.MpDf.shape[0])
            sp.setall(0)
            
            for i in sp_set:
                if i in self.MpDf.index.values:
                    ind=self.MpDf.index.get_loc(i)
                    sp[ind]=1
        else:
            sp=sp_set
        
        if pr is None:
            v=bt(self.MpDf.shape[1])
            v.setall(1)    
            
        elif not (isinstance(pr,bt)):
            v=bt(self.MpDf.shape[1])
            v.setall(0)
            
            for i in pr:
                v[i]=1
        else:
            v=pr
            
            
        # If it's only one species and self mantained, the reuturns the specie
        # itself
        if sp.count()==1 and self.isSmFromSp(sp):
            return {"op_b":[sp]}
        
        Ns=sp.count() # number of species (rows)
        nsp=list(set(range(len(sp)))-set(self.getIndArrayFromBt(sp))) #species no present
        
        rc =[] # creating variable of available reaction 
        for j in self.getIndArrayFromBt(v):
            if (all(self.MpDf.iloc[nsp,j]==0) and all(self.MrDf.iloc[nsp,j]==0)):
                rc.append(j) # selecting reactions that can be trigger with available species
       
        # stoichiometric matrix of rn with prepended destruction reactions
        S=self.MpDf.iloc[self.getIndArrayFromBt(sp),rc]-self.MrDf.iloc[self.getIndArrayFromBt(sp),rc]
        S=S.to_numpy()
        S=np.column_stack((-np.identity(Ns),S))
        S=S.tolist()
        
        
        # flow vector constraint: production of every species = 0
        f=np.zeros(Ns) #norm of porcess vector for minimization 
        f=f.tolist()
        
        # cost 0 for every reaction
        cost=np.zeros(Ns+len(rc)) #norm of porcess vector for minimization 
        cost=cost.tolist()
        
        
        
        #collection for all overproduced bases
        op_b=[]
        
        # coleccion of process vector corresponding to the ovprodued set
        v=[]
        
        for p in range(Ns):
            
            # overproducible status for species (initially False, until proven to be True).
            o=[]
            for i in range(len(sp)):
                o.append(False)
            
            S[p][p]=1 # creation instead of destruction for p
            f[p]=1 # production of p = 1 instead of 0, if it is possible with creation rate 0, then it is overproducible
            cost[p]=1  # cost for creation of p = 1 instead of 0
            
            # lineal programing calculation of existance of a solution to be 
            # self-mantainend
            res = linprog(cost, A_eq=S, b_eq=f,method='highs')
            # The unknown is the process vector v. The equations are S v = f with the inequality constraint v>=0 (rates can be 0).
            # Only the creation reaction for p is penalized in Cost (the rate should be 0 if p is overproducible).

            if(res.x[p]==0):
            
                o[p] = True # no need of creation implies p is overproducible
                for i in range(Ns):
                    if res.x[i]>0:
                        o[i]=True
                
                # adding new overproduced set to the base
                opsp=bt(len(sp))
                opsp.setall(0)
                for i in range(len(o)):
                    if o[i]:
                        opsp[self.getIndArrayFromBt(sp)[i]]=1
                
                if not (opsp in op_b):
                    op_b.append(opsp)
                    
                    # adding corresponding proces to the base
                    # vi=np.zeros(self.MpDf.shape[1])
                    # vi[rc]=res.x[Ns:Ns+len(rc)]
                    # v.append(vi)
                    
                
            S[p][p] = -1 
            f[p] = 0
            cost[p] = 0  # original destruction reaction and zero values for next iteration
        
                
        # return({"op_b":op_b,"pr":v})
        return op_b

    # Decomposition function, catalytic species and the respective fragile 
    # cycles of the reaction network. It takes as input the existing 
    # overprduced species opsp, the exiting species sp ande the process vector
    # pr of the present reactions. It returns an array whose components 
    # indicate the  function performed by each species, correlative positions 
    # to sp species  vector. If the value is -1 it corresponds to an 
    # overproducible species, if it is -2 to a catalytic species and if it 
    # is 0 the species is not present. The integer values indicate belonging 
    # to the current fragile cycle.
    def getDcomArray(self,opsp_set,sp_set,pr=None):
        
        # Checks if input is bitarray, if it is not, it make the 
        # transformation
        if not (isinstance(sp_set,bt)):
            sp=bt(self.MpDf.shape[0])
            sp.setall(0)
            
            for i in sp_set:
                if i in self.MpDf.index.values:
                    ind=self.MpDf.index.get_loc(i)
                    sp[ind]=1
        else:
            sp=sp_set
            
        if not (isinstance(opsp_set,bt)):
            opsp=bt(self.MpDf.shape[0])
            opsp.setall(0)
            
            for i in opsp_set:
                if i in self.MpDf.index.values:
                    ind=self.MpDf.index.get_loc(i)
                    opsp[ind]=1
        else:
            opsp=opsp_set
      
        if pr is None:
            v=bt(self.MpDf.shape[1])
            v.setall(1)    
            
        elif not (isinstance(pr,bt)):
            v=bt(self.MpDf.shape[1])
            v.setall(0)
            
            for i in pr:
                v[i]=1
        else:
            v=pr
        
        # generetinf the decompotion vector
        dcom=np.zeros(len(sp))
        
        # # generating overproducible species
        # opsp = self.over_prod(sp,v)
        dcom[self.getIndArrayFromBt(opsp)]=-1
        
        # If it's only one species and self mantained, the reuturns the specie
        # itself
        if sp.count()==1 and self.isSmFromSp(sp):
            return dcom
        
        
        # generating matrices to find catalytic and non catalytic species
        sp_ind=self.getIndArrayFromBt(sp)
        c_m = self.MrDf.iloc[sp_ind,:].copy()
        nc_m = c_m.copy()
        
        for i in self.getIndArrayFromBt(v):
            c_m.iloc[:,i] = ((self.MpDf.iloc[sp_ind,i]!=0) & (self.MrDf.iloc[sp_ind,i]!=0)) & (self.MpDf.iloc[sp_ind,i]==self.MrDf.iloc[sp_ind,i])
            nc_m.iloc[:,i] = (self.MpDf.iloc[sp_ind,i])!=(self.MrDf.iloc[sp_ind,i])
        
        
        c_m=c_m.iloc[:,self.getIndArrayFromBt(v)]
        nc_m=nc_m.iloc[:,self.getIndArrayFromBt(v)]     
        
        #finding catalytic species
        csp=sp.copy()
        csp.setall(0)
        j=0
        
        
        
        for i in ((c_m.sum(axis=1)!=0) & (nc_m.sum(axis=1)==0)):
            if i:
                csp[sp_ind[j]]=1
            j+=1

        # findinng all other species that aren't catalysers o opverproducble
        fsp=sp.copy() & ~(csp.copy() | opsp.copy())
        
        nsp=list(set(range(len(sp)))-set(self.getIndArrayFromBt(sp))) #species no present
        
        rc =[] # creating variable of available reaction 
        for j in self.getIndArrayFromBt(v):
            if (all(self.MpDf.iloc[nsp,j]==0) and all(self.MrDf.iloc[nsp,j]==0)):
                rc.append(j) # selecting reactions that can be trigger with available species
        
        # if there aren't reactive 
        if(len(rc)==0):
            return
        
        # creating fragile cycles
        if fsp.count()>0:            
            # subselecting matrix for fragile cycles species
            m=self.MpDf.iloc[self.getIndArrayFromBt(fsp),rc]-self.MrDf.iloc[self.getIndArrayFromBt(fsp),rc]
            
            # creating matrix for find conneting species via reactions
            adj=np.zeros((fsp.count(),fsp.count()))
            for i in range(m.shape[1]):
                ka=np.where(m.iloc[:,i]!=0)[0]

                for j in ka:
                    adj[j,ka]=1    
                    
            adj[adj!=0]=1          
            adj = adj + adj.transpose()
            adj[range(adj.shape[0]), range(adj.shape[0])] = 0
            adj=adj>0
            
            fsp_v=np.zeros(fsp.count()) #index of equivalence classes of fragile cycles
            eci=0 
            
            while(any(fsp_v==0)):
                ec = np.where(fsp_v==0)[0][0] # auxilar variable for finding all species of the fragile cycle
                j=0
                while(True):
                    
                    if np.isscalar(ec):
                        ec=np.concatenate((ec,np.where(adj[:,ec])[0]),axis=None)
                    else:
                        ec=np.concatenate((ec,np.where(adj[:,ec[j]])[0]),axis=None)
                        
                    ec=np.unique(ec)
                    j+=1
                    if (j >= len(ec) ):
                        break
                    
                eci+=1 # numbering the equivalance class
                fsp_v[ec]=eci # classifying the corresponding fragile cycle 
           
            # identifying species from the corresponding fragile cycles
            for i in range(fsp.count()):
                dcom[self.getIndArrayFromBt(fsp)[i]]=fsp_v[i]
                
        # identifying catalyst species
        dcom[self.getIndArrayFromBt(csp)]=-2
        return dcom
                    
                                       
    # Function that verifiys if a decomposition input is semi-self-
    # mantained or not.
    def getSsmDcomArray(self,dcom):
        
        #classification of overproduced species
        opsp=np.where(dcom==-1)[0]

        nsp=np.where(dcom==0)[0] #no present species
        psp=np.where(dcom!=0)[0] #present species
        
        rc =[] # creating variable of available reaction 
        for j in range(self.MpDf.shape[1]):
            if (all(self.MpDf.iloc[nsp,j]==0) and all(self.MrDf.iloc[nsp,j]==0)):
                rc.append(j) # selecting reactions that can be trigger with available species
        # if there aren't reactive 
        if(len(rc)==0):
            return
        
        # Stochimetric matrix whit available species and reactions
        S=-self.MpDf.iloc[psp,rc]+self.MrDf.iloc[psp,rc]
        S=S.values.tolist()
        
        # condition of overproduction for overproduced species
        f=np.zeros(len(psp))
        f[np.isin(psp,opsp)]=-1
        f=f.tolist()
        
        nfcsp=list(set(nsp) | set(opsp)) #non present and opverproduced species, 
        fcrc =[] # creating variable of available reaction for fragile cycles 
        for j in range(self.MpDf.shape[0]):
            if (all(self.MpDf.iloc[nfcsp,j]==0) and all(self.MrDf.iloc[nfcsp,j]==0)):
                fcrc.append(j) # selecting reactions that can be trigger with available species
        # if there aren't reactive 
        # Matrix generation for the equality so fragile cycles species have production 0
        S_eq=(self.MpDf-self.MrDf).to_numpy()
        nfcr=list(set(rc)-set(fcrc))
        S_eq[:,nfcr]=0
       
        # cost funtion, all reactions must occur
        c=np.ones(len(rc)).tolist()
        
        bounds=[] #creation of bounds vector, solution sould be greater that 1 
        # for each component
        for i in range(len(rc)):
            bounds.append((1,None))
        
        # lineal programing calculation of existance of a solution to be 
        # self-mantainend
        
        # res = linprog(c, A_ub=S, b_ub=f, A_eq=S_eq, b_eq=f_eq, bounds=bounds)
        res = linprog(c, A_ub=S, b_ub=f, bounds=bounds,method='highs')
        
        # calculation of the production vector
        prod=(-np.array(S).dot(res.x))
        
        # Verifing if overproduced sepcies and fragile cycles species
        if all(prod[f==1]>1) and all(prod[f==0]==0):
            return True
        else:
            return False
    
    
    # def genCombElements(self,G,level,sp,pr):
    #     '''
        

    #     Parameters
    #     ----------
    #     G : TYPE
    #         DESCRIPTION.
    #     level : TYPE
    #         DESCRIPTION.
    #     sp : TYPE
    #         DESCRIPTION.
    #     pr : TYPE
    #         DESCRIPTION.

    #     Returns
    #     -------
    #     G : TYPE
    #         DESCRIPTION.
    #     bool
    #         DESCRIPTION.

    #     '''
    #     print("Comb level:",level)
    #     try:
    #         sup_level_sp=reduce(lambda x,y : x|y,map(lambda x: bt(x[0]),filter(lambda x: x[1]['level']>level, G.nodes(data=True))))
    #     except:
    #         return G, False
    #     try:
    #         inf_level_sp=reduce(lambda x,y : x|y,map(lambda x: bt(x[0]),filter(lambda x: x[1]['level']<=level, G.nodes(data=True))))
    #     except:
    #         return G, True
        
    #     not_in_inf_level=sup_level_sp & ~inf_level_sp
        
    #     if not_in_inf_level.count()==0.:
    #         return G, False
    #     else:
    #         for i in not_in_inf_level.search(1):
    #             level_sets=list(map(lambda x: (bt(x[0]),x[1]),filter(lambda x: x[1]['level']==level, G.nodes(data=True))))
    #             for j in level_sets:
    #                 opts=j.copy()
    #                 opts[i]=1
    #                 opsp , v = self.getOpSpBt(sp_set=sp,opsp_set=opts,pr=pr)
    #                 if opsp.count()>0:
    #                     G.add_node(fbt(opsp), level=opsp.count(), v=v)
                        
    #     return G, True
    
    # def genNextLevel(self,G,level):
    #     '''
        

    #     Parameters
    #     ----------
    #     G : networkx DiGraph
    #         overproducible lattice structure.
    #     level : int
    #         level ( number of species) for the unnion to create new added sets.

    #     Returns
    #     -------
    #     G : networkx DiGraph
    #         Updated overproducible lattice structure.

    #     '''
    #     print("next level:",level)
    #     def add_node_and_edges(a_node,b_node):
    #         G.add_node(fbt(a_node[0]|b_node[0]),level=(a_node[0]|b_node[0]).count()
    #                                       ,v=a_node[1]['v']+b_node[1]['v'])
    #         G.add_edge(fbt(a_node[0]),fbt(a_node[0]))
    #         G.add_edge(fbt(a_node[0]),fbt(b_node[0]))
            
    #     level_sets=list(map(lambda x: (bt(x[0]),x[1]),filter(lambda x: x[1]['level']==level, G.nodes(data=True))))
        
    #     for ind,f_set in enumerate(level_sets):
    #         print(f_set)
    #         union_sets=list(filter(lambda x: (f_set[0]|x[0]).count()==(level+1),level_sets[(ind+1):]))
    #         print(union_sets)
    #         if len(union_sets)>0:
    #             list(map(lambda x: add_node_and_edges(f_set, x),union_sets))
                
    #     return G    
        
    # def setOpStr(self,sp_set=None,pr=None):
    #     '''
        

    #     Parameters
    #     ----------
    #     sp_set : TYPE, optional
    #         DESCRIPTION. The default is None.
    #     pr : TYPE, optional
    #         DESCRIPTION. The default is None.

    #     Returns
    #     -------
    #     G : TYPE
    #         DESCRIPTION.

    #     '''
        
    #     if sp_set is None:
    #         sp=bt(self.MpDf.shape[0])
    #         sp.setall(1)
            
    #     elif not (isinstance(sp_set,bt)):
    #         sp=bt(self.MpDf.shape[0])
    #         sp.setall(0)
            
    #         for i in sp_set:
    #             if i in self.MpDf.index.values:
    #                 ind=self.MpDf.index.get_loc(i)
    #                 sp[ind]=1
    #     else:
    #         sp=sp_set
        
    #     if pr is None:
    #         v=bt(self.MpDf.shape[1])
    #         v.setall(1)    
            
    #     elif not (isinstance(pr,bt)):
    #         v=bt(self.MpDf.shape[1])
    #         v.setall(0)
            
    #         for i in pr:
    #             v[i]=1
    #     else:
    #         v=pr
            
    #     G = nx.DiGraph() # lattice overproducible structre as network graph
    #     opts=sp.copy()
    #     for level in range(1,sp.count()+1):
    #         if level==1:
    #             for i in sp.search(1):
    #                 opts.setall(0)
    #                 opts[i]=1
    #                 opsp , v = self.getOpSpBt(sp_set=sp,opsp_set=opts,pr=pr)
    #                 if opsp.count()>0:
    #                     G.add_node(fbt(opsp), level=opsp.count(), v=v)
    #             G, verification = self.genCombElements(G, level, sp, pr)
    #             G = self.genNextLevel(G,level)
    #         else:
    #             if verification:
    #                 verification = self.genCombElements(G, level, sp, pr)
    #                 G = self.genNextLevel(G,level)
    #             else:
    #                 G = self.genNextLevel(G,level)
                    
                    
    #     return G
    
    def getAllPermutation(self,sp_set,level):
        
        all_comb=combinations(self.getIndArrayFromBt(sp_set), level)
        return list(map(lambda x: fbt(self.getBtFromIndArray(x,len(sp_set))),all_comb))
    
    def addfOpfromList(self,G,sp,oplist,pr):
        
        for i in oplist:
            opsp , v = self.getOpSpBt(sp_set=sp,opsp_set=bt(i),pr=pr,only_ver=False)
            
            try:
                inf_level_sp=reduce(lambda x,y : x|y,map(lambda x: bt(x[0]),filter(lambda x: x[1]['level']<=i.count()-1, G.nodes(data=True))))
            except:
                inf_level_sp=opsp.copy()
                inf_level_sp.setall(0)
                
            if opsp.count()>0 and (not subset(opsp, inf_level_sp)):
                G.add_node(fbt(opsp), level=opsp.count(), v=v)
              
    def genOpBase(self,sp_set=None,pr=None):
        '''
        

        Parameters
        ----------
        sp_set : TYPE, optional
            DESCRIPTION. The default is None.
        pr : TYPE, optional
            DESCRIPTION. The default is None.

        Returns
        -------
        G : TYPE
            DESCRIPTION.

        '''
        
        if sp_set is None:
            sp=bt(self.MpDf.shape[0])
            sp.setall(1)
            
        elif not (isinstance(sp_set,bt)):
            sp=bt(self.MpDf.shape[0])
            sp.setall(0)
            
            for i in sp_set:
                if i in self.MpDf.index.values:
                    ind=self.MpDf.index.get_loc(i)
                    sp[ind]=1
        else:
            sp=sp_set
        
        if pr is None:
            v=bt(self.MpDf.shape[1])
            v.setall(1)    
            
        elif not (isinstance(pr,bt)):
            v=bt(self.MpDf.shape[1])
            v.setall(0)
            
            for i in pr:
                v[i]=1
        else:
            v=pr
            
        G = nx.DiGraph() # lattice overproducible structre as network graph
        for level in range(1,sp.count()+1):
            
            # try:
            #     sup_level_sp=reduce(lambda x,y : x|y,map(lambda x: bt(x[0]),filter(lambda x: x[1]['level']>level, G.nodes(data=True))))
            # except:
            #     break
            try:
                inf_level_sp=reduce(lambda x,y : x|y,map(lambda x: bt(x[0]),filter(lambda x: x[1]['level']<=level-1, G.nodes(data=True))))
                pos_comb=self.getAllPermutation(inf_level_sp, level)
            except:
                pos_comb=[]
            print("pos_pert",pos_comb)
            all_comb=self.getAllPermutation(sp, level)
            print("all_pert",all_comb)
            new_comb=list(filter(lambda x: x not in pos_comb, all_comb))
            new_comb=list(filter(lambda x: x not in list(G.nodes), new_comb))
            print("new_pert",new_comb)
            if len(new_comb)>0: 
                self.addfOpfromList(G, sp, new_comb, pr)            
            else:
                break
        
        return G
         
                    
            
    # Function that generates a Hasse diagram from a set of species with all 
    # the combinations of the overproduced base, obtaining all the 
    # decompositions. The input corresponds to a set of sp_set species which 
    # must be an organization and the output corresponds to a graph whose 
    # vertexs correspond to the different combinations of overproduced species. 
    # The edges corresponds to the join and meet of the overproduced species. 
    # Each vertex has an attribute that is the decomposition vector. 
    def getOpHasseNx(self,sp_set):
        # Checks if input is a bitarray, if it is not, it make the 
        # transformation
        if not (isinstance(sp_set,bt)):
            sp=bt(self.MpDf.shape[0])
            sp.setall(0)
            
            for i in sp_set:
                if i in self.MpDf.index.values:
                    ind=self.MpDf.index.get_loc(i)
                    sp[ind]=1
        else:
            sp=sp_set
      
        # generation of the overproduced base
        op_b=self.getOpBaseBtList(sp_set, self.getTriggerableRpBtFromSp(sp_set))
        # initialization of multigraph of opverproduced hasse 
        G = nx.DiGraph()
        all_op=sp.copy()
        all_op.setall(0)
        
        # steps count
        st=0
        
        if len(op_b)==0:
            st+=1
            op=bt(len(sp))
            op.all()
            dcom=self.getDcomArray(op, sp, self.getTriggerableRpBtFromSp(sp))
            G.add_node(fbt(op),level=0,
                        dcom=dcom)#,
            return G, st
        
        # The nodes corresponding to the overproduced base.
        for i in op_b:
            st+=1
            dcom=self.getDcomArray(i, sp, self.getTriggerableRpBtFromSp(sp))
            G.add_node(fbt(i),level=i.count(),
                        dcom=dcom)#,
                        # is_org=self.getDcomArray_ssm(dcom))
            all_op|=i
        
        

        # print("total levels: ",all_op.count())  
        # Generation of the multigraph of overproduced hasse, by number of 
        # overproduced species
        for i in range(all_op.count()):
            # print("level: ",i)
            # Overproudced sets by level (number of overproduced species)
            nodes = [x for x,y in G.nodes(data=True) if y['level']==i+1]
             
            # union whit connected opverproduced bases for each set in level i
            for j in nodes:
                
                # generating connected nodes, nodes that are not containend in j
                conn_nodes=[];
                for l in op_b:
                    if (not (l & bt(j)) == l) and (not fbt(bt(j)|l) in G):
                        conn_nodes.append(l)
                
                for k in conn_nodes:
                    op_new=fbt(bt(j)|k)
                    st+=1
                    # decomposition result
                    dcom=self.getDcomArray(op_new, sp, self.getTriggerableRpBtFromSp(sp))
                     
                    # node is added if si not in structrue
                    if not (op_new in G):
                        
                        G.add_node(op_new,level=op_new.count(),
                                  dcom=dcom)#,
                                  # is_org=self.getDcomArray_ssm(dcom))
       
                    # Adding edges corresponding to the hasse diagram
                    if i>0:
                        low_level = [x for x,y in G.nodes(data=True) if y['level']==i-1]
                        for m in low_level:    
                            if bt(m) & bt(op_new) == bt(m):  
                                G.add_edge(m,op_new)
      
        return G, st
        
    # Function that generates a Hasse diagram from a set of species with all 
    # the combinations of the overproduced base, obtaining all the 
    # decompositions. The input corresponds to a set of sp_set species which 
    # must be an organization and the output corresponds to a graph whose 
    # vertexs correspond to the different combinations of overproduced species. 
    # The edges corresponds to the join and meet of the overproduced species. 
    # Each vertex has an attribute that is the decomposition vector. 
    def getOpHasseNx_2(self,sp_set):
        # Checks if input is a bitarray, if it is not, it make the 
        # transformation
        if not (isinstance(sp_set,bt)):
            sp=bt(self.MpDf.shape[0])
            sp.setall(0)
            
            for i in sp_set:
                if i in self.MpDf.index.values:
                    ind=self.MpDf.index.get_loc(i)
                    sp[ind]=1
        else:
            sp=sp_set
      
        # generation of the overproduced base
        op_b=self.getOpBaseBtList(sp_set, self.getTriggerableRpBtFromSp(sp_set))
        # initialization of multigraph of opverproduced hasse 
        op_hasse = nx.DiGraph()
        all_op=sp.copy()
        all_op.setall(0)
        
        # The nodes corresponding to the overproduced base.
        for i in op_b:
            dcom=self.getDcomArray(i, sp, self.getTriggerableRpBtFromSp(sp))
            op_hasse.add_node(fbt(i),level=i.count(),
                        dcom=dcom)#,
                        # is_org=self.getDcomArray_ssm(dcom))
            all_op|=i
        
        # present opverpruced base elements to combine
        p_op=bt(len(op_b))
        p_op.setall(1)
        
        # Generation of the multigraph of overproduced hasse, by number of 
        # overproduced species
        for i in op_b:
            for j in list(op_hasse.nodes()):
                op_new=i | bt(j)
                # print("exploring: ",op_new)
                if not (op_new in op_hasse):
                    op_hasse.add_node(fbt(op_new),level=op_new.count(),
                                      dcom=self.getDcomArray(op_new, sp, self.getTriggerableRpBtFromSp(sp)))#,
                   
        #generating the edges of the graph:
        # for i in range(all_op.count()):
        #     for j in [x for x,y in op_hasse.nodes(data=True) if y['level']==i]:
        #         if i>0:
        #             for m in [x for x,y in op_hasse.nodes(data=True) if y['level']==i-1]:    
        #                 if bt(m) & bt(j) == bt(m):  
        #                     op_hasse.add_edge(m,j)
        print("op_hasse: ", len(op_hasse.nodes()))
        return(op_hasse)

    # Flatten a list using generators comprehensions.
    # Returns a flattened version of list lst.
    def flatten(self,lst: List[Any]) -> Iterable[Any]:


        for sublist in lst:
             if isinstance(sublist, list):
                 for item in sublist:
                     yield item
             else:
                 yield sublist
                 
    # Generates the powerset of an list of elements, returns a list of tuples
    # of each comination posible.
    def powerset(self,iterable):
        s = list(iterable)
        return chain.from_iterable(combinations(s, r) for r in range(len(s)+1))
    
    
    # Function that generates a Hasse diagram from a set of species with all 
    # the combinations of the overproduced base, obtaining all the 
    # decompositions. The input corresponds to a set of sp_set species which 
    # must be an organization and the output corresponds to a graph whose 
    # vertexs correspond to the different combinations of overproduced species. 
    # The edges corresponds to the join and meet of the overproduced species. 
    # Each vertex has an attribute that is the decomposition vector. 
    def getOpHasseNx_3(self,sp_set):
        # Checks if input is a bitarray, if it is not, it make the 
        # transformation
        if not (isinstance(sp_set,bt)):
            sp=bt(self.MpDf.shape[0])
            sp.setall(0)
            
            for i in sp_set:
                if i in self.MpDf.index.values:
                    ind=self.MpDf.index.get_loc(i)
                    sp[ind]=1
        else:
            sp=sp_set
      
        # generation of the overproduced base
        op_b=self.getOpBaseBtList(sp_set, self.getTriggerableRpBtFromSp(sp_set))
        # initialization of multigraph of opverproduced hasse 
        op_hasse = nx.DiGraph()
        all_op=sp.copy()
        all_op.setall(0)
        
        # The nodes corresponding to the overproduced base.
        for i in op_b:
            dcom=self.getDcomArray(i, sp, self.getTriggerableRpBtFromSp(sp))
            op_hasse.add_node(fbt(i),level=i.count(),
                        dcom=dcom)#,
                        # is_org=self.getDcomArray_ssm(dcom))
            all_op|=i
        
        # generating the powerset and eliminating redudant variables.
        op_b=list(map(self.getIndArrayFromBt,op_b))
        op_hasse=list(self.powerset(op_b))
        op_hasse=list(map(lambda x: set(list(self.flatten(x))),list(map(list,op_hasse))))
        op_hasse=list(map(sorted,op_hasse))
        op_hasse = [list(x) for x in set(tuple(x) for x in op_hasse)]

        # op_hasse=list(map(list,op_hasse))
        
        # generating all decompositions
        dcom=list(map(lambda x: self.getDcomArray(self.sp[x], sp, self.getTriggerableRpBtFromSp(sp)),op_hasse))
        print("op_hasse2: ", len(op_hasse))
        return(op_hasse)
    
    
    
    # Function that generates the polyhedra and polytopes that the fragile and 
    # overproduced cycles of a decomposition. It takes as an increment the 
    # overproduced species opsp_set, the total species sp_set, and the present 
    # reactions pr. It returns as objects the rays and vertices of the 
    # overproduced set op_ph and lists them with the respective rays 
    # and vertices of the fragile circuits fc_ph_list.   
    # def polyth(self,opsp_set,sp_set,pr):
    #     # Checks if input is a bitarray, if it is not, it make the 
    #     # transformation
    #     if not (isinstance(sp_set,bt)):
    #         sp=bt(self.MpDf.shape[0])
    #         sp.setall(0)
            
    #         for i in sp_set:
    #             if i in self.MpDf.index.values:
    #                 ind=self.MpDf.index.get_loc(i)
    #                 sp[ind]=1
    #     else:
    #         sp=sp_set
        
    #     if not (isinstance(opsp_set,bt)):
    #         opsp=bt(self.MpDf.shape[0])
    #         opsp.setall(0)
            
    #         for i in opsp_set:
    #             if i in self.MpDf.index.values:
    #                 ind=self.MpDf.index.get_loc(i)
    #                 opsp[ind]=1
    #     else:
    #         opsp=opsp_set
            
    #     if not (isinstance(pr,bt)):
    #         v=bt(self.MpDf.shape[0])
    #         v.setall(0)
            
    #         for i in pr:
    #             v[i]=1
    #     else:
    #         v=pr
        
        
        
    #     Ns=sp.count() # number of species (rows)
    #     nsp=list(set(range(len(sp)))-set(self.getIndArrayFromBt(sp))) #species no present
        
        
    #     rc =[] # creating variable of available reaction 
    #     for j in self.getIndArrayFromBt(v):
    #         if (all(self.MpDf.iloc[nsp,j]==0) and all(self.MrDf.iloc[nsp,j]==0)):
    #             rc.append(j) # selecting reactions that can be trigger with available species
        
    #     E = np.identity(len(v))
    #     f = np.zeros(len(v))
        
    #     proj =(E,f) 
       
    #     # stoichiometric matrix of rn with prepended destruction reactions
    #     S=self.MpDf-self.MrDf
    #     S=S.to_numpy()  
        
    #     S=np.concatenate((S,np.identity(len(v))),axis=0)
        
    #     p=np.zeros(Ns+len(v))
    #     p[self.getIndArrayFromBt(opsp)]=1
        
    #     ineq=(-S,-p)
        
    #     if set(range(len(v)))-set(rc) != set():
    #         print("d ind: ",list(set(range(len(v)))-set(rc)))
            
    #         d=f.copy()
    #         de=d.copy()
    #         de[np.array(list(set(range(len(v)))-set(rc)))]=1
    #         C=np.diag(de)
            
    #         eq=(C,d)            
    #         op_ph=ph.projection.project_polyhedron(proj, ineq, eq)
    #     else:
            
    #         op_ph=ph.projection.project_polyhedron(proj, ineq)
            
            
    #     dcom=self.getDcomArray(opsp,sp,v)
    #     print("dcom :",dcom)
    #     fc_ph_list=[]
        
    #     for i in np.unique(dcom[dcom>0]):
            
    #         print("i: ",i)
    #         sp_ind=np.where(dcom==i)[0]
    #         # print("sp_ind: ",sp_ind)
            
    #         # print("mr condition: ",self.MrDf.iloc[sp_ind,:].sum(axis=0)>0)
    #         # print("mp condition: ",self.MpDf.iloc[sp_ind,:].sum(axis=0)>0)
            
    #         sub_rc=set(np.where(self.MrDf.iloc[sp_ind,:].sum(axis=0)>0)[0])
    #         sub_rc=set(sub_rc) | set(np.where(self.MpDf.iloc[sp_ind,:].sum(axis=0))[0])
    #         sub_rc=np.array(list(sub_rc))
   
    #         sub_sp=set(np.where(self.MrDf.iloc[:,sub_rc].sum(axis=1)>0)[0])
    #         sub_sp=set(sub_sp) | set(np.where(self.MpDf.iloc[:,sub_rc].sum(axis=1)>0)[0])
    #         # sub_sp=np.array(list(sub_sp))
            
    #         print("sub_sp: ",sub_sp)
            
    #         nsp=list(set(range(len(sp)))-sub_sp) #species no present
    #         sub_rc =[] # creating variable of available reaction 
    #         for j in self.getIndArrayFromBt(v):
    #             if (all(self.MpDf.iloc[nsp,j]==0) and all(self.MrDf.iloc[nsp,j]==0)):
    #                 sub_rc.append(j) # selecting reactions that can be trigger with available species
           
    #         print("sub_rc: ",sub_rc)
            
    #         op_ind=np.array(set(self.getIndArrayFromBt(opsp)) & set(sp_ind))
    #         cy_ind=np.array(set(dcom[dcom==-2]) & set(sp_ind))
            
    #         E = np.identity(len(v))
    #         f = np.zeros(len(v))
            
    #         proj =(E,f)
        
    #         S=self.MpDf-self.MrDf
    #         de=np.zeros(len(v))
            
    #         de[sub_rc]=1
    #         S=np.concatenate((S,np.diag(de)),axis=0)
    #         p=np.zeros(Ns+len(v))
            
    #         # print("S: ",S)
            
    #         ineq=(-S,-p)
            
    #         # condition of free production for overproduced species (either 
    #         # positive or negative)
    #         if set(range(len(v)))-set(sub_rc) != set():
    #             # print("d ind: ",list(set(range(len(v)))-set(sub_rc)))
    #             d=f.copy()
    #             de=d.copy()
    #             de[np.array(list(set(range(len(v)))-set(sub_rc)))]=1
    #             C=np.diag(de)
                    
    #             eq=(C,d)

    #             fc_ph_list.append(ph.projection.project_polyhedron(proj, ineq, eq))
                
    #         else:
    #             fc_ph_list.append(ph.projection.project_polyhedron(proj, ineq))
            
            
        
    #     return({"op_ph":op_ph,"fc_ph_list":fc_ph_list})
            
            
                

