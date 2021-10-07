#!/bin/bash

rm -rf __py* charmm*
rm -f residuetypes.dat universe phprocessed.pdb record.dat
rm -f box.pdb solvated.pdb pdb2gmxtemp.pdb ions.pdb buffers.pdb

rm -f \#*
rm -f *.top *.gro *.itp
rm -f mdout.mdp builder.log EM.pdb NVT.pdb NPT.pdb MD.pdb IONS.mdp lambda_*.dat
rm -f *.ndx MD.mdp *.tpr *.log *.edr *.out step*.pdb *.cpt *.trr *.xtc
