import argparse
from pathlib import Path
#
from tqdm import tqdm
import pandas as pd
import biotite.sequence as seq
import biotite.sequence.io.fasta as fasta

def main():
    parser = argparse.ArgumentParser(
        description="Take folder of designed sequences and list designs in csv"
    )
    parser.add_argument(
        "input",
        type=str,
        help="Path to folder with designed sequences (e.g. design0/seqs)"
    )
    parser.add_argument(
        "--homooligomer", action="store_true",
        help = "Parses sequence design outputs assuming homo-oligomer design (i.e. only takes sequence of chain A, assuming every chain has same sequence)"
    )
    args = parser.parse_args()

    # dict to store sequences
    sequences = {
        'id': [],
        'sequence': []
    }

    # iterate through all fasta files
    for file in tqdm(list(Path(args.input).iterdir())):
        if file.name.endswith('.fa'):
            file = fasta.FastaFile.read(str(file))

            # iterate through all sequences
            for header, sequence in file.items():

                name = header.split(', ')
                # skip if first seq (input)
                if not name[1].startswith('id'):
                    continue

                if args.homooligomer:
                    sequence = sequence.split(':')[0]
                
                # store into dict
                name = name[0] + '_id' + name[1].split('=')[1] #name_id0
                sequences['id'].append(name)
                sequences['sequence'].append(sequence)
    
    # write to csv
    df = pd.DataFrame(sequences)
    df.to_csv(f'{args.input}/seqs.csv', index=False)
    print(f'Wrote {len(df)} sequences to {args.input}/seqs.csv')

if __name__ == "__main__":
    main()