from pathlib import Path
import json
import argparse
from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor
import os
#
import biotite.structure as struc
import biotite.structure.io as strucio
from biotite.structure import AtomArray

def main():
    parser = argparse.ArgumentParser(
        description="Score RMSD of .pdb files in folder against reference (do not input multi-state references)"
    )
    parser.add_argument(
        "input",
        type=str,
        help="Path to .json file with keys as path to .pdb, item as path to reference .pdb"
    )
    parser.add_argument(
        "-m", "--mode",
        type=str,
        default='all',
        choices=['all', 'CA', 'backbone'],
        help="Type of RMSD to calculate (heavy atom RMSD, C_alpha RMSD, backbone RMSD)"
    )
    args = parser.parse_args()

    # get inputs
    with open(args.input, 'r') as file:
        inputs = json.load(file)

    # collect inputs for parallel processing
    tasks = [(mobile, inputs[mobile], args.mode) for mobile in list(inputs.keys())]
    try:
        max_workers = int(os.environ['NSLOTS']) #type: ignore
    except:
        max_workers = 4 # dev nodes gives each user 4 slots, presumably
    print(f'Using {max_workers} threads to process {len(tasks)} files')
    
    # calculate RMSD in parallel
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        rmsds = dict(
            tqdm(
                executor.map(worker, tasks),
                total=len(tasks)
            )
        )
    '''
    Single thread
    for mobile in tqdm(list(inputs.keys())):
        rmsds[mobile] = float(calculate_rmsd(
            mobile,
            inputs[mobile],
            args.mode
        ))
    '''
    
    # save output
    jsonpath = str(Path(args.input).parent) + f'/rmsd_{args.mode}_{Path(args.input).stem}.json'
    with open(jsonpath, 'w') as file:
        json.dump(rmsds, file, indent=4)
    print(f'Calculated RMSD of {len(rmsds)} structures with mode {args.mode} to {jsonpath}')

def worker(args):
    mobile, reference, mode = args
    return mobile, float(calculate_rmsd(mobile, reference, mode))

def calculate_rmsd(
    mobile: str,
    reference: str,
    mode: str
):
    # ignore warnings about guessing elements
    import warnings
    warnings.filterwarnings("ignore", category=UserWarning)

    # load structures
    reference_struc: AtomArray = strucio.load_structure(reference) #type: ignore
    mobile_struc: AtomArray = strucio.load_structure(mobile) #type: ignore

    # superimpose
    mobile_backbone = mobile_struc[struc.filter_peptide_backbone(mobile_struc)]
    reference_backbone = reference_struc[struc.filter_peptide_backbone(reference_struc)]
    _, transform = struc.superimpose(
        reference_backbone,
        mobile_backbone,
    )
    mobile_aligned = transform.apply(
        mobile_struc
    )
    
    # get rmsd
    if mode == 'all':
        return struc.rmsd(
            reference_struc,
            mobile_aligned
        )
    elif mode == 'CA':
        return struc.rmsd(
            reference_struc[reference_struc.atom_name == 'CA'],
            mobile_aligned[mobile_aligned.atom_name == 'CA']
        ) 
    elif mode == 'backbone':
        return struc.rmsd(
            reference_backbone,
            mobile_aligned[struc.filter_peptide_backbone(mobile_aligned)]
        )
    
    raise ValueError(f'Invalid mode: {mode}')


if __name__ == "__main__":
    main()