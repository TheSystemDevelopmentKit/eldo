# Written by Marko Kosunen 20190109
# marko.kosunen@aalto.fi
import os
import pdb
from thesdk import *
from eldo import *
from copy import deepcopy

class eldo_module(thesdk):
    @property
    def _classfile(self):
        return os.path.dirname(os.path.realpath(__file__)) + "/"+__name__

    def __init__(self, **kwargs):
        # No need to propertize these yet
        self.file=kwargs.get('file','')
        self._name=kwargs.get('name','')
        self._instname=kwargs.get('instname',self.name)
        if not self.file and not self._name:
            self.print_log(type='F', msg='Either name or file must be defined')
    
    #Name derived from the file
    @property
    def name(self):
        if not self._name:
            self._name=os.path.splitext(os.path.basename(self.file))[0]
        return self._name

    @property
    def instname(self):
        if not hasattr(self,'_instname'):
            self._instname=self.name+'_DUT'
        return self._instname
    @instname.setter
    def instname(self,value):
            self._instname=value

    @property
    def contents(self):
        if not hasattr(self,'_contents'):
            self._contents=""
        return self._contents
    @contents.setter
    def contents(self,value):
        self._contents=value
    @contents.deleter
    def contents(self,value):
        self._contents=None

    # Parsing the subcircuit definition from input netlist
    @property
    def subckt(self):
        if not hasattr(self,'_subckt'):
            cellnamematch=re.compile(r"\*\*\* Design cell name:")
            startmatch=re.compile(r"\.SUBCKT")
            endmatch=re.compile(r"\.ENDS")
            cellname = ""
            self._subckt="*** Subcircuit definitions\n\n"
            # Extract the module definition
            if os.path.isfile(self._dutfile):
                with open(self._dutfile) as infile:
                    wholefile=infile.readlines()
                    startfound=False
                    endfound=False
                    for line in wholefile:
                        if not startfound and cellnamematch.search(line) != None:
                            words = line.split()
                            cellname = words[-1]
                        if not startfound and startmatch.search(line) != None and cellname != "":
                            startfound=True
                            words = line.split()
                            if words[1].lower() == cellname.lower():
                                self._subckt+="\n*** Subcircuit definition for %s module\n" % self.parent.name
                                words[1] = self.parent.name.upper()
                                line = ' '.join(words) + "\n"
                        if startfound:
                            self._subckt=self._subckt+line
                        if startfound and endmatch.search(line) != None:
                            startfound=False
            else:
                self.print_log(type='W',msg='File %s not found.' % self._dutfile)
        return self._subckt
    @subckt.setter
    def subckt(self,value):
        self._subckt=value
    @subckt.deleter
    def subckt(self,value):
        self._subckt=None

    # Generating subcircuit instance from the definition
    @property
    def subinst(self):
        if not hasattr(self,'_subinst'):
            startmatch=re.compile(r"\.SUBCKT %s" % self.parent.name.upper())
            subckt = self.subckt.split('\n')
            if len(subckt) <= 3:
                self.print_log(type='W',msg='No subcircuit found.')
                self._subinst = "*** Empty subcircuit\n"
            else:
                self._subinst = "*** Subcircuit instance\n"
                startfound = False
                endfound = False
                # Extract the module definition
                for line in subckt:
                    if startmatch.search(line) != None:
                        startfound = True
                    elif startfound and len(line) > 0 and line[0] != "+":
                        endfound = True
                        startfound = False
                    if startfound and not endfound:
                        words = line.split(" ")
                        if words[0].lower() == ".subckt":
                            words[0] = "X%s" % self.parent.name.lower()
                            words.pop(1)
                            line = ' '.join(words)
                        self._subinst += line + "\n"
                self._subinst += "+" + self.parent.name.upper()
        return self._subinst
    @subinst.setter
    def subinst(self,value):
        self._subinst=value
    @subinst.deleter
    def subinst(self,value):
        self._subinst=None

    # Generating eldo options string
    @property
    def options(self):
        if not hasattr(self,'_options'):
            self._options = "*** Options\n"
            for optname,optval in self.parent.eldooptions.items():
                if optval != "":
                    self._options += ".option " + optname + "=" + optval + "\n"
                else:
                    self._options += ".option " + optname + "\n"
        return self._options
    @options.setter
    def options(self,value):
        self._options=value
    @options.deleter
    def options(self,value):
        self._options=None

    # Generating eldo parameters string
    @property
    def parameters(self):
        if not hasattr(self,'_parameters'):
            self._parameters = "*** Parameters\n"
            for parname,parval in self.parent.eldoparameters.items():
                self._parameters += ".param " + parname + "=" + str(parval) + "\n"
        return self._parameters
    @parameters.setter
    def parameters(self,value):
        self._parameters=value
    @parameters.deleter
    def parameters(self,value):
        self._parameters=None

    # Generating eldo library inclusion string
    @property
    def libcmd(self):
        if not hasattr(self,'_libcmd'):
            libfile = ""
            corner = "top_tt"
            temp = "27"
            for optname,optval in self.parent.eldocorner.items():
                if optname == "temp":
                    temp = optval
                if optname == "corner":
                    corner = optval
            try:
                libfile = thesdk.GLOBALS['ELDOLIBFILE']
                self._libcmd = "*** Eldo device models\n"
                self._libcmd += ".lib " + libfile + " " + corner + "\n"
            except:
                self.print_log(type='W',msg='Global TheSDK variable ELDOLIBPATH not set.')
                self._libcmd = "*** Eldo device models (undefined)\n"
                self._libcmd += "*.lib " + libfile + " " + corner + "\n"
            self._libcmd += ".temp " + temp + "\n"
        return self._libcmd
    @libcmd.setter
    def libcmd(self,value):
        self._libcmd=value
    @libcmd.deleter
    def libcmd(self,value):
        self._libcmd=None

    # Generating eldo device model string
    @property
    def corner(self):
        if not hasattr(self,'_corner'):
            self._corner = "*** Device models\n"
            for optname,optval in self.parent.eldocorner.items():
                if optname == "temp":
                    self._corner += "." + optname + " " + optval + "\n"
                if optname == "process":
                    self._process = optval
        return self._corner
    @corner.setter
    def corner(self,value):
        self._corner=value
    @corner.deleter
    def corner(self,value):
        self._corner=None

    # Generating eldo design inclusion string
    @property
    def includecmd(self):
        if not hasattr(self,'_includecmd'):
            self._includecmd = "*** Subcircuit file\n"
            self._includecmd += ".include %s\n" % self._subcktfile
        return self._includecmd
    @includecmd.setter
    def includecmd(self,value):
        self._includecmd=value
    @includecmd.deleter
    def includecmd(self,value):
        self._includecmd=None

    @property
    def misccmd(self):
        if not hasattr(self,'_misccmd'):
            self._misccmd="*** Manual commands\n"
            mcmd = self.parent.eldomisc
            for cmd in mcmd:
                self._misccmd += cmd + "\n"
        return self._misccmd
    @misccmd.setter
    def misccmd(self,value):
        self._misccmd=value
    @misccmd.deleter
    def misccmd(self,value):
        self._misccmd=None

    @property
    def definition(self):
        if not hasattr(self,'_definition'):
            self._definition=self.contents
        return self._definition

    # Instance is defined through the io_signals
    # Therefore it is always regenerated
    @property
    def instance(self):
        self._instance=""
        return self._instance

if __name__=="__main__":
    pass
