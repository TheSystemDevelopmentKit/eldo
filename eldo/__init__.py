"""
=======
ELDO
=======
Simulation interface package for The System Development Kit 

Provides utilities to import eldo modules to python environment and
automatically generate testbenches for the most common simulation cases.

Initially written by Okko Järvinen, 2019
"""
import os
import sys
import subprocess
import shlex
import pdb
import shutil
import time
from datetime import datetime
from abc import * 
from thesdk import *
import numpy as np
from numpy import genfromtxt
import pandas as pd
from functools import reduce
from eldo.testbench import testbench as etb
from eldo.eldo_iofile import eldo_iofile as eldo_iofile
from eldo.eldo_dcsource import eldo_dcsource as eldo_dcsource
from eldo.eldo_simcmd import eldo_simcmd as eldo_simcmd

class eldo(thesdk,metaclass=abc.ABCMeta):
    """Adding this class as a superclass enforces the definitions 
    for vhdl simulations in the subclasses.
    
    """

    #These need to be converted to abstact properties
    def __init__(self):
        pass

    @property
    @abstractmethod
    def _classfile(self):
        return os.path.dirname(os.path.realpath(__file__)) + "/"+__name__

    @property
    def preserve_iofiles(self):  
        """True | False (default)

        If True, do not delete file IO files after 
        simulations. Useful for debugging the file IO"""

        if hasattr(self,'_preserve_iofiles'):
            return self._preserve_iofiles
        else:
            self._preserve_iofiles=False
        return self._preserve_iofiles
    @preserve_iofiles.setter
    def preserve_iofiles(self,value):
        self._preserve_iofiles=value
        
    @property
    def preserve_eldofiles(self):  
        """True | False (default)

        If True, do not delete generated Eldo files (testbench, subcircuit, etc.)
        after simulations. Useful for debugging."""

        if hasattr(self,'_preserve_eldofiles'):
            return self._preserve_eldofiles
        else:
            self._preserve_eldofiles=False
        return self._preserve_eldofiles
    @preserve_eldofiles.setter
    def preserve_eldofiles(self,value):
        self._preserve_eldofiles=value

    @property
    def load_state(self):  
        if hasattr(self,'_load_state'):
            return self._load_state
        else:
            self._load_state=''
        return self._load_state
    @load_state.setter
    def load_state(self,value):
        self._load_state=value

    @property
    def runname(self):
        if hasattr(self,'_runname'):
            return self._runname
        else:
            self._runname='%s_%s' % \
                    (datetime.now().strftime('%Y%m%d%H%M%S'),os.path.basename(tempfile.mkstemp()[1]))
        return self._runname
    @runname.setter
    def runname(self,value):
        self._runname=value

    @property
    def interactive_eldo(self):
        """ True | False (default)
        
        Launch simulator in local machine with GUI."""

        if hasattr(self,'_interactive_eldo'):
            return self._interactive_eldo
        else:
            self._interactive_eldo=False
        return self._interactive_eldo
    @interactive_eldo.setter
    def interactive_eldo(self,value):
        self._interactive_eldo=value

    @property
    def nproc(self):
        if hasattr(self,'_nproc'):
            return self._nproc
        else:
            self._nproc=False
        return self._nproc
    @nproc.setter
    def nproc(self,value):
        self._nproc=value

    @property
    def iofile_bundle(self):
        """ 
        Property of type thesdk.Bundle.
        This property utilises eldo_iofile class to maintain list of IO-files
        that  are automatically assigned as arguments to eldocmd.
        when eldo.eldo_iofile.eldo_iofile(name='<filename>,...) is used to define an IO-file, created file object is automatically
        appended to this Bundle property as a member. Accessible with self.iofile_bundle.Members['<filename>']
        """
        if not hasattr(self,'_iofile_bundle'):
            self._iofile_bundle=Bundle()
        return self._iofile_bundle
    @iofile_bundle.setter
    def iofile_bundle(self,value):
        self._iofile_bundle=value
    @iofile_bundle.deleter
    def iofile_bundle(self):
        for name, val in self.iofile_bundle.Members.items():
            if val.preserve:
                for f in val.file:
                    self.print_log(type="I", msg="Preserving file %s." %(f))
            else:
                val.remove()
        if (not self.preserve_iofiles) and self.interactive_eldo:
            simpathname = self.eldosimpath
            try:
                shutil.rmtree(simpathname)
                self.print_log(type='I',msg='Removing %s.' % simpathname)
            except:
                self.print_log(type='W',msg='Could not remove %s.' % simpathname)
        #self._iofile_bundle=None

    @property
    def dcsource_bundle(self):
        if not hasattr(self,'_dcsource_bundle'):
            self._dcsource_bundle=Bundle()
        return self._dcsource_bundle
    @dcsource_bundle.setter
    def dcsource_bundle(self,value):
        self._dcsource_bundle=value
    @dcsource_bundle.deleter
    def dcsource_bundle(self):
        for name, val in self.dcsource_bundle.Members.items():
            val.remove()

    @property
    def simcmd_bundle(self):
        if not hasattr(self,'_simcmd_bundle'):
            self._simcmd_bundle=Bundle()
        return self._simcmd_bundle
    @simcmd_bundle.setter
    def simcmd_bundle(self,value):
        self._simcmd_bundle=value
    @simcmd_bundle.deleter
    def simcmd_bundle(self):
        for name, val in self.simcmd_bundle.Members.items():
            val.remove()

    @property 
    def eldo_submission(self):
        """
        Defines eldo submioddion prefix from thesdk.GLOBALS['LSFSUBMISSION']

        Usually something like 'bsub -K'
        """
        if not hasattr(self, '_eldo_submission'):
            try:
                self._eldo_submission=thesdk.GLOBALS['LSFSUBMISSION']+' '
            except:
                self.print_log(type='W',msg='Variable thesdk.GLOBALS incorrectly defined. _eldo_submission defaults to empty string and simulation is ran in localhost.')
                self._eldo_submission=''

        if hasattr(self,'_interactive_eldo'):
            return self._eldo_submission

        return self._eldo_submission

    @property
    def eldoparameters(self): 
        if not hasattr(self, '_eldoparameters'):
            self._eldoparameters =dict([])
        return self._eldoparameters
    @eldoparameters.setter
    def eldoparameters(self,value): 
            self._eldoparameters = value
    @eldoparameters.deleter
    def eldoparameters(self): 
            self._eldoparameters = None

    @property
    def eldocorner(self): 
        if not hasattr(self, '_eldocorner'):
            self._eldocorner =dict([])
        return self._eldocorner
    @eldocorner.setter
    def eldocorner(self,value): 
            self._eldocorner = value
    @eldocorner.deleter
    def eldocorner(self): 
            self._eldocorner = None

    @property
    def eldooptions(self): 
        if not hasattr(self, '_eldooptions'):
            self._eldooptions =dict([])
        return self._eldooptions
    @eldooptions.setter
    def eldooptions(self,value): 
            self._eldooptions = value
    @eldooptions.deleter
    def eldooptions(self): 
            self._eldooptions = None

    @property
    def eldoiofiles(self): 
        if not hasattr(self, '_eldoiofiles'):
            self._eldoiofiles =dict([])
        return self._eldoiofiles
    @eldoiofiles.setter
    def eldoiofiles(self,value): 
            self._eldoiofiles = value
    @eldoiofiles.deleter
    def eldoiofiles(self): 
            self._eldoiofiles = None

    @property
    def eldoplotextras(self): 
        if not hasattr(self, '_eldoplotextras'):
            self._eldoplotextras = []
        return self._eldoplotextras
    @eldoplotextras.setter
    def eldoplotextras(self,value): 
            self._eldoplotextras = value
    @eldoplotextras.deleter
    def eldoplotextras(self): 
            self._eldoplotextras = None

    @property
    def eldomisc(self): 
        if not hasattr(self, '_eldomisc'):
            self._eldomisc = []
        return self._eldomisc
    @eldomisc.setter
    def eldomisc(self,value): 
            self._eldomisc = value
    @eldomisc.deleter
    def eldomisc(self): 
            self._eldomisc = None

    @property
    def name(self):
        if not hasattr(self, '_name'):
            self._name=os.path.splitext(os.path.basename(self._classfile))[0]
        return self._name
    #No setter, no deleter.

    @property
    def entitypath(self):
        if not hasattr(self, '_entitypath'):
            self._entitypath= os.path.dirname(os.path.dirname(self._classfile))
        return self._entitypath
    #No setter, no deleter.

    @property
    def eldosrcpath(self):
        self._eldosrcpath  =  self.entitypath + '/eldo'
        try:
            if not (os.path.exists(self._eldosrcpath)):
                os.makedirs(self._eldosrcpath)
                self.print_log(type='I',msg='Creating %s.' % self._eldosrcpath)
        except:
            self.print_log(type='E',msg='Failed to create %s.' % self._eldosrcpath)
        return self._eldosrcpath
    #No setter, no deleter.

    @property
    def eldosrc(self):
        if not hasattr(self, '_eldosrc'):
            self._eldosrc=self.eldosrcpath + '/' + self.name + '.cir'
            if not os.path.exists(self._eldosrc):
                self.print_log(type='W',msg='No source circuit found in %s.' % self._eldosrc)
        return self._eldosrc

    @property
    def eldotbsrc(self):
        if not hasattr(self, '_eldotbsrc'):
            if self.interactive_eldo:
                self._eldotbsrc=self.eldosrcpath + '/tb_' + self.name + '.cir'
            else:
                self._eldotbsrc=self.eldosimpath + '/tb_' + self.name + '.cir'
        return self._eldotbsrc

    @property
    def eldowdbsrc(self):
        if not hasattr(self, '_eldowdbsrc'):
            if self.interactive_eldo:
                self._eldowdbsrc=self.eldosrcpath + '/tb_' + self.name + '.wdb'
            else:
                self._eldowdbsrc=self.eldosimpath + '/tb_' + self.name + '.wdb'
        return self._eldowdbsrc

    @property
    def eldochisrc(self):
        if not hasattr(self, '_eldochisrc'):
            if self.interactive_eldo:
                self._eldochisrc=self.eldosrcpath + '/tb_' + self.name + '.chi'
            else:
                self._eldochisrc=self.eldosimpath + '/tb_' + self.name + '.chi'
        return self._eldochisrc

    @property
    def eldosubcktsrc(self):
        if not hasattr(self, '_eldosubcktsrc'):
            if self.interactive_eldo:
                self._eldosubcktsrc=self.eldosrcpath + '/subckt_' + self.name + '.cir'
            else:
                self._eldosubcktsrc=self.eldosimpath + '/subckt_' + self.name + '.cir'
        return self._eldosubcktsrc

    @property
    def eldosimpath(self):
        #self._eldosimpath  = self.entitypath+'/Simulations/eldosim'
        self._eldosimpath = self.entitypath+'/Simulations/eldosim/'+self.runname
        try:
            if not (os.path.exists(self._eldosimpath)):
                os.makedirs(self._eldosimpath)
                self.print_log(type='I',msg='Creating %s.' % self._eldosimpath)
        except:
            self.print_log(type='E',msg='Failed to create %s.' % self._eldosimpath)
        return self._eldosimpath
    @eldosimpath.deleter
    def eldosimpath(self):
        if (not self.interactive_eldo) and (not self.preserve_eldofiles):
            # Removing generated files
            filelist = [
                self.eldochisrc,
                self.eldowdbsrc,
                self.eldotbsrc,
                self.eldosubcktsrc
                ]
            for f in filelist:
                try:
                    if os.path.exists(f):
                        os.remove(f)
                        self.print_log(type='I',msg='Removing %s.' % f)
                except:
                    self.print_log(type='W',msg='Could not remove %s.' % f)
                    pass

            # Cleaning up extra files
            remaining = os.listdir(self.eldosimpath)
            for f in remaining:
                try:
                    fpath = '%s/%s' % (self.eldosimpath,f)
                    if f.startswith('tb_%s' % self.name):
                        os.remove(fpath)
                        self.print_log(type='I',msg='Removing %s.' % fpath)
                except:
                    self.print_log(type='W',msg='Could not remove %s.' % fpath)

            # IO files were also removed -> remove the directory
            if not self.preserve_iofiles:
                # I need to save this here to prevent the directory from being re-created
                simpathname = self._eldosimpath
                try:
                    # This fails now because of .nfs files
                    shutil.rmtree(simpathname)
                    self.print_log(type='I',msg='Removing %s.' % simpathname)
                except:
                    self.print_log(type='W',msg='Could not remove %s.' % simpathname)
        else:
            # Using the private variable here to prevent the re-creation of the dir?
            self.print_log(type='I',msg='Preserving eldo files in %s.' % self._eldosrcpath)


    @property
    def eldocmd(self):
        if self.interactive_eldo:
            ezwave = "-ezwave"
            submission=""
        else:
            ezwave = ""
            submission=self.eldo_submission

        if self.nproc:
            nproc = "-use_proc %d" % self.nproc
        else:
            nproc = ""

        eldosimcmd = "eldo -64b -queue %s %s " % (ezwave,nproc)
        eldotbfile = self.eldotbsrc
        self._eldocmd = submission +\
                        eldosimcmd +\
                        eldotbfile
        return self._eldocmd

    # Just to give the freedom to set this if needed
    @eldocmd.setter
    def eldocmd(self,value):
        self._eldocmd=value
    @eldocmd.deleter
    def eldocmd(self):
        self._eldocmd=None

    def connect_inputs(self):
        for ioname,io in self.IOS.Members.items():
            if ioname in self.iofile_bundle.Members:
                val=self.iofile_bundle.Members[ioname]
                # File type inputs are driven by the file.Data, not the input field
                if not isinstance(self.IOS.Members[val.name].Data,eldo_iofile) \
                        and val.dir is 'in':
                    # Data must be properly shaped
                    self.iofile_bundle.Members[ioname].Data=self.IOS.Members[ioname].Data

    def connect_outputs(self):
        for name,val in self.iofile_bundle.Members.items():
            if val.dir is 'out':
                self.IOS.Members[name].Data=self.iofile_bundle.Members[name].Data

    # This writes infiles
    def write_infile(self):
        for name, val in self.iofile_bundle.Members.items():
            if val.dir.lower()=='in' or val.dir.lower()=='input':
                self.iofile_bundle.Members[name].write()

    # Reading output files
    def read_outfile(self):
        for name, val in self.iofile_bundle.Members.items():
            if val.dir.lower()=='out' or val.dir.lower()=='output':
                 self.iofile_bundle.Members[name].read()
    
    def execute_eldo_sim(self):
        # Call eldo here
        self.print_log(type='I', msg="Running external command %s\n" %(self.eldocmd) )
    
        # This is some experimental stuff
        count = 0
        while True:
            status = int(os.system(self.eldocmd)/256)
            # Status code 9 seems to result from failed licensing in LSF runs
            # Let's not try to restart if in interactive mode
            if status != 9 or count == 10 or self.interactive_eldo:
                break
            else:
                count += 1
                self.print_log(type='W',msg='License error, trying again... (%d/10)' % count)
                time.sleep(5)
        if status > 0:
            self.print_log(type='F',msg='Eldo encountered an error (%d).' % status)

    def extract_powers(self):
        self.powers = {}
        self.currents = {}
        try:
            currentmatch = re.compile(r"CURRENT_")
            powermatch = re.compile(r"POWER_")
            with open(self.eldochisrc) as infile:
                chifile = infile.readlines()
                for line in chifile:
                    if currentmatch.search(line):
                        words = line.split()
                        sourcename = words[1].replace('CURRENT_','')
                        extval = float(words[3])
                        self.currents[sourcename] = extval
                        self.print_log(type='I',msg='%s\tcurrent = %g\tA'%(sourcename,extval))
                    elif powermatch.search(line):
                        words = line.split()
                        sourcename = words[1].replace('POWER_','')
                        extval = float(words[3])
                        self.powers[sourcename] = extval
                        self.print_log(type='I',msg='%s\tpower   = %g\tW'%(sourcename,extval))
            if len(self.currents.keys()) > 0:
                self.print_log(type='I',msg='Total\tcurrent = %g\tA'%(sum(self.currents.values())))
                self.print_log(type='I',msg='Total\tpower   = %g\tW'%(sum(self.powers.values())))
        except:
            self.print_log(type='W',msg='Something went wrong while extracting power consumptions.')

    def run_eldo(self):
        if self.load_state == '': 
            # Normal execution of full simulation
            self.tb = etb(self)
            self.tb.iofiles = self.iofile_bundle
            self.tb.dcsources = self.dcsource_bundle
            self.tb.simcmds = self.simcmd_bundle
            self.connect_inputs()
            self.tb.generate_contents()
            self.tb.export_subckt(force=True)
            self.tb.export(force=True)
            self.write_infile()
            self.execute_eldo_sim()
            self.extract_powers()
            self.read_outfile()
            self.connect_outputs()

            # Calling deleter of iofiles
            del self.iofile_bundle
            # And eldo files (tb, subcircuit, wdb)
            del self.eldosimpath
        else:
            #Loading previous simulation results and not simulating again
            try:
                self.runname = self.load_state
                simpath = self.entitypath+'/Simulations/eldosim/'+self.runname
                if not (os.path.exists(simpath)):
                    self.print_log(type='E',msg='Existing results not found in %s.' % simpath)
                    existing = os.listdir(self.entitypath+'/Simulations/eldosim/')
                    self.print_log(type='I',msg='Found results:')
                    for f in existing:
                        self.print_log(type='I',msg='%s' % f)
                else:
                    self.print_log(type='I',msg='Loading results from %s.' % simpath)
                    #self.tb = etb(self)
                    #self.tb.iofiles = self.iofile_bundle
                    #self.tb.dcsources = self.dcsource_bundle
                    #self.tb.simcmds = self.simcmd_bundle
                    self.connect_inputs()
                    #self.tb.generate_contents()
                    #self.tb.export_subckt(force=True)
                    #self.tb.export(force=True)
                    #self.write_infile()
                    #self.execute_eldo_sim()
                    #self.extract_powers()
                    self.read_outfile()
                    self.connect_outputs()
            except:
                self.print_log(type='F',msg='Failed while loading results from %s.' % self._eldosimpath)

