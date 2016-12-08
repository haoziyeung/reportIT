#!/usr/bin/env python
# python 2.7

'''
USAGE: code/IGV_batchscript_generator.py 
DESCRITPION: Generate IGV batch script for creating snapshots of BAMs PER SAMPLE
based on the sample's summary table of variants

# files needed:
# sample BAM
# sample BAI
# IGV batch file output
# IGV snapshot dir
# build version
# image height
# sample summary table
# OPTIONAL: control bam
'''

# ~~~~ LOAD PACKAGES ~~~~~~ #
import sys
import os
import re
import errno
import glob
import pandas as pd
import subprocess as sp
import collections
import argparse


# ~~~~ CUSTOM FUNCTIONS ~~~~~~ #
def write_IGV_script(IGV_batch_file, IGV_snapshot_dir, bam_file, build_version, image_height, locations, Control_bam_file = False):
    # generate an IGV script for batch processing
    # IGV_batch_file : file the script will be written to
    # IGV_snapshot_dir : dir to hold the snapshots that will be created
    # bam_file : bam file to be used; bai file must be present as well!
    # build_version : reference genome to use e.g. hg19, mm10, etc.
    # image_height : height of the snapshot image
    # locations : a list of the chromosome locations in the format ['chr9:21971111-21971111', 'chr9:21971111-21971111', ... etc. ]
    initialize_file("new", IGV_batch_file)
    append_string("snapshotDirectory " + IGV_snapshot_dir, IGV_batch_file)
    append_string("load " + bam_file, IGV_batch_file) 
    if Control_bam_file:
        append_string("load " + Control_bam_file, IGV_batch_file)
    append_string("genome " + build_version, IGV_batch_file)
    append_string("maxPanelHeight " + image_height, IGV_batch_file)
    for location in locations: 
        append_string("goto " + location, IGV_batch_file)
        append_string("snapshot", IGV_batch_file)
    append_string("exit", IGV_batch_file)

def initialize_file(string, output_file):
    # write string to file, overwriting contents
    with open(output_file, "w") as myfile:
        myfile.write(string + '\n')

def append_string(string, output_file):
    # append string to file
    with open(output_file, "a") as myfile:
        myfile.write(string + '\n')

def mkdir_p(path, return_path=False):
    # make a directory, and all parent dir's in the path
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise
    if return_path:
        return path



# ~~~~ GET SCRIPT ARGS ~~~~~~ #
parser = argparse.ArgumentParser(description='IGV snapshot batchscript generator.')
# positional args
parser.add_argument("summary_table_file", help="Path to the summary table for the sample")
parser.add_argument("bam_file", help="Path to the BAM file for the sample")
parser.add_argument("IGV_snapshot_dir", help="Path to the IGV snapshot output directory for the sample")

# optional args
parser.add_argument("-b", default = 'hg19', type = str, dest = 'build_version', metavar = 'build version', help="Build version. Name of the reference genome, Defaults to hg19")
parser.add_argument("-ht", default = '500', type = str, dest = 'image_height', metavar = 'image height', help="Height for the IGV tracks")
parser.add_argument("-cb", default = False, type = str, dest = 'NC_bam', metavar = 'control BAM', help="Path to the control BAM file (NC) for the sample")


args = parser.parse_args()

# print args
summary_table_file = args.summary_table_file; print summary_table_file
bam_file = args.bam_file
IGV_snapshot_dir = args.IGV_snapshot_dir
build_version = args.build_version
image_height = args.image_height
NC_bam = args.NC_bam


IGV_batch_file = os.path.join(IGV_snapshot_dir,"IGV_script.bat")
mkdir_p(IGV_snapshot_dir)

print "Sumamry table file is:", summary_table_file
print "Bam file is:", bam_file
print "IGV_snapshot_dir is:", IGV_snapshot_dir
print "IGV_batch_file is:", IGV_batch_file



# load summary table
summary_df = pd.read_table(summary_table_file)

# make a list of the unique entries to be printed
locations = summary_df[['Chrom','Position', 'Position']].apply(lambda x : '{}:{}-{}'.format(x[0],x[1], x[2]), axis=1).unique()
print locations

# sys.exit()

# start the IGV script
write_IGV_script(IGV_batch_file = IGV_batch_file, 
    IGV_snapshot_dir = IGV_snapshot_dir, 
    bam_file = bam_file, 
    build_version = build_version, 
    image_height = image_height, 
    locations = locations, 
    Control_bam_file = NC_bam)