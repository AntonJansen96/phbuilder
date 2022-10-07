#!/bin/python3

import matplotlib.pyplot as plt
import MDAnalysis
import MDAnalysis.analysis.rms
import os, subprocess

# MDANALYSIS DOES NOT KNOW WHAT THE BACKBONE OF ASPT GLUT HSPT ARE!!!!!

def gromacs(command, stdin=[]):
    d_gmxbasepath = '/usr/local/gromacs_constantph'

    # If we do not pass any envvars to subprocess (which happens by default) this will work.
    path_to_gmx = os.path.normpath(d_gmxbasepath + '/' + 'bin/gmx')
    command = "{} {}".format(path_to_gmx, command)

    if stdin:
        xstr = ' << EOF\n'
        for val in stdin:
            xstr += '{}\n'.format(val)
        command += xstr + 'EOF'

    process = subprocess.run(command, shell=True, env={})

    if process.returncode != 0:
        print("Failed to run \"{}\" (exitcode {}).".format(command, process.returncode))

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

def inputOptionHandler(message, options):
    """
    Function for handling user input.
    message: the string you would like to prompt the user.
    options: a list of strings containing the options.
    """

    valids = []
    msgstring = "{}:".format(message)

    for idx in range(0, len(options)):
        msgstring += "\n{}. {}".format(idx, options[idx])
        valids.append(str(idx))
        
    while True:
        print(msgstring)
        val = input("Type a number: ")

        if val in valids:
            print()
            return int(val)

        print("{} is not a valid option, please try again:\n".format(val))

def getLambdaFileIndices(structure, resid):
    """
    Returns an array containing the lambda-file indices for the specified resid.
    Example: CA.pdb, residue: 35.
    """

    u                  = MDAnalysis.Universe(structure)
    numChains          = len(u.segments) - 1
    segmentAatoms      = u.segments[0].atoms
    titratableAtoms    = segmentAatoms.select_atoms('resname ASPT GLUT HSPT')
    titratableResnames = list(titratableAtoms.residues.resnames)
    titratableResids   = list(titratableAtoms.residues.resids)
    targetidx          = titratableResids.index(resid)

    numASPTGLUT        = len(segmentAatoms.select_atoms('resname ASPT GLUT').residues)
    numHSPT            = len(segmentAatoms.select_atoms('resname HSPT').residues)
    factor             = numASPTGLUT + 3 * numHSPT

    count = 1
    for idx in range(0, len(titratableResnames)):

        if idx == targetidx:
            array = []
            for ii in range(0, numChains):
                array.append(count + ii * factor)
            return array

        if titratableResnames[idx] in ['ASPT', 'GLUT']:
            count += 1

        elif titratableResnames[idx] == 'HSPT':
            count += 3

    raise Exception('how did we end up here?')

def notExists(fname):
    """Returns True if the file 'panels/fname' does not yet exist."""
    path = "panels/{}".format(fname)
    
    if os.path.exists(path):
        print('{} already exists, not creating it again...'.format(path))
        return False
    
    return True

def RMSDPlot(sim, rep, sel):
    """
    Creates RMSD plots for a selection of residues. Loads MD_conv.xtc.
    sim: the simulation, e.g. '4HFI_4'
    rep: the replica, e.g. 1
    sel: selection, e.g. '32-35'
    """

    path1 = '{}/{:02d}/CA.pdb'.format(sim, rep)
    path2 = '{}/{:02d}/MD_conv.xtc'.format(sim, rep)
    u = MDAnalysis.Universe(path1, path2)

    # INDIVIDUAL CHAINS
    chain = ['A', 'B', 'C', 'D', 'E']
    for idx in range(0, len(chain)):
        R = MDAnalysis.analysis.rms.RMSD(u, select='segid {} and {}'.format(chain[idx], sel))
        R.run(step=2)
        t  = [val / 1000.0 for val in R.rmsd.T[1]]
        x1 = R.rmsd.T[2]
        plt.plot(t, x1, linewidth=0.5, label=chain[idx])

    # ALL CHAINS
    R = MDAnalysis.analysis.rms.RMSD(u, select='(segid A B C D E) and {}'.format(sel))
    R.run(step=2)
    t  = [val / 1000.0 for val in R.rmsd.T[1]]
    x1 = R.rmsd.T[2]
    plt.plot(t, x1, linewidth=0.5, label='all', color='black')

    plt.xlabel("time (ns)")
    plt.ylabel(r"RMSD ($\AA$)")
    plt.xlim(0, 1000)
    plt.ylim(0, 5)
    plt.title('{} RMSD segment {}'.format(sim, sel))
    plt.legend()
    plt.tight_layout()
    plt.savefig('panels/rmsd_{}_{}.png'.format(sim, sel))
    plt.clf(); plt.close()

class PanelBuilder:
    """
    Combines multiple functions and tries to create the entire panel at once.
    target: <int> the target resid e.g. 35
    resids: <list> the contacts you'd like to check, e.g. [158c, 'NA']
    rmsd: <string> optional, e.g. 'resid 15 to 22'
    test: <bool> is this a test run? (faster)
    """

    def __init__(self, target, resids, rmsd='', test=False):
        self.target   = target
        self.resids   = resids
        self.rmsd     = rmsd
        self.test     = test

        if self.test:
            self.sims = ['4HFI_4']
            self.reps = [1]
        else:
            self.sims = ['4HFI_4', '4HFI_7', '6ZGD_4', '6ZGD_7']
            self.reps = [1]

        for sim in self.sims:
            for rep in self.reps:

                # CREATE THE CHARGE PLOTS
                if notExists("proto_{}_{}.png".format(sim, self.target)):
                    self.chargePlot(sim, rep)
                
                # CREATE THE MINIMUM DISTANCE PLOTS
                for resid in self.resids:
                    if notExists('mindist_{}_{}-{}.png'.format(sim, self.target, resid)):
                        self.mindistPlot(sim, rep, resid)

                # CREATE THE RMSD PLOTS
                if self.rmsd != '':
                    if notExists('rmsd_{}_{}.png'.format(sim, self.target)):
                        self.RMSDPlot(sim, rep)

        # STUFF RELATED TO THE PANELS
        self.rowCount = 0
        self.createPanelRows()
        self.createPanelColumns()

    def chargePlot(self, sim, rep):
        """
        Make the charge plot in time for residue. Does not work for histidines.
        sim: the simulation, e.g. '4HFI_4'
        rep: the replica, e.g. 1
        res: the residue, e.g. 35
        """
        print('Creating charge plot')

        chain = ['A', 'B', 'C', 'D', 'E']
        array = getLambdaFileIndices('{}/{:02d}/CA.pdb'.format(sim, rep), self.target)

        store = []
        for idx in range(0, len(array)):
            data = loadxvg('{}/{:02d}/cphmd-coord-{}.xvg'.format(sim, rep, array[idx]), dt=5000, b=0)
            t    = [val / 1000.0 for val in data[0]] # ps -> ns
            x    = [1.0 - val for val in data[1]] # deprotonation -> protonation
            store.append(x)

            plt.plot(t, x, linewidth=1, label=chain[idx])

        # PLOT MEAN PROTONATION
        # average = [0] * len(store[0])
        # for idx in range(0, len(store[0])):
        #     average[idx] = store[0] + store[1] + store[2] + store[3] + store[4]
        # plt.plot(t, x, linewidth=1.5, label='mean', color='b', linestyle=':')

        plt.ylabel('Protonation')
        plt.xlabel('Time (ns)')
        plt.axis([0, 1000, -0.1, 1.1])
        plt.title('{} protonation {}'.format(sim, self.target))
        plt.legend()
        plt.tight_layout()
        plt.savefig('panels/proto_{}_{}.png'.format(sim, self.target))
        plt.clf(); plt.close()

    def mindistPlot(self, sim, rep, resid):
        """
        Currently a wrapper for GROMACS mindist. Makes the minimum distance plots in time. Uses MD_conv.xtc.
        sim: the simulation, e.g. '4HFI_4'
        rep: the replica, e.g. 1
        resid: the residue it makes contacts with, e.g. 158c
        """
        print("Creating mindist plot")

        # Go to the simulation directory
        os.chdir('{}/{:02d}'.format(sim, rep))

        # Process the principal vs complementary identifier.
        # Note: 158c gives the correct distances using these lists, and 158 is 
        # in fact complementary to 35 so these chain2 orders are correct.
        # Also, we need to make an exception for NA, CL, as shown below.
        chain1 = ['A','B','C','D','E']
        if resid not in ['NA', 'CL']:
            if resid[-1] == 'c':
                chain2 = ['E','A','B','C','D']
                temp = int(resid[:-1])
            elif resid[-1] == 'p':
                chain2 = ['B','C','D','E','A']
                temp = int(resid[:-1])
            else:
                chain2 = ['A','B','C','D','E']
                temp = int(resid)
        else:
            temp = resid
            chain2 = 5 * [temp]

        # Create the index file required for the analysis
        stdin = ['q']
        for chain in ['A', 'B', 'C', 'D', 'E'][::-1]:
            stdin.insert(0, 'r {} & chain {}'.format(self.target, chain))
            stdin.insert(0, 'r {} & chain {}'.format(temp, chain))

        gromacs('make_ndx -f CA.pdb -o mindist.ndx', stdin=stdin)

        # Call GROMACS mindist using the mindist.ndx we just created:
        for idx in range(0, len(chain1)):
            sel1 = 'r_{}_&_ch{}'.format(self.target, chain1[idx])
            if resid == 'NA':
                sel2 = 18 # this group number corresponds to NA
            elif resid == 'CL':
                sel2 = 19 # this group number corresponds to CL
            else: # business as usual
                sel2 = 'r_{}_&_ch{}'.format(temp, chain2[idx])

            if self.test:
                # Speed things up significantly if this is just a test run.
                gromacs('mindist -s MD.tpr -f MD_conv.xtc -n mindist.ndx -dt 10000', stdin=[sel1, sel2])
            else:
                gromacs('mindist -s MD.tpr -f MD_conv.xtc -n mindist.ndx -dt 10', stdin=[sel1, sel2])

            data = loadxvg('mindist.xvg')
            t = [val / 1000.0 for val in data[0]]
            x = data[1]
            plt.plot(t, x, linewidth=0.5, label='{}-{}'.format(chain1[idx], chain2[idx]))

        os.system('rm -f mindist.ndx \\#*\\#')
        os.chdir('../..')

        plt.xlabel("time (ns)")
        plt.xlim(0, 1000)
        if temp in ['NA', 'CL']:
            plt.ylim(0, 2)          # Use 2 nm for ions and 1 nm for rest.
        else:
            plt.ylim(0, 1)
        plt.ylabel("Minimum distance (nm)")
        plt.title('{} mindist {}-{}'.format(sim, self.target, resid))
        plt.legend()
        plt.tight_layout()
        plt.savefig('panels/mindist_{}_{}-{}.png'.format(sim, self.target, resid))
        plt.clf(); plt.close()

    def RMSDPlot(self, sim, rep):
        pass

    def createPanelRows(self):
        """Creates the (temporary) panel rows."""
        print("Creating panel rows")

        # THE FIRST ROW IS ALWAYS A ROW OF CHARGE PLOTS.
        A = 'panels/proto_6ZGD_7_{}.png'.format(self.target)
        B = 'panels/proto_6ZGD_4_{}.png'.format(self.target)
        C = 'panels/proto_4HFI_7_{}.png'.format(self.target)
        D = 'panels/proto_4HFI_4_{}.png'.format(self.target)
        self.rowCount += 1
        os.system('convert {} {} {} {} +append panels/row_{}.png'.format(A, B, C, D, self.rowCount))

        # THE ROWS BELOW COME FROM MINDIST BETWEEN RESIDS
        for resid in self.resids:
            A = 'panels/mindist_6ZGD_7_{}-{}.png'.format(self.target, resid)
            B = 'panels/mindist_6ZGD_4_{}-{}.png'.format(self.target, resid)
            C = 'panels/mindist_4HFI_7_{}-{}.png'.format(self.target, resid)
            D = 'panels/mindist_4HFI_4_{}-{}.png'.format(self.target, resid)
            self.rowCount += 1
            os.system('convert {} {} {} {} +append panels/row_{}.png'.format(A, B, C, D, self.rowCount))

        # THE FINAL ROW IS OPTIONAL AND COMES FROM RMSD
        if self.rmsd != '':
            A = 'panels/rmsd_6ZGD_7_{}.png'.format(self.target)
            B = 'panels/rmsd_6ZGD_4_{}.png'.format(self.target)
            C = 'panels/rmsd_4HFI_7_{}.png'.format(self.target)
            D = 'panels/rmsd_4HFI_4_{}.png'.format(self.target)
            self.rowCount += 1
            os.system('convert {} {} {} {} +append panels/row_{}.png'.format(A, B, C, D, self.rowCount))

    def createPanelColumns(self):
        '''Joins the (temporary) panel rows together to make the final panel.'''
        print("Creating final panel")

        str = ""
        for num in range(1, self.rowCount + 1):
            str += 'panels/row_{}.png '.format(num)

        os.system('convert {} -append panels/panel_{}.png'.format(str, self.target))

if __name__ == "__main__":
    PanelBuilder(35, ['158c', 'NA', 'CL'])
