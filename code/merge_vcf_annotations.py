#!/usr/bin/env python
# python 2.7


"""
USAGE: merge_vcf_annotations.py run_barcodes_file.txt vcf_query_file.tsv annovar_annotations_file.txt transcript_list.txt panel_genes.txt actionable_genes.txt

DESCRIPTION:
0. Get Sample ID's and Barcode ID's from the sample_barcode_IDs.tsv file previously created by the pipeline
1. Get VCF Query and Annotation files (IonXpress_008_query.tsv, IonXpress_008.hg19_multianno.txt), and sample_barcode_IDs.tsv
2. Merge the VCF and Annotation tables
3. Split the Annotaton transcript fields into separate rows
4. Add sample ID, barcode, and run fields
5. Save summary, full, and filtered tables

This script operates on a single sample in an analysis run
"""

# ~~~~ LOAD PACKAGES ~~~~~~ #
# virtualenv : /ifs/home/kellys04/.local/lib/python2.7/site-packages
import sys
import os
import errno
import pandas as pd # pandas==0.17.1
import numpy as np # numpy==1.11.0
import pipeline_functions as pl

# ~~~~ CUSTOM FUNCTIONS ~~~~~~ #
def test_canonical_transcripts(df, canon_trancr_list):
    # check to make sure that only canonical transcript ID's are in the df
    for transcript in  df['Transcript'].tolist():
        transcript = str(transcript)
        # print transcript
        if not transcript in canon_trancr_list:
            print "ERROR: Transcript in table is not in the canonical transcript list:\n" + transcript
            print "Exiting..."
            sys.exit()

def test_filtered_genes(df, unique_genes_list):
    # test to make sure that all unique genes are in the table
    for gene in table_genes:
        gene = str(gene)
        if not gene in merge_df['Gene'].tolist():
            print "ERROR: Gene was not present in the table after filtering:\n" + gene
            print "Did the gene lack a canonical transcript? Better check!"
            print "Exiting..."
            sys.exit()

def find_vcf_timestamp(vcf_file):
    # find line in VCF file that looks like this:
    ##fileUTCtime=2016-09-23T16:46:51
    with open(vcf_file) as f:
        for line in f:
            if "fileUTCtime" in line:
                return line.strip().split("=")[1]


# ~~~~ GET SCRIPT ARGS ~~~~~~ #
# print 'script name is:', sys.argv[0]
# print 'Number of arguments:\n', len(sys.argv)
# print 'Argument List:', str(sys.argv)
barcodes_file = sys.argv[1]
query_file = sys.argv[2]
annotation_file = sys.argv[3]
canon_trancr_file = sys.argv[4]
panel_genes_file = sys.argv[5]
actionable_genes_file = sys.argv[6]
analysis_ID = sys.argv[7]
vcf_file = sys.argv[8]

# load the filter criteria for the summary table
filter_criteria_json_file = 'filter_criteria.json'
filter_criteria = pl.load_json(filter_criteria_json_file)

vcf_timestamp = find_vcf_timestamp(vcf_file)
canon_trancr_list = pl.list_file_lines(canon_trancr_file)
panel_genes = pl.list_file_lines(panel_genes_file)
actionable_genes = pl.list_file_lines(actionable_genes_file)
outdir = os.path.dirname(annotation_file)

# Summary Table Fields:
summary_cols = ["Chrom", "Position", "Ref", "Variant", "Gene", "Quality", "Coverage", "Allele Coverage", "Strand Bias", "Coding", "Amino Acid Change", "Transcript", "Frequency", "Sample Name", "Barcode", "Run Name", "Review", "Analysis ID", "Date"]



# ~~~~ LOAD TABLES ~~~~~~ #
barcodes_df = pd.read_table(barcodes_file,sep='\t',header=0,na_values=['.'])
query_df = pd.read_table(query_file,sep='\t',header=0,na_values=['.'])
annotation_df = pd.read_table(annotation_file,sep='\t',header=0,na_values=['.'])


# ~~~~ GET SAMPLE BARCODE ID ~~~~~~ #
barcode_ID = os.path.basename(os.path.dirname(query_file))
sample_ID = barcodes_df.loc[barcodes_df['Barcode'] == barcode_ID, 'Sample Name'].values[0]
run_ID = barcodes_df.loc[barcodes_df['Barcode'] == barcode_ID, 'Run Name'].values[0]


# ~~~~ PROCESS & MERGE TABLES ~~~~~~ #
# rename the columns for merging
annotation_df = annotation_df.rename(columns = {'Chr':'Chrom', 'Start':'Position', 'Ref':'Ref', 'Alt':'Variant', 'Gene.refGene':'Gene'})

query_df = query_df.rename(columns = {'Chrom':'Chrom', 'Position':'Position', 'Ref':'Ref'})

# merge
merge_df = pd.merge(annotation_df, query_df, on=['Chrom', 'Position', 'Ref', 'Variant']) # , how = 'left'

# split the AAChange rows in the table
merge_df = pl.split_df_col2rows(dataframe = merge_df, split_col = 'AAChange.refGene', split_char = ',', new_colname = 'AAChange')


# split the new columns into separate columns
merge_df = pl.split_df_col2cols(dataframe = merge_df, split_col = 'AAChange', split_char = ':', new_colnames = ['Gene.AA', 'Transcript', 'Exon', 'Coding', 'Amino Acid Change'], delete_old = True)

# the merged fields:
# Chrom Position    End Ref Variant Func.refGene    Gene.refGene    GeneDetail.refGene
# ExonicFunc.refGene  cosmic68    clinvar_20150629    1000g2015aug_all
# Quality Allele Frequency    Coverage    Allele Coverage Strand Bias Gene
# Transcript  Exon    Coding  Amino Acid Change   Barcode Sample Name Run Name

# ~~~~ FILTER TABLE ~~~~~~ #
'''
merge table:
filter for only canon transcripts # canon_trancr_list
filter for desired variant qualities

summary table:
filter for desired columns
'''

# get the list of unique genes in the table
table_genes = merge_df.Gene.unique()

# keep only canonical transcripts
merge_df = merge_df[merge_df['Transcript'].isin(canon_trancr_list)]

# sanity check:
# make sure only canonical transcripts passed the filter
test_canonical_transcripts(merge_df, canon_trancr_list)
# make sure that all unique genes are represented after filtering for canonical transcripts
# test_filtered_genes(merge_df, table_genes)
# don't do this it doesn't work for variants that had no trainscript..



# add sample IDs to table
merge_df['Barcode'] = barcode_ID
merge_df['Sample Name'] = sample_ID
merge_df['Run Name'] = run_ID
merge_df['Analysis ID'] = analysis_ID
merge_df['Date'] = vcf_timestamp

# keep only the panel genes; default Unknown Significance
merge_df = merge_df[merge_df["Gene"].isin(panel_genes)]

# add review; Known Signficance, Unknown Significance ; panel genes
# default is Unknown Signficiance
merge_df['Review'] = 'US'

# change actionable genes to Known Signficance
merge_df.loc[merge_df["Gene"].isin(actionable_genes), 'Review'] = "KS"
# !! need tests for these ^^

# make a copy of the complete table before filtering for qualities
full_df = merge_df

# filter varaints based on quality criteria; filter rows
# only filter if there's at least 1 row..
# pl.my_debugger(globals().copy())
if len(merge_df) > 0:
    merge_df = pl.table_multi_filter(merge_df, filter_criteria)
else:
    print """
WARNING: Table lenght {} is less than 1; table has no rows, and will not be filtered.
    """.format(len(merge_df))

# make the summary table
# filter out fields that aren't needed for reporting; filter columns
summary_df = merge_df[summary_cols]



# ~~~~ SAVE TABLES ~~~~~~ #
summary_file = os.path.join(outdir, barcode_ID + "_summary.tsv")
summary_df.to_csv(summary_file, sep='\t', index=False)
print "Summary table (filtered rows & columns) saved to:\n" + summary_file + "\n"

merge_file = os.path.join(outdir, barcode_ID + "_filtered.tsv")
merge_df.to_csv(merge_file, sep='\t', index=False)
print "Filtered table (rows only) saved to:\n" + merge_file + "\n"

full_table_file = os.path.join(outdir, barcode_ID + "_full_table.tsv")
full_df.to_csv(full_table_file, sep='\t', index=False)
print "Full table saved to :\n" + full_table_file + "\n"
