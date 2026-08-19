import argparse
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from tqdm import tqdm
import json
import os
#
import pyrosetta
from pyrosetta import get_fa_scorefxn
from pyrosetta.rosetta.protocols.relax import FastRelax
from pyrosetta.rosetta.core.kinematics import MoveMap
from pyrosetta import pose_from_pdb

def main():
    # parse arguments
    parser = argparse.ArgumentParser(
        description="FastRelax input structures, only allowing side chain angle changes, then score with Rosetta"
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
    parser.add_argument(
        "--bb",
        action="store_true",
        help='Whether backbone is flexible during relax'
    )
    parser.add_argument(
        '--no-chi',
        action="store_false",
        dest='chi',
        help='Disable side chain angle movement during relax'
    )
    parser.set_defaults(chi=True)
    parser.add_argument(
        '--cycles',
        type=int,
        default=1,
        help='Number of FastRelax cycles'
    )
    args = parser.parse_args()

    # parse inputs
    tasks = []
    for item in Path(args.input).iterdir():
        if item.suffix == '.pdb':
            tasks.append(str(item))

    # assign workers
    try:
        max_workers = int(os.environ.get('NSLOTS', os.cpu_count())) #type: ignore
    except:
        max_workers = 4 # dev nodes gives each user 4 slots, presumably
    print(f'Using {max_workers} threads to process {len(tasks)} files')
    
    # calculate RMSD in parallel
    with ProcessPoolExecutor(
        max_workers=max_workers,
        initializer=init_worker,
        initargs=(args.bb, args.chi, args.cycles)
    ) as executor: 
        results = dict(tqdm(
            executor.map(worker, tasks),
            total=len(tasks)
        ))

    # save results
    if not Path(args.output).exists():
        Path(args.output).mkdir(parents=True)
    outfile = Path(args.output, 'fastrelax_score.json')
    with open(outfile, 'w') as file:
        json.dump(results, file, indent=4)
    print(f'Scored {len(tasks)} structures to {outfile}')


# create worker objects that only initialize score function and relax object once
scorefxn = None
relax = None
def init_worker(
    bb: bool, chi: bool, cycles: int
):
    global scorefxn, relax

    pyrosetta.init("-mute all")

    scorefxn = get_fa_scorefxn()

    mm = MoveMap()
    mm.set_bb(bb)
    mm.set_chi(chi)

    relax = FastRelax(scorefxn, cycles)
    relax.set_movemap(mm)

# workers relax and score
def worker(
    pdb_path
):
    # open 
    pose = pose_from_pdb(pdb_path)

    # relax
    relax.apply(pose) #type: ignore

    # score
    score = scorefxn(pose) #type: ignore

    # get components
    score_terms = {
        str(component).split('.')[-1]: pose.energies().total_energies()[component]
        for component in scorefxn.get_nonzero_weighted_scoretypes() #type: ignore
    }

    return Path(pdb_path).name, {
        "total_score": score,
        **score_terms
    }

if __name__ == "__main__":
    main()