"""
Script to offset match IDs in CSV files.

Takes input and output file from command line arguments and offsets all match IDs
by the given offset value.
"""
import sys


def offset_match_ids(input_file, output_file, offset):
    """
    Offset all match IDs in a CSV file by a given value.

    Args:
        input_file: Path to the input CSV file
        output_file: Path to the output CSV file
        offset: Integer offset to add to each match ID
    """
    is_rounds_file = False
    with open(input_file, 'r', encoding='utf-8') as infile, \
         open(output_file, 'w', encoding='utf-8') as outfile:
        # Skip header
        if infile.readline().strip().split(',')[1] == 'round_number':
            is_rounds_file = True
        next(infile)
        for line in infile:
            parts = line.strip().split(',')
            if len(parts) < 2:
                continue
            try:
                # Match ID has format M0001
                match_id = parts[0][1:]  # Remove the 'M' prefix
                match_id = int(match_id)
                new_match_id = match_id + offset
                parts[0] = "M" + str(new_match_id).zfill(4)
                if not is_rounds_file:
                    # remove last column
                    parts = parts[:-1]
                outfile.write(','.join(parts) + '\n')
            except ValueError:
                continue


def main():
    """Main entry point for the script."""
    if len(sys.argv) != 4:
        print("Usage: python offset_matchid.py <input_file> <output_file> <offset>")
        sys.exit(1)
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    offset = int(sys.argv[3])
    print(f"Offsetting match IDs by {offset}")
    offset_match_ids(input_file, output_file, offset)


if __name__ == "__main__":
    main()
