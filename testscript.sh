#!/bin/bash

# Input multi-FASTA file path
multi_fasta_file="uniprotkb.fasta"

# Name of the file to keep track of the progress
progress_file="progress.txt"

# Dry run mode flag
dry_run=false

# Check if the script is run in dry run mode
if [ "$1" == "--dry-run" ]; then
    dry_run=true
    echo "Dry run mode enabled. Only printing commands:"
fi

# Check if progress file exists and get the last processed file
if [ ! -f "$progress_file" ]; then
    touch "$progress_file"
fi

last_processed_file=$(cat "$progress_file")

# Function to parse multi-FASTA file into individual files using Python
parse_fasta() {
    python3 -c '
import os
import re

# Read multi-FASTA file path
multi_fasta_file = "uniprotkb_glycoprotein_AND_organism_id_2023_11_27.fasta"

# Open multi-FASTA file for parsing

with open(multi_fasta_file, "rt") as f:
    sequences = f.read().split(">")

# Process each sequence and write to individual files
count = 0
for seq in sequences:
    accession = re.search(r"([OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2})", seq)
    if accession:
        accession = accession.group(1)
        filename = f"{accession}.fa"
        with open(filename, "wt") as f:
            f.write(">"+seq)
            count = count + 1
        print(f"Processed sequence with accession: {accession}, {count}")
    '
}

# Parse multi-FASTA file into individual files
if [ ! -f "$last_processed_file" ]; then
    parse_fasta "$multi_fasta_file"   
fi

skip_flag=false

if [ -z "$last_processed_file" ]; then
    skip_flag=false
else
    echo "starting from $last_processed_file"
    skip_flag=true
fi

for fasta_file in *.fa; do
    if [ "$skip_flag" = true ]; then
        if [ "$last_processed_file" = "$fasta_file" ]; then
            skip_flag=false
        else
            continue
        fi
    fi

    if [ -f "$fasta_file" ]; then
        # Extract UniProt accession from the FASTA file
        uniprot_acc=${fasta_file/.fa/}
        
        # Create output folder based on UniProt accession
        if [ -n "$uniprot_acc" ]; then
            output_folder="${uniprot_acc}"
            mkdir -p "${output_folder}"
            
            # Formulate Docker command
            docker_command="docker run --rm -v ./:/data consurf-alone:0.0.1 --algorithm HMMER --Maximum_Likelihood --seq /data/${fasta_file} --dir /data/${output_folder}"

            if [ "$dry_run" = true ]; then
                echo "$docker_command"  # Print Docker command
                echo "Processing file: $fasta_file"
            else
                # Run Docker command for each individual FASTA file
                echo "Executing: $docker_command"
                $docker_command

                # Record the processed file in the progress file
                echo "$fasta_file" > "$progress_file"
            fi
        else
            echo "Could not extract UniProt accession from file: $fasta_file"
        fi
    fi
done
