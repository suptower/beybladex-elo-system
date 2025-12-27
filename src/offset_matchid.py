# Take input and output file from command line argument
# Offset all match ids by given offset
import sys
def offset_match_ids(input_file, output_file, offset):
    with open(input_file, 'r', encoding='utf-8') as infile, open(output_file, 'w', encoding='utf-8') as outfile:
        # skip header
        next(infile)
        for line in infile:
            parts = line.strip().split(',')
            if len(parts) < 2:
                continue
            try:
                # match id has format M0001
                match_id = parts[0][1:]  # Remove the 'M' prefix
                match_id = int(match_id)
                new_match_id = match_id + offset
                parts[0] = "M" + str(new_match_id).zfill(4)
                # Remove last column
                #parts = parts[:-1]
                outfile.write(','.join(parts) + '\n')
            except ValueError:
                continue

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python offset_matchid.py <input_file> <output_file> <offset>")
        sys.exit(1)
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    offset = int(sys.argv[3])
    print(f"Offsetting match IDs by {offset}")
    offset_match_ids(input_file, output_file, offset)