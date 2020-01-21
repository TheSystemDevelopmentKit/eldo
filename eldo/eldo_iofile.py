"""
======================
eldo_iofile package 
======================

Provides eldo- file-io related attributes and methods 
for TheSDK eldo

Initially written by Okko Järvinen, okko.jarvinen@aalto.fi, 9.1.2020

Last modification by Okko Järvinen, 21.01.2020 16:30

"""
import os
import sys
from abc import * 
from thesdk import *
from thesdk.iofile import iofile
import numpy as np
import pandas as pd
from numpy import genfromtxt
#from eldo.connector import intend

class eldo_iofile(iofile):
    """
    Class to provide file IO for eldo simulations. When created, 
    adds a eldo_iofile object to the parents iofile_bundle attribute.
    Accessible as iofile_bundle.Members['name'].

    Example
    -------
    Initiated in parent as: 
        _=eldo_iofile(self,name='foobar')
    
    Parameters
    -----------
    parent : object 
        The parent object initializing the 
        eldo_iofile instance. Default None
    
    **kwargs :  
            name : str  
                Name of the IO.
            ioformat : str
                Formatting of the IO signal.
                Not yet implemented.
            dir : str
                Direction of the IO: 'in'/'out'.
            iotype : str
                Type of the IO signal: 'event'/'sample'/'time'.
                Event type signals are time-value pairs (analog signal),
                while sample type signals are sampled by a clock signal (digital bus).
                Time type signals return a vector of timestamps corresponding
                to threshold crossings.
            datatype : str
                Datatype, not yet implemented.
            trigger : str
                Name of the clock signal node in the Spice netlist.
                Applies only to sample type outputs.
            vth : float
                Threshold voltage of the trigger signal and the bit rounding.
                Applies only to sample type outputs.
            edgetype : str
                Type of triggering edge: 'rising'/'falling'/'both'.
                When time type signal is used, the edgetype values can define the
                extraction type as: 'rising'/'falling'/'both'/'risetime'/'falltime'.
                Default 'rising'.
            big_endian : bool
                Flag to read the extracted bus as big-endian.
                Applies only to sample type outputs.
                Default False.
            rs : float
                Sample rate of the sample type input.
                Default None.
            vhi : float
                High bit value of sample type input.
                Default 1.0.
            vlo : float
                Low bit value of sample type input.
                Default 0.
            tfall : float
                Falltime of sample type input.
                Default 5e-12.
            trise : float
                Risetime of sample type input.
                Default 5e-12.
    """
    def __init__(self,parent=None,**kwargs):
        #This is a redundant check, but doens not hurt.to have it here too.
        if parent==None:
            self.print_log(type='F', msg="Parent of eldo input file not given")
        try:  
            super(eldo_iofile,self).__init__(parent=parent,**kwargs)
            self.paramname=kwargs.get('param','-g g_file_')

            self._ioformat=kwargs.get('ioformat','%d') #by default, the io values are decimal integer numbers

            self._trigger=kwargs.get('trigger','')
            self._vth=kwargs.get('vth',0.5)
            self._edgetype=kwargs.get('edgetype','rising')
            self._big_endian=kwargs.get('big_endian',False)
            self._rs=kwargs.get('rs',None)
            self._vhi=kwargs.get('vhi',1.0)
            self._vlo=kwargs.get('vlo',0)
            self._tfall=kwargs.get('tfall',5e-12)
            self._trise=kwargs.get('trise',5e-12)

        except:
            self.print_log(type='F', msg="eldo IO file definition failed.")


    @property
    def ioformat(self):
        if hasattr(self,'_ioformat'):
            return self._ioformat
        else:
            self._ioformat='%d'
        return self._ioformat
    @ioformat.setter
    def ioformat(self,value):
        self._ioformat=value

    @property
    def trigger(self):
        if hasattr(self,'_trigger'):
            return self._trigger
        else:
            self._trigger=""
            self.print_log(type='F',msg='Trigger node not given.')
        return self._trigger
    @trigger.setter
    def trigger(self,value):
        self._trigger=value

    @property
    def vth(self):
        if hasattr(self,'_vth'):
            return self._vth
        else:
            self._vth=0.5
        return self._vth
    @vth.setter
    def vth(self,value):
        self._vth=value

    @property
    def edgetype(self):
        if hasattr(self,'_edgetype'):
            return self._edgetype
        else:
            self._edgetype='rising'
        return self._edgetype
    @edgetype.setter
    def edgetype(self,value):
        self._edgetype=value

    @property
    def big_endian(self):
        if hasattr(self,'_big_endian'):
            return self._big_endian
        else:
            self._big_endian=False
        return self._big_endian
    @big_endian.setter
    def big_endian(self,value):
        self._big_endian=value

    @property
    def rs(self):
        if hasattr(self,'_rs'):
            return self._rs
        else:
            self._rs=None
        return self._rs
    @rs.setter
    def rs(self,value):
        self._rs=value

    @property
    def vhi(self):
        if hasattr(self,'_vhi'):
            return self._vhi
        else:
            self._vhi=1.0
        return self._vhi
    @vhi.setter
    def vhi(self,value):
        self._vhi=value

    @property
    def vlo(self):
        if hasattr(self,'_vlo'):
            return self._vlo
        else:
            self._vlo=0
        return self._vlo
    @vlo.setter
    def vlo(self,value):
        self._vlo=value

    @property
    def tfall(self):
        if hasattr(self,'_tfall'):
            return self._tfall
        else:
            self._tfall=5e-12
        return self._tfall
    @tfall.setter
    def tfall(self,value):
        self._tfall=value

    @property
    def trise(self):
        if hasattr(self,'_trise'):
            return self._trise
        else:
            self._trise=5e-12
        return self._trise
    @trise.setter
    def trise(self,value):
        self._trise=value

    @property
    def sourcetype(self): # Type of source for inputs (V or I)
        if hasattr(self,'_sourcetype'):
            return self._sourcetype
        else:
            self._sourcetype='V'
        return self._sourcetype
    @sourcetype.setter
    def sourcetype(self,value):
        self._sourcetype=value

    # Overloading file property to contain a list
    @property
    def file(self):
        self._file = []
        for ioname in self.ionames:
            self._file.append(self.parent.eldosimpath +'/' + ioname.replace('<','').replace('>','').replace('.','_')\
                    + '_' + self.rndpart +'.txt')
        return self._file
    @file.setter
    def file(self,val):
        self._file=val
        return self._file

    # Overloading ionames property to contain a list
    @property
    def ionames(self):
        if isinstance(self._ionames,str):
            self._ionames = [self._ionames]
        return self._ionames
    @ionames.setter
    def ionames(self,val):
        self._ionames=val
        return self._ionames

    # Overloading the remove functionality to remove tmp files
    def remove(self):
        if self.preserve:
            self.print_log(type='I', msg='Preserving files for %s.' % self.name)
        else:
            try:
                self.print_log(type='I',msg='Removing files for %s.' % self.name)
                for f in self.file:
                    if os.path.exists(f):
                        os.remove(f)
            except:
                self.print_log(type='W',msg='Failed while removing files for %s.' % self.name)

    # Overloaded write from thesdk.iofile
    def write(self,**kwargs):
        if self.iotype == 'event':
            try:
                data = self.Data
                for i in range(len(self.file)):
                    np.savetxt(self.file[i],data[:,[2*i,2*i+1]],delimiter=',')
                    self.print_log(type='I',msg='Writing input file: %s.' % self.file[i])
            except:
                self.print_log(type='E',msg='Failed while writing files for %s.' % self.name)
        else:
            pass

    # Overloaded read from thesdk.iofile
    def read(self,**kwargs):
        for i in range(len(self.file)):
            try:
                if self.iotype=='event':
                    arr = genfromtxt(self.file[i],delimiter=' ',skip_header=2)
                    if self.Data is None: 
                        self.Data = np.array(arr)
                    else:
                        self.Data = np.hstack((self.Data,np.array(arr)))
                elif self.iotype=='time':
                    nodematch=re.compile(r"%s" % self.ionames[i].upper())
                    with open(self.file[i]) as infile:
                        wholefile=infile.readlines()
                        arr = []
                        for line in wholefile:
                            if nodematch.search(line) != None:
                                arr.append(float(line.split()[-1]))
                        nparr = np.array(arr).reshape(-1,1)
                        if self.Data is None: 
                            self.Data = nparr
                        else:
                            if len(self.Data[:,-1]) > len(nparr):
                                # Old max length is bigger -> padding new array
                                nans = np.empty(self.Data[:,-1].shape).reshape(-1,1)
                                nans.fill(np.nan)
                                nans[:nparr.shape[0],:nparr.shape[1]] = nparr
                                nparr = nans
                            elif len(self.Data[:,-1]) < len(nparr):
                                # Old max length is smaller -> padding old array
                                nans = np.empty((nparr.shape[0],self.Data.shape[1]))
                                nans.fill(np.nan)
                                nans[:self.Data.shape[0],:self.Data.shape[1]] = self.Data
                                self.Data = nans
                            self.Data = np.hstack((self.Data,nparr))
                    infile.close()
                elif self.iotype=='sample':
                    nodematch=re.compile(r"%s" % self.ionames[i].upper())
                    with open(self.file[i]) as infile:
                        wholefile=infile.readlines()
                        maxsamp = -1
                        outbus = {}
                        for line in wholefile:
                            if nodematch.search(line) != None:
                                tokens = re.findall(r"[\w']+",line)
                                bitidx = tokens[2]
                                sampidx = tokens[3]
                                if int(sampidx) > maxsamp:
                                    maxsamp = int(sampidx)
                                bitval = line.split()[-1]
                                # TODO: Rounding to bits is done here (might need to go elsewhere)
                                # Also, not all sampled signals need to be output as bits necessarily
                                if float(bitval) >= self.vth:
                                    bitval = '1'
                                else:
                                    bitval = '0'
                                if bitidx in outbus.keys():
                                    outbus[bitidx].append(bitval)
                                else:
                                    outbus.update({bitidx:[bitval]})
                        maxbit = max(map(int,outbus.keys()))
                        minbit = min(map(int,outbus.keys()))
                        if self.big_endian:
                            bitrange = range(maxbit,minbit-1,-1)
                            self.print_log(type='I',msg='Reading %s<%d:%d> from file to %s.'%(self.ionames[i].upper(),minbit,maxbit,self.name))
                        else:
                            bitrange = range(minbit,maxbit+1,1)
                            self.print_log(type='I',msg='Reading %s<%d:%d> from file to %s.'%(self.ionames[i].upper(),maxbit,minbit,self.name))
                        arr = []
                        for idx in range(maxsamp):
                            word = ''
                            for key in bitrange:
                                word += outbus[str(key)][idx]
                            arr.append(word)
                        if self.Data is None: 
                            self.Data = np.array(arr).reshape(-1,1)
                        else:
                            self.Data = np.hstack((self.Data,np.array(arr).reshape(-1,1)))
                    infile.close()
                else:
                    self.print_log(type='F',msg='Couldn\'t read file for input type \'%s\'.'%self.iotype)
            except:
                self.print_log(type='F',msg='Failed while reading files for %s.' % self.name)

