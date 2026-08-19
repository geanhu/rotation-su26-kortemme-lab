import argparse
from tqdm import tqdm
from pathlib import Path
import os
import pandas as pd
#
from Bio.PDB.MMCIFParser import FastMMCIFParser
from Bio.PDB.PDBIO import PDBIO
from frame2seq import Frame2seqRunner

def main():
    parser = argparse.ArgumentParser(
        description="Score structure-sequence compatibility with Frame2Seq"
    )
    parser.add_argument(
        "input",
        type=str,
        help="Path to folder of PDB files (.cif files will be converted to .pdb first)"
    )
    parser.add_argument(
        "output",
        type=str,
        help="Path to folder of output"
    )
    args = parser.parse_args()

    # suppress user warnings
    import warnings
    warnings.simplefilter('ignore', UserWarning)

    # go to output folder
    if not Path(args.output).exists():
        Path(args.output).mkdir()
    os.chdir(args.output)

    # open input
    input = []
    parser = FastMMCIFParser(QUIET=True) # we only care about structure coords, not annotations
    io = PDBIO()
    print('Parsing input PDBS ...')
    for file in tqdm(list(Path(args.input).iterdir())):
        # open pdb directly
        if file.suffix == '.pdb':
            input.append(str(file))

        # if .cif -> need to convert to .pdb
        # since Frame2Seq manually parses .pdb
        if file.suffix == '.cif':
            # skip conversion if exists
            pdb_path = Path(file.parent, file.stem + '.pdb')
            if pdb_path.exists():
                continue

            # else, convert
            structure = parser.get_structure("structure", str(file))
            io.set_structure(structure)
            io.save(str(pdb_path))
            input.append(str(pdb_path))

    # scoring
    print('Initializing Frame2Seq ...')
    runner = Frame2seqRunner()
    for pdb in tqdm(input):
        runner.score(
            pdb_file = pdb,
            chain_id = 'A',
            verbose = False
        )

    # combine scores
    print('Combining scores ...')
    dfs = []
    for csvfile in Path(args.output, 'frame2seq_outputs/scores').iterdir():
        dfs.append(pd.read_csv(csvfile))
        csvfile.unlink()
    Path(args.output, 'frame2seq_outputs/scores').rmdir()
    Path(args.output, 'frame2seq_outputs').rmdir()
    #
    df = pd.concat(dfs, ignore_index=True)
    df.to_csv(Path(args.output, 'scores.csv'))

    # print
    print(f'Scored sequences for {len(input)} structures with Frame2Seq to {args.output}/scores.csv')

if __name__ == "__main__":
    main()