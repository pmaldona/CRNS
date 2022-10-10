#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jul  9 19:15:03 2022

@author: pmaldona

General Reaction Network Class
"""

from .CRNS import CRNS
from .RNLI import RNLI
import copy
    
class pyRN(CRNS,RNLI):
    
    def copy(self):
        return pyRN(copy.copy(self))
    
    pass


    
    
        

