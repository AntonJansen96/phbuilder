#!/bin/python3

# IMPORT MODULES
import os, numpy as np, matplotlib.pyplot as plt
from phbuilder.structure import Structure
from data import biophys, nury2010, fritsch2011, lev2017, nemecz2017

def loadxvg(fname, col=[0, 1], dt=1, b=0):
    """
    This function loads an .xvg file into a list of lists.
    fname: file name (e.g. 'rmsd.xvg')
    col: which columns to load
    dt: skip every dt steps
    b: start from ... in first column
    """
    count = -1
    data = [ [] for _ in range(len(col)) ]
    for stringLine in open(fname).read().splitlines():
        if stringLine[0] in ['@', '#', '&']:
            continue
        # This is for the dt part.
        count += 1
        if count % dt != 0:
            continue
        
        listLine = stringLine.split()
        # And this is for the b part.
        if b != 0 and float(listLine[col[0]]) < b:
            continue

        for idx in col:
            data[idx].append(float(listLine[col[idx]]))
    return data

class TwoState:
    '''Holds data for a two-state (ASP or GLU) titratable group.'''
    def __init__(self, idx, resname, resid, chain, t, x):
        self.d_idx      = idx
        self.d_fname    = 'cphmd-coord-{}.xvg'.format(idx)
        self.d_resname  = resname
        self.d_resid    = resid
        self.d_chain    = chain
        self.d_t        = t
        self.d_x        = x

class MultiState:
    '''Holds data for a multistate-state (HIS) titratable group.'''
    def __init__(self, idx, resname, resid, chain, t1, t2, t3, x1, x2, x3):
        self.d_idx      = [idx, idx+1, idx+2]
        self.d_fname    = ['cphmd-coord-{}.xvg'.format(idx), 'cphmd-coord-{}.xvg'.format(idx+1), 'cphmd-coord-{}.xvg'.format(idx+2)]
        self.d_resname  = resname
        self.d_resid    = resid
        self.d_chain    = chain
        self.d_t        = [t1, t2, t3]
        self.d_x        = [x1, x2, x3]

class Buffer:
    '''Holds data for the buffer group.'''
    def __init__(self, idx, t, x, count):
        self.d_idx     = idx
        self.d_fname   = 'cphmd-coord-{}.xvg'.format(idx)
        self.d_resname = 'BUF'
        self.d_t       = t
        self.d_x       = x
        self.d_count   = count

class Replica:
    '''Holds data for one replica.'''
    def __init__(self, name, replicaID, twoStateList, multiStateList, buffer):
        self.d_name           = name
        self.d_replicaID      = replicaID
        self.d_twoStateList   = twoStateList
        self.d_multiStateList = multiStateList
        self.d_buffer         = buffer

class ReplicaSet:
    '''Holds data for one set of GLIC replicas (e.g. 4HFI_4).'''
    def __init__(self, name, replicaSet):
        self.d_name        = name
        self.d_replica     = replicaSet

class GLICSims:
    '''Holds the data for all four GLIC replica sets'''
    def __init__(self, folders, replicas, dt, b):

        self.d_replicaSet = []
        for ii in folders:
            os.chdir(ii)

            replicaList = []
            for jj in replicas:
                os.chdir(jj)

                idx = 1
                foundBUF = False
                twoStateList   = []
                multiStateList = []
                for residue in Structure('CA.pdb', 2).d_residues:

                    if residue.d_resname in ['ASPT', 'GLUT']:
                        print('{} : {} Loading {}-{} in chain {}...'.format(ii, jj, residue.d_resname, residue.d_resid, residue.d_chain), end='\r')

                        xvgdata = loadxvg('cphmd-coord-{}.xvg'.format(idx), dt=dt, b=b)

                        twoStateList.append(TwoState(
                            idx, 
                            residue.d_resname, 
                            residue.d_resid,
                            residue.d_chain,
                            xvgdata[0], # time
                            xvgdata[1]  # coordinates
                            ))

                        idx += 1

                    elif residue.d_resname == 'HSPT':
                        print('{} : {} Loading {}-{} in chain {}...'.format(ii, jj, residue.d_resname, residue.d_resid, residue.d_chain), end='\r')

                        xvgdata1 = loadxvg('cphmd-coord-{}.xvg'.format(idx  ), dt=dt, b=b)
                        xvgdata2 = loadxvg('cphmd-coord-{}.xvg'.format(idx+1), dt=dt, b=b)
                        xvgdata3 = loadxvg('cphmd-coord-{}.xvg'.format(idx+2), dt=dt, b=b)

                        multiStateList.append(MultiState(
                            idx,
                            residue.d_resname,
                            residue.d_resid,
                            residue.d_chain,
                            xvgdata1[0],  # file 1 time
                            xvgdata2[0],  # file 2 time
                            xvgdata3[0],  # file 3 time
                            xvgdata1[1],  # file 1 coordinates
                            xvgdata2[1],  # file 2 coordinates
                            xvgdata3[1])) # file 3 coordinates

                        idx += 3

                    elif residue.d_resname == 'BUF' and not foundBUF:
                        xvgdata  = loadxvg('cphmd-coord-{}.xvg'.format(idx), dt=dt)
                        buffer   = Buffer(idx, xvgdata[0], xvgdata[1], count=185)
                        foundBUF = True

                replicaList.append(Replica(ii, int(jj), twoStateList, multiStateList, buffer))

                os.chdir('..')
            
            self.d_replicaSet.append(ReplicaSet(ii, replicaList))

            os.chdir('..')

        # DIRECTORY STRUCTURE
        if not os.path.isdir('lambdaplots'):
            os.mkdir('lambdaplots')

    # FUNCTION FOR MOVING DEPROTONATION
    def movingDeprotonation(self, tList, xList, window):
        Sum = sum(xList[0:window]) # Initialize

        t = tList[window:]
        x = len(range(window, len(xList))) * [0]

        for ii in range(window, len(xList)):
            x[ii - window] = Sum / float(window)
            Sum -= xList[ii - window]
            Sum += xList[ii]

        return t, x

    def histograms(self):
        totalResidues = len(self.d_replicaSet[0].d_replica[0].d_twoStateList)
        chains = 5
        residuesPerChain = int(totalResidues / chains)

        # Outer most loop is over the ReplicaSets (4HFI_4, 4HFI_7, etc.):
        for ii in range(0, len(self.d_replicaSet)):
            # Second loop is over the titratable residues:
            for jj in range(0, residuesPerChain):
                # Set valuesList to zero:
                valuesList = []
                # Third loop is over the four replicas:
                for kk in range(0, len(self.d_replicaSet)): # 4 replicas...
                    # And fourth loop is over the five chains:
                    for ll in range(0, chains): # ...x5 chains = 20 samples

                        # GET THE DATA
                        x = self.d_replicaSet[ii].d_replica[kk].d_twoStateList[jj + residuesPerChain * ll].d_x
                        x = [1.0 - val for val in x] # Mirror in vertical x=0.5 axis

                        # GET HISTOGRAM VALUES
                        values, bins = np.histogram(x, density=True, bins=200, range=(-0.1, 1.1))
                        valuesList.append(values)

                # COMPUTE MEAN AND STANDARD ERROR
                meanList  = len(values) * [0] # 200, to hold mean for each bin
                errorList = len(values) * [0] # 200, to hold erro for each bin

                for kk in range(0, len(values)): # 200

                    # Create list of 20 values
                    temp = [0] * len(valuesList) # 4*5=20
                    for ll in range(0, len(valuesList)): # 4*5=20
                        temp[ll]  = valuesList[ll][kk]

                    meanList[kk]  = np.mean(temp)
                    errorList[kk] = np.std(temp)

                # PLOT MEAN AND SHADED REGION (ERROR)
                A = []; B = []
                for kk in range(0, len(meanList)):
                    A.append(meanList[kk] + errorList[kk])
                    B.append(meanList[kk] - errorList[kk])

                plt.figure(figsize=(8, 6))
                plt.plot(bins[1:], meanList)
                plt.fill_between(bins[1:], A, B, alpha=0.4, color='#1f77b4')

                # MAKE PLOT MORE NICE
                plt.text(x = 1, y = 12.2, s='Proto\n$q = 0$', ha='center', fontsize=12)
                plt.text(x = 0, y = 12.1, s='Deproto\n$q = -1$', ha='center', fontsize=12)
                plt.title(self.d_replicaSet[ii].d_name, fontsize=18)
                plt.axis([-0.1, 1.1, -0.1, 12])
                plt.xlabel(r"$\lambda$-coordinate")
                plt.xticks(ticks=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0], labels=[1.0, 0.8, 0.6, 0.4, 0.2, 0.0]) # because we mirror in vertical x=0.5 axis
                plt.grid()

                group = self.d_replicaSet[0].d_replica[0].d_twoStateList[jj]

                # ADD EXPERIMENTAL DATA FOR PH=4 CASE
                if float(self.d_replicaSet[ii].d_name[5:]) == 4.0:
                    plt.vlines(x=biophys["{0}-{1}".format(group.d_resname, group.d_resid)], ymin=0, ymax=10, color='r', linewidth=4.0, label="biophysics.se/Prevost2012")
                    plt.vlines(x=nury2010["{0}-{1}".format(group.d_resname, group.d_resid)], ymin=0, ymax=8, color='g', linewidth=4.0, label="Nury2010/Cheng2010/Calimet2013")
                    plt.vlines(x=fritsch2011["{0}-{1}".format(group.d_resname, group.d_resid)], ymin=0, ymax=6, color='b', linewidth=4.0, label="Fritsch2011")
                    plt.vlines(x=lev2017["{0}-{1}".format(group.d_resname, group.d_resid)], ymin=0, ymax=4, color='c', linewidth=4.0, label="Lev2017")
                    plt.vlines(x=nemecz2017["{0}-{1}".format(group.d_resname, group.d_resid)], ymin=0, ymax=2, color = 'm', linewidth=4.0, label="Nemecz2017/Hu2018")
                    plt.legend(loc='upper center')

                # SAVE AND CLEAR
                plt.tight_layout()
                plt.savefig('lambdaplots/{}_{:03d}-{}.png'.format(self.d_replicaSet[ii].d_name, group.d_resid, group.d_resname))
                plt.clf(); plt.close()

    def convergence(self, window):
        totalResidues = len(self.d_replicaSet[0].d_replica[0].d_twoStateList)
        chains = 5
        residuesPerChain = int(totalResidues / chains)
        
        # Outer most loop is over the ReplicaSets (4HFI_4, 4HFI_7, etc.):
        for ii in range(0, len(self.d_replicaSet)):
            # Second loop is over the titratable residues:
            for jj in range(0, residuesPerChain):
                # Third loop is over the four replicas:
                for kk in range(0, len(self.d_replicaSet)): # 4 replicas...
                    # And fourth loop is over the five chains:
                    for ll in range(0, chains): # ...x5 chains = 20 samples

                        # GET THE DATA
                        t = self.d_replicaSet[ii].d_replica[kk].d_twoStateList[jj + residuesPerChain * ll].d_t
                        x = self.d_replicaSet[ii].d_replica[kk].d_twoStateList[jj + residuesPerChain * ll].d_x
                        x = [1.0 - val for val in x] # Mirror in vertical x=0.5 axis

                        # PLOT
                        a, b = self.movingDeprotonation(t, x, window)
                        plt.plot(a, b)

                # MAKE PLOT MORE NICE
                plt.title(self.d_replicaSet[ii].d_name, fontsize=18)
                plt.ylim(-0.1, 1.1)
                plt.xlabel("Time (ps)")
                plt.ylabel("Protonation running average")
                plt.ticklabel_format(axis='x', style='sci', scilimits=(0, 3))
                plt.grid()

                group = self.d_replicaSet[0].d_replica[0].d_twoStateList[jj]

                # SAVE AND CLEAR
                plt.tight_layout()
                plt.savefig('lambdaplots/{}_{:03d}-{}_conv.png'.format(self.d_replicaSet[ii].d_name, group.d_resid, group.d_resname))
                plt.clf(); plt.close()

    def histidine(self):
        totalResidues = len(self.d_replicaSet[0].d_replica[0].d_multiStateList)
        chains = 5
        residuesPerChain = int(totalResidues / chains)

        # Outer most loop is over the ReplicaSets (4HFI_4, 4HFI_7, etc.):
        for ii in range(0, len(self.d_replicaSet)):
            # Second loop is over the titratable residues (01, 02, etc.):
            for jj in range(0, residuesPerChain):
                # Start figure here
                plt.figure(figsize=(8, 6))
                # Third loop is over the three lambda groups:
                for kk in [0, 1, 2]:
                    # Set valuesList to zero.
                    valuesList = []
                    # Fourth loop is over the four replicas:
                    for ll in range(0, len(self.d_replicaSet)): # 4 replicas...
                        # And fifth loop is over the five chains:
                        for mm in range(0, chains): # ...x5 chains = 20 samples

                            # GET THE DATA
                            x = self.d_replicaSet[ii].d_replica[kk].d_multiStateList[jj + residuesPerChain * ll].d_x[kk]
                            x = [1.0 - val for val in x] # Mirror in vertical x=0.5 axis

                            # GET HISTOGRAM VALUES, BINS
                            values, bins = np.histogram(x, density=True, bins=200, range=(-0.1, 1.1))
                            valuesList.append(values)

                    # COMPUTE MEAN AND STANDARD ERROR
                    meanList  = len(values) * [0] # 200, to hold mean for each bin
                    errorList = len(values) * [0] # 200, to hold error for each bin

                    for ll in range(0, len(values)): # 200

                        # Create list of 20 values
                        temp = [0] * len(valuesList) # 4*5=20
                        for mm in range(0, len(valuesList)): # 4*5=20
                            temp[mm] = valuesList[mm][ll]

                        meanList[ll] = np.mean(temp)
                        errorList[ll] = np.std(temp)

                    # PLOT MEAN AND SHADED REGION (ERROR)
                    A = []; B = []
                    for ll in range(0, len(meanList)):
                        A.append(meanList[ll] + errorList[ll])
                        B.append(meanList[ll] - errorList[ll])

                    description = ['state 1 (double proto)', 'state 2 (anti)', 'state 3 (syn)']
                    color = ['#1f77b4', '#ff7f0e', '#2ca02c']

                    plt.plot(bins[1:], meanList, color=color[kk], label=description[kk])
                    plt.fill_between(bins[1:], A, B, alpha=0.4, color=color[kk])

                # MAKE PLOT MORE NICE
                plt.title(self.d_replicaSet[ii].d_name, fontsize=18)
                plt.axis([-0.1, 1.1, -0.1, 12])
                plt.xlabel(r"$\lambda$-coordinate")
                plt.xticks(ticks=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0], labels=[1.0, 0.8, 0.6, 0.4, 0.2, 0.0]) # because we mirror in vertical x=0.5 axis
                plt.grid()
                plt.legend(loc='upper center')

                group = self.d_replicaSet[0].d_replica[0].d_multiStateList[jj]

                # SAVE AND CLEAR
                plt.tight_layout()
                plt.savefig('lambdaplots/{}_{:03d}-{}.png'.format(self.d_replicaSet[ii].d_name, group.d_resid, group.d_resname))
                plt.clf(); plt.close()

    def doFinalPlots(self):
        os.chdir('lambdaplots')
        for res in ['127-HSPT', '235-HSPT', '277-HSPT']:
            # CREATE FINAL HISTOGRAMS FOR HISTIDINE
            os.system('convert 6ZGD_7_{}.png 4HFI_7_{}.png +append temp1.png'.format(res, res))
            os.system('convert 6ZGD_4_{}.png 4HFI_4_{}.png +append temp2.png'.format(res, res))
            os.system('convert temp1.png temp2.png -append hist_{}.png'.format(res))
        for res in ['013-ASPT', '014-GLUT', '026-GLUT', '031-ASPT', '032-ASPT', '035-GLUT', '049-ASPT', '055-ASPT', '067-GLUT', '069-GLUT', '075-GLUT', '082-GLUT', '086-ASPT', '088-ASPT', '091-ASPT', '097-ASPT', '104-GLUT', '115-ASPT', '122-ASPT', '136-ASPT', '145-ASPT', '147-GLUT', '153-ASPT', '154-ASPT', '161-ASPT', '163-GLUT', '177-GLUT', '178-ASPT', '181-GLUT', '185-ASPT', '222-GLUT', '243-GLUT', '272-GLUT', '282-GLUT']:
            # CREATE FINAL HISTOGRAMS FOR ASPARTIC AND GLUTAMIC ACID
            os.system('convert 6ZGD_7_{}.png 4HFI_7_{}.png +append temp1.png'.format(res, res))
            os.system('convert 6ZGD_4_{}.png 4HFI_4_{}.png +append temp2.png'.format(res, res))
            os.system('convert temp1.png temp2.png -append hist_{}.png'.format(res))
            # CREATE FINAL CONVERGENCE PLOTS FOR ASPARTIC AND GLUTAMIC ACID
            os.system('convert 6ZGD_7_{}_conv.png 4HFI_7_{}_conv.png +append temp1.png'.format(res, res))
            os.system('convert 6ZGD_4_{}_conv.png 4HFI_4_{}_conv.png +append temp2.png'.format(res, res))
            os.system('convert temp1.png temp2.png -append conv_{}.png'.format(res))
            # MERGE BOTH TO CREATE FINAL PLOTS
            os.system('convert hist_{}.png conv_{}.png +append final_{}.png'.format(res, res, res))