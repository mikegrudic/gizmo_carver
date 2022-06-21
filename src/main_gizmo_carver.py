"""
   main_gizmo_carver.py

   Purpose:
        Driver file for RADMC carve routines. Call this file when you want
        to run the code. Should not ever need to edit this file.

   Author:
        Sean Feng, feng.sean01@utexas.edu
        Spring 2022
        
        Modified from: main_CarveOut.py, written by:
        Aaron T. Lee, aaron.t.lee@utexas.edu
        Spring 2018

   Written/Tested with Python 3.9, yt 4.0.2
"""

import yt
from writer_gizmo_carver import RadMC3DWriter_Gizmo
from globals_gizmo_carver import *
import inputs_gizmo_carver as inputs
from yt.units import *
import os
from datetime import datetime
import shutil
import numpy as np
import glob as glob
from new_fields_list import *
import sys
import h5py as h5py

# Need to read and concatenate these files of accreted particles
fns = glob.glob(inputs.hdf5_dir+"/blackhole_details/bhswallow*.txt")
print("Accretion files =", fns)

if inputs.mask == True:
    alllines = np.empty((0,19))
    for file in fns:
        #read file
        lines = np.loadtxt(file, comments="#", delimiter=" ", unpack=False)
        #print(np.shape(alllines), np.shape(lines), file, lines)
        alllines=np.concatenate((alllines, lines), axis=0)

        yt.add_field(('PartType0', 'Mask'), function=_Mask, units='g/cm**3', sampling_type='particle', force_override=True)

        yt.add_field(('PartType0', 'MaskedMolecularNumDensity'), function=_MaskedMolecularNumDensity, units='cm**-3', sampling_type='particle', force_override=True)

# Loads file into YT
ds = yt.load(inputs.hdf5_file, unit_base=inputs.unit_base)
print("domain = ", ds.domain_left_edge, ds.domain_right_edge)
try:
    print("Loaded file " + str(ds)) # using classic print() for try/except to work
except NameError:
    assert False, "Unable to properly load file into YT!"

now = datetime.now()
dt_string = now.strftime("%m.%d.%y_%H'%M'%S")

# Create working directory for this run
current_dir = inputs.output_filepath
working_dir_name = os.path.join(current_dir, 'RADMC_inputs_' + inputs.tag+dt_string)
os.mkdir(working_dir_name)

# Make a file to store I/O and setup parameters
f = open(os.path.join(working_dir_name, inputs.out_makeinput), 'w')
original_stdout = sys.stdout #Reset do: sys.stdout = original_stdout 
sys.stdout = f
print("Input parameters (inputs_gizmo_carver.py):")
print("  dust_to_gas ", inputs.dust_to_gas)
print("  molecular_abundance ", inputs.molecular_abundance)
print("  mask abundance ", inputs.mask_abundance)
print("  box_size, box_dim, box_center ", inputs.box_size, inputs.box_dim, inputs.box_center)
print("  hdf5_file ", inputs.hdf5_file)
f = h5py.File(inputs.hdf5_file, 'r')
part = f['PartType5']
print(" Simulation time [code units] = ", f['Header'].attrs['Time'])
print(" Number of stars =", len(f['PartType5']['StellarFormationTime']))

print("Setup output (main_gizmo_carver): ")

box_left = np.add(inputs.box_center, -inputs.box_size)
box_right = np.add(inputs.box_center, inputs.box_size)
box_left_cgs = [Convert(x, inputs.box_units, 'cm', 'cm') for x in box_left]
box_right_cgs = [Convert(x, inputs.box_units, 'cm', 'cm') for x in box_right]

box_left_cgs = unyt_array(box_left_cgs, 'cm')
box_right_cgs = unyt_array(box_right_cgs, 'cm')

print("\nCarving between Left = " + str(box_left_cgs))
print("            to Right = " + str(box_right_cgs))
print("       w/ Resolution = " + str(abs(inputs.box_dim)) + " x " + str(abs(inputs.box_dim)) + "\n")

writer = RadMC3DWriter_Gizmo(ds, a_boxLeft=box_left_cgs, a_boxRight=box_right_cgs, a_boxDim=inputs.box_dim)

# Write the amr grid file (fast)
print("1/7: Writing amr grid file (fast!)")
writer.write_amr_grid(os.path.join(working_dir_name, inputs.out_afname))

# Write the number density file for species (slow)
print("2/7: Writing number density file (slow.)")
if inputs.mask_abundance == True:
    writer.write_line_file(('PartType0', 'MaskedMolecularNumDensity'), os.path.join(working_dir_name, inputs.out_nfname))
else:
    writer.write_line_file(('PartType0', 'MolecularNumDensity'), os.path.join(working_dir_name, inputs.out_nfname))

# Write the dust density file for dust (slow)
print("3/7: Writing dust density file (slow.)")
writer.write_dust_file(('PartType0', 'DustDensity'), os.path.join(working_dir_name, inputs.out_ddfname))

print("4.5/7: Writing microturbulence file (slow.)")
writer.write_line_file(("PartType0", "microturbulence_speed"), os.path.join(working_dir_name, inputs.out_mtfname))

# Write the temperature file for species or dust (slow)
print("5/7: Writing temperature file (slower..)")
print(ds.find_max(("PartType0","gas_temperature")))
writer.write_line_file(("PartType0", "gas_temperature"), os.path.join(working_dir_name, inputs.out_tfname))

# Assuming dust temperature is same as gas for now...
print("6/7: Writing dust temperature file (slower..)")
writer.write_dust_file(("PartType0", "dust_temperature"), os.path.join(working_dir_name, inputs.out_dtfname))

# Write the gas velocity file (slow x 3)
print("7/7: Writing velocity file (slowest...)")
velocity_fields = ["velocity_x", "velocity_y", "velocity_z"]
writer.write_line_file(velocity_fields, os.path.join(working_dir_name, inputs.out_vfname))

# Copy over existing files
print('Copying default files...')
shutil.copy(os.path.join(inputs.existing_filepath, inputs.out_molname), working_dir_name)
shutil.copy(os.path.join(inputs.existing_filepath, inputs.out_wlmname), working_dir_name)
shutil.copy(os.path.join(inputs.existing_filepath, inputs.out_cwlname), working_dir_name)
shutil.copy(os.path.join(inputs.existing_filepath, inputs.out_dksname), working_dir_name)
shutil.copy(os.path.join(inputs.existing_filepath, inputs.out_dtpname), working_dir_name)
shutil.copy(os.path.join(inputs.existing_filepath, inputs.out_linname), working_dir_name)
shutil.copy(os.path.join(inputs.existing_filepath, inputs.out_rmcname), working_dir_name)
shutil.copy(os.path.join(inputs.existing_filepath, inputs.out_execute), working_dir_name)
shutil.copy(os.path.join(inputs.existing_filepath, inputs.out_subscript), working_dir_name)

print('Done! Output files generated at: \n\n' + os.path.abspath(working_dir_name))
