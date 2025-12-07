import sys


"""
 python ../scripts/merge_files.py ../scripts/merged_files.txt ../competition.md ../data/from_discussions.md ../data/raw_dataset_inspection_report.txt ../data/raw_dataset_dropout_logic_inspection.txt ../data/raw_dataset_inspection.md ../data/cleaned_dataset_columns.md ../README.md schema.py load_data.py data_preprocessor.py landmark_feature.py generate_voids.py orchestrator.py
"""

if len(sys.argv) < 3:
    print("Usage: python merge_files.py output_file input1 input2 ...")
    sys.exit(1)

output_file = sys.argv[1]
input_files = sys.argv[2:]

with open(output_file, 'w', encoding='utf-8') as outfile:
    for fname in input_files:
        with open(fname, 'r', encoding='utf-8') as infile:
            outfile.write(infile.read())
            outfile.write('\n')  # Optional: add a newline between files

print(f"Merged {len(input_files)} files into {output_file}")