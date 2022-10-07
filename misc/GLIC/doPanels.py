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
    Returns an array containing the lambda-file indices for the specified residue.
    Example: MD.pdb, residue: 35
    """

    u                  = MDAnalysis.Universe(structure)
    numChains          = len(u.segments) - 1
    segmentAatoms      = u.segments[0].atoms
    titratableAtoms    = segmentAatoms .select_atoms('resname ASPT GLUT HSPT')
    titratableResnames = list(titratableAtoms.residues.resnames)
    titratableResids   = list(titratableAtoms.residues.resids)
    targetid           = 1 + titratableResids.index(resid)
    
    numASPTGLUT        = len(segmentAatoms.select_atoms('resname ASPT GLUT').residues)
    numHSPT            = len(segmentAatoms.select_atoms('resname HSPT').residues)
    factor             = numASPTGLUT + 3 * numHSPT

    count = 1
    for idx in range(0, len(titratableResnames)):

        if idx + 1 == targetid:
            array = []
            for ii in range(0, numChains):
                array.append(count + ii * factor)
            return array

        if titratableResnames[idx] in ['ASPT', 'GLUT']:
            count += 1

        elif titratableResnames[idx] == 'HSPT':
            count += 3

def chargePlot(sim, rep, resid):
    """
    Make the charge plot in time for residue. Does not work for histidines.
    sim: the simulation, e.g. '4HFI_4'
    rep: the replica, e.g. 1
    res: the residue, e.g. 35
    """

    chain = ['A', 'B', 'C', 'D', 'E']
    array = getLambdaFileIndices('{}/{:02d}/CA.pdb'.format(sim, rep), resid)

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
    plt.title('{} protonation {}'.format(sim, resid))
    plt.legend()
    plt.tight_layout()
    plt.savefig('panels/proto_{}_{}.png'.format(sim, resid))
    plt.clf(); plt.close()

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

def mindistPlot(sim, rep, resid1, resid2, chain1, chain2, name):
    """
    Creates mindists plots between sel1 and sel2. Uses MD_conv.xtc.
    sim: the simulation, e.g. '4HFI_4'
    rep: the replica, e.g. 1
    resid1: residue 1, e.g. 35
    resid1: residue 2, e.g. 158
    chain1: chains to match e.g. ['A', 'B', 'C', 'D', 'E']
    chain2: chains to match e.g. ['E', 'A', 'B', 'C', 'D']
    name: file/title name, e.g. 'E35-T158'
    """

    if len(chain1) != len(chain2):
        raise Exception('chain1 and chain2 must be same length')

    os.chdir('{}/{:02d}'.format(sim, rep))

    stdin = ['q']
    for chain in ['A', 'B', 'C', 'D', 'E'][::-1]:
        stdin.insert(0, 'r {} & chain {}'.format(resid1, chain))
        stdin.insert(0, 'r {} & chain {}'.format(resid2, chain))

    gromacs('make_ndx -f CA.pdb -o mindist.ndx', stdin=stdin)

    for idx in range(0, len(chain1)):
        sel1 = 'r_{}_&_ch{}'.format(resid1, chain1[idx])
        sel2 = 'r_{}_&_ch{}'.format(resid2, chain2[idx])

        gromacs('mindist -s MD.tpr -f MD_conv.xtc -n mindist.ndx -dt 10', stdin=[sel1, sel2])

        data = loadxvg('mindist.xvg')
        t = [val / 1000.0 for val in data[0]]
        x = data[1]
        plt.plot(t, x, linewidth=0.5, label='{}-{}'.format(chain1[idx], chain2[idx]))

    os.system('rm -f mindist.ndx \\#*\\#')
    os.chdir('../..')

    plt.xlabel("time (ns)")
    plt.xlim(0, 1000)
    plt.ylim(0, 1)
    plt.ylabel("Minimum distance (nm)")
    plt.title('{} mindist {}'.format(sim, name))
    plt.legend()
    plt.tight_layout()
    plt.savefig('panels/mindst_{}_{}.png'.format(sim, name))
    plt.clf(); plt.close()

def mindistIonsPlot(sim, rep, resid, ion, name):
    """
    Creates mindists plots between sel1 and sel2. Uses MD_conv.xtc.
    sim: the simulation, e.g. '4HFI_4'
    rep: the replica, e.g. 1
    sel: selection, e.g. 35
    ionName: name of the ion, e.g. 'NA'
    name: file/title name, e.g. 'E35-Na+'
    """

    os.chdir('{}/{:02d}'.format(sim, rep))

    stdin = ['q']
    for chain in ['A', 'B', 'C', 'D', 'E']:
        stdin.insert(0, 'r {} & chain {}'.format(resid, chain))

    gromacs('make_ndx -f CA.pdb -o mindist.ndx', stdin=stdin)

    for chain in ['A', 'B', 'C', 'D', 'E']:
        if ion == 'NA':
            ndx = 18 # 18 is NA
        elif ion == 'CL':
            ndx = 19 # 19 is CL

        gromacs('mindist -s MD.tpr -f MD_conv.xtc -n mindist.ndx -dt 10', stdin=['r_{}_&_ch{}'.format(resid, chain), ndx])

        data = loadxvg('mindist.xvg')
        t = [val / 1000.0 for val in data[0]]
        x = data[1]
        plt.plot(t, x, linewidth=0.5, label=chain)

    os.system('rm -f mindist.ndx \\#*\\#')
    os.chdir('../..')

    plt.xlabel("time (ns)")
    plt.xlim(0, 1000)
    plt.ylim(0, 5)
    plt.ylabel("Minimum distance (nm)")
    plt.title('{} mindist {}'.format(sim, name))
    plt.legend()
    plt.tight_layout()
    plt.savefig('panels/mindst_{}_{}.png'.format(sim, name))
    plt.clf(); plt.close()

def notExists(fname):
    """Returns True if the file 'panels/fname' does not yet exist."""
    path = "panels/{}".format(fname)
    
    if os.path.exists(path):
        print('{} already exists, not creating it again...'.format(path))
        return False
    
    return True

def doPanel(target, resids, rmsd=[], test=False):
    """
    Combines multiple functions and tries to create the entire panel at once.
    target: <int> the target resid e.g. 35
    resids: <list> the contacts e.g. [158, 'NA']
    rmsd: <string> optional, e.g. 'resid 15 to 22'
    test: <bool> is this a test run (faster)?
    """

    for sim in ['4HFI_4']:
    # for sim in ['4HFI_4', '4HFI_7', '6ZGD_4', '6ZGD_7']:
        rep = 1
    
        # CREATE THE CHARGE PLOTS
        if notExists("proto_{}_{}.png".format(sim, target)):
            chargePlot(sim, rep, target)

doPanel(243, [1])





# for sim in ['4HFI_4']:
# # for sim in ['4HFI_4', '4HFI_7', '6ZGD_4', '6ZGD_7']:
#     rep = 1

#     # Add: "if file exists... skip" to all analysis functions
#     # Add a function that automatically builds the panels
#     # Add loops to reduce the number of function lines here?

#     # E26
#     chargePlot(sim, rep, 'E26')
#     mindistPlot(sim, rep, 26, 105, ['A','B','C','D','E'], ['A','B','C','D','E'], name='E26-105')
#     mindistPlot(sim, rep, 26, 79, ['A','B','C','D','E'], ['B','C','D','E','A'], name='E26-V79c')
#     mindistPlot(sim, rep, 26, 155, ['A','B','C','D','E'], ['A','B','C','D','E'], name='E26-V155')

#     # D32
#     chargePlot(sim, rep, 'D32')
#     mindistPlot(sim, rep, 32, 122, ['A','B','C','D','E'], ['A','B','C','D','E'], name='D32-D122')
#     mindistPlot(sim, rep, 32, 192, ['A','B','C','D','E'], ['A','B','C','D','E'], name='D32-R192')

#     # E35
#     chargePlot(sim, rep, 'E35')
#     mindistPlot(sim, rep,  35, 158, ['A','B','C','D','E'], ['E','A','B','C','D'], name='E35-T158c')
#     mindistPlot(sim, rep, 35, 29, ['A','B','C','D','E'], ['E','A','B','C','D'], name='E35-S29c')
#     # mindist backbone loopF
#     mindistIonsPlot(sim, rep, '222', ion='NA', name='E222-Na+')

    # # E67
    # chargePlot(sim, rep, 'E67')
    # mindistPlot(sim, rep, 67, yy, ['A','B','C','D','E'], ['A','B','C','D','E'], name='xx-yy')

    # # E69
    # chargePlot(sim, rep, 'E69')
    # mindistPlot(sim, rep, 69, yy, ['A','B','C','D','E'], ['A','B','C','D','E'], name='xx-yy')

    # ECD

    # chargePlot(sim, rep, 'E26')
    # chargePlot(sim, rep, 'E104')
    # chargePlot(sim, rep, 'E177')
    # chargePlot(sim, rep, 'D178')
    # chargePlot(sim, rep, 'E181')
    # RMSDPlot(sim, rep, '172-185') # loopC

    # ECD-TMD

    # chargePlot(sim, rep, 'E26')
    # chargePlot(sim, rep, 'E35')
    # chargePlot(sim, rep, 'D122')
    # chargePlot(sim, rep, 'E243')
    # RMSDPlot(sim, rep, 'resid 32-35') # b1-b2 loop
    # mindistIonsPlot(sim, rep, '35', name='E35-Na+')
    # mindistPlot(sim, rep,  35, 158, ['A','B','C','D','E'], ['E','A','B','C','D'], name='E35-T158')
    # mindistPlot(sim, rep, 243, 248, ['A','B','C','D','E'], ['A','B','C','D','E'], name='E243-K248')

    # TMD

    # chargePlot(sim, rep, 'E243')
    # chargePlot(sim, rep, 'H235')
    # chargePlot(sim, rep, 'E222')
    # RMSDPlot(sim, rep, 'resid 220-245') # M2
    # RMSDPlot(sim, rep, 'resid 246-252') # M2-M3 loop

    # BOTTOM OF TMD + VMD ######################################################

    # chargePlot(sim, rep, 'E222') # good
    # mindistIonsPlot(sim, rep, '222', ion='NA', name='E222-Na+') # bad
    # mindistIonsPlot(sim, rep, '222', ion='CL', name='E222-Cl-') # bad
    # mindistPlot(sim, rep, 222, 220, ['A','B','C','D','E'], ['A','B','C','D','E'], name='E222-S220')
    # mindistPlot(sim, rep, 277, 221, ['A','B','C','D','E'], ['A','B','C','D','E'], name='H277-Y221') # good

    # Idea Berk
    # RMSDPlot(sim, rep, 'resid 35 ')
