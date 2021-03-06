"""
======================
Eldo DC Source
======================

Class for ELDO DC sources.

Initially written for eldo-module by Okko Järvinen, okko.jarvinen@aalto.fi, 9.1.2020

Last modification by Marko Kosunen, marko.kosunen@aalto.fi, 22.01.2020 12:28

"""

import os
import sys
from abc import * 
from thesdk import *
from thesdk.iofile import iofile
import numpy as np
import pandas as pd

class eldo_dcsource(thesdk):
    """
    Class to provide DC source definitions to ELDO testbench.
    When instantiated in the parent class, this class automatically
    attaches eldo_dcsource objects to dcsource_bundle -bundle in testbench.

    Example
    -------
    Initiated in parent as: 
        `_=eldo_dcsource(self,name='dd',value=1.0,supply=True,pos='VDD',neg='VSS')`
    
    """

    @property
    def _classfile(self):
        return os.path.dirname(os.path.realpath(__file__)) + "/"+__name__

    def __init__(self,parent,**kwargs):
        '''
            Parameters
            ----------
            parent : object 
                The parent object initializing the 
                `eldo_dcsource` instance. Default None
            
            **kwargs :  
                    name : str  
                        Name of the source.
                    value : float  
                        Value of the source.
                    sourcetype : str  
                        Type of the DC source. Either 'V' for voltage
                        or 'I' for current.
                    extract : bool
                        Flag the source for current and power consumption extraction.
                        Default False.
                    ext_start : float
                        Time to start extracting average transient power consumption.
                        Default is 0.
                    ext_stop : float
                        Time to start extracting average transient power consumption.
                        Default is simulation end time.
                    pos : str
                        Name of the positive node in the ELDO netlist.
                    neg : str
                        Name of the negative node in the ELDO netlist.

        '''

        try:  
            self.parent = parent
            self._sourcetype=kwargs.get('sourcetype','V')
            self._name=kwargs.get('name','sourcename')
            self._pos=kwargs.get('pos','POSNODE')
            self._neg=kwargs.get('neg','NEGNODE')
            self._value=kwargs.get('value',0)
            self._extract=kwargs.get('extract',False)
            self._ext_start=kwargs.get('ext_start','start')
            self._ext_stop=kwargs.get('ext_stop','end')
            # TODO: Implement for example supply ramping

        except:
            self.print_log(type='F', msg="Eldo DC source definition failed.")

        if hasattr(self.parent,'dcsource_bundle'):
            self.parent.dcsource_bundle.new(name=self.name,val=self)

    @property
    def sourcetype(self):
        if hasattr(self,'_sourcetype'):
            return self._sourcetype
        else:
            self._sourcetype='V'
        return self._sourcetype
    @sourcetype.setter
    def sourcetype(self,value):
        self._sourcetype=value

    @property
    def name(self):
        if hasattr(self,'_name'):
            return self._name
        else:
            self._name='sourcename'
        return self._name
    @name.setter
    def name(self,value):
        self._name=value

    @property
    def neg(self):
        if hasattr(self,'_neg'):
            return self._neg
        else:
            self._neg='NEGNODE'
        return self._neg
    @neg.setter
    def neg(self,neg):
        self._neg=neg

    @property
    def pos(self):
        if hasattr(self,'_pos'):
            return self._pos
        else:
            self._pos='POSNODE'
        return self._pos
    @pos.setter
    def pos(self,pos):
        self._pos=pos

    @property
    def value(self):
        if hasattr(self,'_value'):
            return self._value
        else:
            self._value='0'
        return self._value
    @value.setter
    def value(self,value):
        self._value=value

    @property
    def extract(self):
        if hasattr(self,'_extract'):
            return self._extract
        else:
            self._extract=False
        return self._extract
    @extract.setter
    def extract(self,value):
        self._extract=value

    @property
    def ext_start(self):
        if hasattr(self,'_ext_start'):
            return self._ext_start
        else:
            self._ext_start='start'
        return self._ext_start
    @ext_start.setter
    def ext_start(self,value):
        self._ext_start=str(value)

    @property
    def ext_stop(self):
        if hasattr(self,'_ext_stop'):
            return self._ext_stop
        else:
            self._ext_stop='end'
        return self._ext_stop
    @ext_stop.setter
    def ext_stop(self,value):
        self._ext_stop=str(value)

