import argparse
from pathlib import Path
#
from tqdm import tqdm
import biotite.structure.io as strucio
import biotite.structure as struc

def main():
    # arguments
    parser = argparse.ArgumentParser(
        description="Separate homo-oligomer chains (.pdb files) output from ProteinMPNN into separate .pdb files"
    )
    parser.add_argument(
        "input",
        type=str,
        help='Path to folder with homo-oligomer ProteinMPNN .pdb outputs'
    )
    parser.add_argument(
        "output",
        type=str,
        help="Path to output folder"
    )
    args = parser.parse_args()

    # ignore element guessing warnings
    import warnings
    warnings.simplefilter('ignore', UserWarning)

    # iterate through all pdb files in folder
    count = 0
    for item in tqdm(sorted(list(Path(args.input).iterdir()))):
        if item.suffix.endswith('.pdb'):

            # read in PDB
            structure = strucio.load_structure(item)

            # separate by chain
            structure_A = structure[structure.chain_id == "A"] #type: ignore
            structure_B = structure[structure.chain_id == "B"] #type: ignore

            # write out chain A
            strucio.save_structure(
                f'{args.output}/{item.stem}_chainA.pdb',
                structure_A
            )

            # undisplace chain B
            structure_B.coord[:, 0] -= 300

            # write out chain B
            strucio.save_structure(
                f'{args.output}/{item.stem}_chainB.pdb',
                structure_B
            )

            count += 1
    
    print(f'Separated {count} .pdb files to {args.output}')
        

if __name__ == "__main__":
    main()