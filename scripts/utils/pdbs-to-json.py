from pathlib import Path
import json
import argparse

def main():
    parser = argparse.ArgumentParser(
        description="Take folder and create .json with keys being all .pdb files in folder"
    )
    parser.add_argument(
        "input",
        type=str,
        help="Path to folder with .pdb files"
    )
    args = parser.parse_args()

    # dict to dump into json
    pdbs = {}

    # iterate through all files
    for item in Path(args.input).iterdir():
        if str(item).endswith('.pdb'): #only include .pdb files
            pdbs[str(item)] = ""
    
    # write json file
    jsonpath = str(Path(args.input)) + '/' + Path(args.input).name + '.json'
    with open(jsonpath, 'w') as file:
        json.dump(pdbs, file, indent=4)
    
    print(f'Wrote paths of {len(pdbs)} .pdb files to {jsonpath}')


if __name__ == "__main__":
    main()