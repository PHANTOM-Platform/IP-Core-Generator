############################################################
## This file is generated automatically by Vivado HLS.
## Please DO NOT edit it.
## Copyright (C) 1986-2017 Xilinx, Inc. All Rights Reserved.
############################################################


# Open project and reset to get a clean state
open_project generated-ipcores -reset


# Add files to project
for { set a 3}  {$a < [lindex $argc]} {incr a} {
   add_files [lindex $argv $a]
}


# Configure Project
set_top [lindex $argv 2]
open_solution [lindex $argv 1]
set_part [lindex $argv 0] -tool vivado
create_clock -period 5 -name default


# Run Synthesis
csynth_design


# Export IP Core
export_design -format ip_catalog

