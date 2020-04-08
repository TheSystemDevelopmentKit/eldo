# Written by Marko Kosunen 20190108
import os
import sys
import subprocess
import shlex
from abc import * 
from thesdk import *
from eldo import *
from eldo.module import eldo_module
import pdb

import numpy as np
import pandas as pd
from functools import reduce
import textwrap
from datetime import datetime
## Some guidelines:
## DUT is parsed from the eldo file.
## Simparams are parsed to header from the parent
## All io's are read from a file? (Is this good)
## Code injection should be possible
## at least between blocks
## Default structure during initialization?

# Utilizes logging method from thesdk
# Is extendsd eldo module with some additional properties
class testbench(eldo_module):
    @property
    def _classfile(self):
        return os.path.dirname(os.path.realpath(__file__)) + "/"+__name__

    def __init__(self, parent=None, **kwargs):
        if parent==None:
            self.print_log(type='F', msg="Parent of Eldo testbench not given")
        else:
            self.parent=parent
        try:  
            if self.parent.interactive_eldo:
                self._file=self.parent.eldosrcpath + '/tb_' + self.parent.name + '.cir'
                self._subcktfile=self.parent.eldosrcpath + '/subckt_' + self.parent.name + '.cir'
            else:
                self._file=self.parent.eldosimpath + '/tb_' + self.parent.name + '.cir'
                self._subcktfile=self.parent.eldosimpath + '/subckt_' + self.parent.name + '.cir'
            self._dutfile=self.parent.eldosrcpath + '/' + self.parent.name + '.cir'
            self._trantime=0
        except:
            self.print_log(type='F', msg="Eldo Testbench file definition failed")
        
        #The methods for these are derived from eldo_module
        self._name=''
        self.iofiles=Bundle()
        self.dcsources=Bundle()
        self.simcmds=Bundle()
        
    @property
    def file(self):
        if not hasattr(self,'_file'):
            self._file=None
        return self._file

    @file.setter
    def file(self,value):
            self._file=value

    @property
    def dut_instance(self):
        if not hasattr(self,'_dut_instance'):
            self._dut_instance=eldo_module(**{'file':self._dutfile})
        return self._dut_instance

    @dut_instance.setter
    def dut_instance(self,value):
        self._dut_instance=value

    # Generating eldo dcsources string
    @property
    def dcsourcestr(self):
        if not hasattr(self,'_dcsourcestr'):
            self._dcsourcestr = "*** DC sources\n"
            for name, val in self.dcsources.Members.items():
                self._dcsourcestr += "%s%s %s %s %g %s\n" % \
                        (val.sourcetype.upper(),val.name.lower(),val.pos,val.neg,val.value, \
                        'NONOISE' if not val.noise else '')
                # If the DC source is a supply, the power consumption is extracted for it automatically
                if val.extract:
                    supply = "%s%s"%(val.sourcetype.upper(),val.name.lower())
                    self._dcsourcestr += ".defwave p_%s=v(%s)*i(%s)\n" % \
                            (supply.lower(),supply,supply)
                    self._dcsourcestr += ".extract label=current_%s abs(average(i(%s),%s,%s))\n" % \
                            (supply.lower(),supply,val.ext_start,val.ext_stop)
                    self._dcsourcestr += ".extract label=power_%s abs(average(w(p_%s),%s,%s))\n" % \
                            (supply.lower(),supply.lower(),val.ext_start,val.ext_stop)
        return self._dcsourcestr
    @dcsourcestr.setter
    def dcsourcestr(self,value):
        self._dcsourcestr=value
    @dcsourcestr.deleter
    def dcsourcestr(self,value):
        self._dcsourcestr=None

    # Generating eldo inputsignals string
    @property
    def inputsignals(self):
        if not hasattr(self,'_inputsignals'):
            self._inputsignals = "*** Input signals\n"
            for name, val in self.iofiles.Members.items():
                # Input file becomes a source
                if val.dir.lower()=='in' or val.dir.lower()=='input':
                    if val.iotype.lower()=='event':
                        for i in range(len(val.ionames)):
                            # Finding the max time instant
                            maxtime = val.Data[-1,0]
                            if float(self._trantime) < float(maxtime):
                                self._trantime = maxtime
                            # Adding the source
                            self._inputsignals += "%s%s %s 0 pwl(file=\"%s\")\n" % \
                                    (val.sourcetype.upper(),val.ionames[i].lower(),val.ionames[i].upper(),val.file[i])
                    elif val.iotype.lower()=='sample':
                        for i in range(len(val.ionames)):
                            pattstr = ''
                            for d in val.Data[:,i]:
                                pattstr += '%s ' % str(d)
                            if float(self._trantime) < len(val.Data)/val.rs:
                                self._trantime = len(val.Data)/val.rs
                            # Checking if the given bus is actually a 1-bit signal
                            if ('<' not in val.ionames[i]) and ('>' not in val.ionames[i]) and len(str(val.Data[0,i])) == 1:
                                busname = '%s_BUS' % val.ionames[i]
                                self._inputsignals += '.setbus %s %s\n' % (busname,val.ionames[i])
                            else:
                                busname = val.ionames[i]
                            # Adding the source
                            self._inputsignals += ".sigbus %s vhi=%s vlo=%s tfall=%s trise=%s thold=%s tdelay=%s base=%s PATTERN %s\n" % \
                                    (busname,str(val.vhi),str(val.vlo),str(val.tfall),str(val.trise),str(1/val.rs),val.after,'bin',pattstr)
                    else:
                        print_log(type='F',msg='Input type \'%s\' undefined.' % val.iotype)

            if self._trantime == 0:
                self._trantime = "simtime"
        return self._inputsignals
    @inputsignals.setter
    def inputsignals(self,value):
        self._inputsignals=value
    @inputsignals.deleter
    def inputsignals(self,value):
        self._inputsignals=None

    # Generating eldo simcmds string
    @property
    def simcmdstr(self):
        if not hasattr(self,'_simcmdstr'):
            self._simcmdstr = "*** Simulation commands\n"
            for simtype, val in self.simcmds.Members.items():
                if str(simtype).lower() == 'tran':
                    self._simcmdstr += '.%s %s %s %s\n' % \
                            (simtype,str(val.tprint),str(val.tstop) if val.tstop is not None else str(self._trantime+2e-9) \
                            ,'UIC' if val.uic else '')
                    if val.noise:
                        self._simcmdstr += '.noisetran fmin=%s fmax=%s nbrun=1 NONOM %s\n' % \
                                (str(val.fmin),str(val.fmax),'seed=%d'%(val.seed) if val.seed is not None else '')
                else:
                    self.print_log(type='E',msg='Simulation type \'%s\' not yet implemented.' % str(simtype))
        return self._simcmdstr
    @simcmdstr.setter
    def simcmdstr(self,value):
        self._simcmdstr=value
    @simcmdstr.deleter
    def simcmdstr(self,value):
        self._simcmdstr=None

    # Generating eldo plot and print commands
    @property
    def plotcmd(self):
        if not hasattr(self,'_plotcmd'):
            # TODO: This manual plot should be moved elsewhere
            if len(self.parent.eldoplotextras) > 0:
                self._plotcmd = "*** Manually probed signals\n"
                self._plotcmd += ".plot "
                for i in self.parent.eldoplotextras:
                    self._plotcmd += i + " "
                self._plotcmd += "\n\n"
            self._plotcmd += "*** Output signals\n"
            for name, val in self.iofiles.Members.items():
                # Output iofile becomes an extract command
                if val.dir.lower()=='out' or val.dir.lower()=='output':
                    if val.iotype=='event':
                        for i in range(len(val.ionames)):
                            self._plotcmd += ".printfile %s(%s) file=\"%s\"\n" % \
                                    (val.sourcetype,val.ionames[i].upper(),val.file[i])
                    elif val.iotype=='sample':
                        for i in range(len(val.ionames)):
                            # Checking the given trigger(s)
                            if isinstance(val.trigger,list):
                                if len(val.trigger) == len(val.ionames):
                                    trig = val.trigger[i]
                                else:
                                    trig = val.trigger[0]
                                    self.print_log(type='W',msg='%d triggers given for %d ionames. Using the first trigger for all ionames.' % (len(val.trigger),len(val.ionames)))
                            else:
                                trig = val.trigger
                            # Checking the polarity of the triggers (for now every trigger has to have same polarity)
                            vthstr = ',%s' % str(val.vth)
                            afterstr = ',%g' % float(val.after)
                            beforestr = ',end'
                            if val.edgetype.lower()=='falling':
                                polarity = 'xdown'
                            elif val.edgetype.lower()=='both':
                                # Syntax for tcross is a bit different
                                polarity = 'tcross'
                                vthstr = ',vth=%s' % str(val.vth)
                                afterstr = ',after=%g' % float(val.after)
                                beforestr = ',before=end'
                            else:
                                polarity = 'xup'
                            self._plotcmd += ".extract file=\"%s\" vect label=%s yval(v(%s<*>),%s(v(%s)%s%s%s))\n" % (val.file[i],val.ionames[i],val.ionames[i].upper(),polarity,trig,vthstr,afterstr,beforestr)
                    elif val.iotype=='time':
                        for i in range(len(val.ionames)):
                            vthstr = ',%s' % str(val.vth)
                            if val.edgetype.lower()=='falling':
                                edge = 'xdown'
                            elif val.edgetype.lower()=='both':
                                edge = 'tcross'
                                vthstr = ',vth=%s' % str(val.vth)
                            elif val.edgetype.lower()=='risetime':
                                edge = 'trise'
                                vthstr = ''
                            elif val.edgetype.lower()=='falltime':
                                edge = 'tfall'
                                vthstr = ''
                            else:
                                edge = 'xup'
                            self._plotcmd += ".extract file=\"%s\" vect label=%s %s(v(%s)%s)\n" % (val.file[i],val.ionames[i],edge,val.ionames[i].upper(),vthstr)
                    else:
                        self.print_log(type='W',msg='Output filetype incorrectly defined.')
        return self._plotcmd
    @plotcmd.setter
    def plotcmd(self,value):
        self._plotcmd=value
    @plotcmd.deleter
    def plotcmd(self,value):
        self._plotcmd=None


    def export(self,**kwargs):
        if not os.path.isfile(self.file):
            self.print_log(type='I',msg='Exporting eldo testbench to %s.' %(self.file))
            with open(self.file, "w") as module_file:
                module_file.write(self.contents)

        elif os.path.isfile(self.file) and not kwargs.get('force'):
            self.print_log(type='F', msg=('Export target file %s exists.\n Force overwrite with force=True.' %(self.file)))

        elif kwargs.get('force'):
            self.print_log(type='I',msg='Forcing overwrite of eldo testbench to %s.' %(self.file))
            with open(self.file, "w") as module_file:
                module_file.write(self.contents)

    def export_subckt(self,**kwargs):
        if self._postlayout:
            return
        if not os.path.isfile(self.parent.eldosubcktsrc):
            self.print_log(type='I',msg='Exporting eldo subcircuit to %s.' %(self.parent.eldosubcktsrc))
            with open(self.parent.eldosubcktsrc, "w") as module_file:
                module_file.write(self.subckt)

        elif os.path.isfile(self.parent.eldosubcktsrc) and not kwargs.get('force'):
            self.print_log(type='F', msg=('Export target file %s exists.\n Force overwrite with force=True.' %(self.parent.eldosubcktsrc)))

        elif kwargs.get('force'):
            self.print_log(type='I',msg='Forcing overwrite of eldo subcircuit to %s.' %(self.parent.eldosubcktsrc))
            with open(self.parent.eldosubcktsrc, "w") as module_file:
                module_file.write(self.subckt)

    def generate_contents(self):
        date_object = datetime.now()
        headertxt = "********************************************\n" +\
                    "****** Testbench for %s\n" % self.parent.name +\
                    "****** Generated %s \n" % date_object +\
                    "********************************************\n"
        libcmd = self.libcmd
        includecmd = self.includecmd
        options = self.options
        params = self.parameters
        subinst = self.subinst
        dcsourcestr = self.dcsourcestr
        inputsignals = self.inputsignals
        misccmd = self.misccmd
        simcmd = self.simcmdstr
        plotcmd = self.plotcmd
        self.contents = headertxt + "\n" +\
                        libcmd + "\n" +\
                        includecmd + "\n" +\
                        options + "\n" +\
                        params + "\n" +\
                        subinst + "\n\n" +\
                        misccmd + "\n" +\
                        dcsourcestr + "\n" +\
                        inputsignals + "\n" +\
                        simcmd + "\n" +\
                        plotcmd + "\n" +\
                        ".end"

if __name__=="__main__":
    pass
