import argparse
import json
from pathlib import Path
from functools import reduce
import os
#
from concurrent.futures import ThreadPoolExecutor
from threading import local
from tempfile import TemporaryDirectory
#
import pandas as pd
from tqdm import tqdm
tqdm.pandas()
# cbutils set up as editable module
from cbutils import (
    aa_code,
    mpnn_score
)
import biotite.structure.io as strucio
import biotite.structure as struc

'''
RUNNING MULTI-THREADED ON GPU (MAY) OVERWHELM GPU VRAM
'''

# filter out warnings
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

def main():
    # parse arguments
    parser = argparse.ArgumentParser(
        description="Use conformational biasing workflow to find single point mutant bias to input structures"
    )
    parser.add_argument(
        "input",
        type=str,
        help="Path to input .json, expecting key = name, value = [path/to/state/A.pdb, path/to/state/B.pdb]; only uses state A sequence"
    )
    parser.add_argument(
        '--chain',
        type=str,
        default='A',
        help='Chain of input structure to use'
    )

    # ProteinMPNN arguments
    parser.add_argument(
        "--proteinmpnn",
        action='store_true',
        help='Run CB with ProteinMPNN as IF model'
    )
    parser.add_argument(
        '--model_name',
        type=str,
        choices = [
            'v_48_002',
            'v_48_010',
            'v_48_020',
            'v_48_030'
        ],
        default='v_48_020',
        help='ProteinMPNN model checkpoint to use'
    )
    parser.add_argument(
        '--backbone_noise',
        type=float,
        default=0.0,
        help='Add backbone noise during ProteinMPNN inference'
    )
    parser.add_argument(
        '--weights',
        type=str,
        choices = [
            'original',
            'soluble'
        ],
        default='soluble',
        help='Whether to use ProteinMPNN trained on original dataset or soluble dataset'
    )

    # ESM
    parser.add_argument(
        '--esm',
        action='store_true',
        help='Run CB with ESM-IF1 as IF model (WARNING: takes long) NOT IMPLEMENTED'
    )

    # Frame2Seq
    parser.add_argument(
        '--frame2seq',
        action='store_true',
        help='Run CB with Frame2Seq as IF model'
    )

    # Caliby
    parser.add_argument(
        '--caliby',
        action='store_true',
        help='Run CB with Caliby as IF model; make sure to set $TMPDIR before running'
    )

    parser.add_argument(
        '--caliby_model',
        type=str,
        choices = [
            'caliby',
            'soluble_caliby',
            'soluble_caliby_v1',
            'caliby_distill',
            'soluble_caliby_distill'
        ],
        default='soluble_caliby',
        help='Caliby model to use'
    )

    # parse
    args = parser.parse_args()

    # determine multi-threading settings
    max_workers = int(os.environ.get('NSLOTS') or 4)
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        max_workers = 1
    print(f'Using {max_workers} threads ...')

    # must run a model
    if (not args.proteinmpnn) and (not args.esm) and (not args.frame2seq) and (not args.caliby):
        raise ValueError("No model(s) selected")

    # collect inputs
    with open(args.input, 'r') as file:
        inputs = json.load(file)
    n_inputs = len(inputs)

    # align sequences and make mutants
    inputs = preprocess_inputs(inputs, args.chain)

    # run each model
    methods = []
    outputs = [] #save output dataframes
    if args.proteinmpnn:
        outputs.append(proteinmpnn(
            inputs,
            args.model_name, args.backbone_noise, args.weights,
            max_workers,
            args.chain
        ))
        methods += 'proteinmpnn'
    if args.esm:
        outputs.append(esm(inputs))
        methods += 'esm '
    if args.frame2seq:
        outputs.append(frame2seq(
            inputs,
            max_workers,
            args.chain
        ))
        methods += 'frame2seq'
    if args.caliby:
        outputs.append(caliby(
            inputs,
            args.caliby_model,
            max_workers,
            args.chain
        ))
        methods += 'caliby'
    methods = '-'.join(methods)

    # save results
    results: pd.DataFrame | None = None
    if len(outputs) > 1:
        results = reduce(
            lambda left, right:
            pd.merge(
                left, right,
                on=['name', 'mut'],
                how='left',
                validate='one_to_one'
            ),
            outputs
        )
    else:
        results = outputs[0]
    #
    savepath = Path(Path(args.input).parent, Path(args.input).stem + f'_conf-bias_{methods}.csv')
    results.to_csv(savepath, index=False) #type: ignore
    print(f'Scored sequences for {n_inputs} structural ensembles using conformational biasing with methods {methods} to {savepath}')

#---- Preprocess inputs

def preprocess_inputs(
    inputs: dict,
    chain: str
):
    print('Preprocessing inputs ...')
    
    # store necessary info
    processed = {}

    for name in tqdm(list(inputs.keys())):
        # get sequences from pdb
        pdbs = inputs[name]
        '''
        IMPORTANT: 
        Directly taking state A sequence; allows inputing state B 
        (e.g. start state) without threading sequence design. (Model only
        uses backbone anyways)
        '''
        wt_seq = get_seq(pdbs[0], chain) 

        # create list of mutants
        muts = []
        mut_seqs = []
        for i, aa in enumerate(wt_seq):
            for aa_new in aa_code:
                if aa_new != aa:
                    mut_seqs.append(wt_seq[:i] + aa_new + wt_seq[i + 1 :])
                    muts.append(f"{aa}{i+1}{aa_new}")

        # save
        processed[name] = {
            'wt': wt_seq,
            'mutants': muts,
            'mutant_seqs': mut_seqs,
            'pdbs': pdbs
        }

        if len(wt_seq) == 0:
            print(name)
    return processed

# open sequence from pdb, regardless of if side chain atoms are present
# prevent gemmi parsing errors where sequence will not be read if SC atoms not present
def get_seq(pdbpath, chain):

    # load
    structure = strucio.load_structure(pdbpath)

    # chain
    structure = structure[structure.chain_id == chain] #type: ignore

    # seq
    sequences, _ = struc.to_sequence(structure)
    return str(sequences[0])

#----Run ProteinMPNN

def proteinmpnn(
    inputs,
    model_name, backbone_noise, weights,
    max_workers: int,
    chain
):
    
    # only import if using
    from colabdesign.mpnn import mk_mpnn_model

    # set multi-threading so threads have separate models
    thread_local = local()

    # initialize model
    def init_worker():
        thread_local.mpnn_model = mk_mpnn_model(
            model_name = model_name,
            backbone_noise = backbone_noise,
            weights = weights
        )

    # prediction for one input
    def worker(name):
        mpnn_model = thread_local.mpnn_model

        # create "rows of df" that will store results for this input
        rows = [
            {'name': name, 'mut': 'wt'},
            *[
                {'name': name, 'mut': mut}
                for mut in inputs[name]['mutants']
            ]
        ] #list of {'name', 'mut'} dicts

        # score for each state
        for i, pdb in enumerate(inputs[name]['pdbs']):

            # load structure model
            mpnn_model.prep_inputs(
                pdb_filename=pdb,
                chain=chain,
                homooligomer=False,
                fix_pos=None,
                inverse=True, #not sure what this set true by default means, esp if no fix pos
                verbose=False,
            )

            # score wt
            wt_score = mpnn_score(
                inputs[name]['wt'],
                mpnn_model
            )
            # save wt score
            rows[0][f'proteinmpnn_pdb{i}'] = wt_score

            # score mutants
            for idx, mut_seq in enumerate(inputs[name]['mutant_seqs']):

                # score mutant
                score = mpnn_score(
                    mut_seq,
                    mpnn_model
                )

                # save score
                rows[idx + 1][f'proteinmpnn_pdb{i}'] = ( #+1 since 0 is WT
                    score - wt_score
                )

        return rows

    # distribute and execute with each worker
    print('Scoring with ProteinMPNN ...')
    names = list(inputs) 
    with ThreadPoolExecutor(
        max_workers = max_workers,
        initializer = init_worker, #separate model each worker
    ) as executor:
        results = list(
            tqdm(
                executor.map(worker, names),
                total = len(names)
            )
        )

    # unpack one level of lists to create long df
    results = [
        row
        for result in results # each input
        for row in result # each mutant
    ]

    return pd.DataFrame(results)

def esm(inputs):
    raise NotImplementedError('Using ESM-IF as model is not implemented.')

def frame2seq(
    inputs,
    max_workers: int,
    chain
):
    # only import if using
    print('Initializing Frame2Seq ...')
    from frame2seq import Frame2seqRunner
    from frame2seq.utils import residue_constants
    from frame2seq.utils.util import get_neg_pll
    from frame2seq.utils.pdb2input import get_inference_inputs
    import torch

    # set multi-threading so threads have separate models
    thread_local = local() 
        
    # set up frame2seq scoring function
    def frame2seq_score(runner, pdb_file: str, input_seqs: list[str], chain_id: str = 'A'):
        """
        Calculates the pseudo-log-likelihood (PLL) scores for a list of input sequences
        given a structure using a Frame2seq model ensemble.

        Args:
            runner: Frame2seqRunner.
                An initialized Frame2seqRunner object containing the ensemble models.
            pdb_file: str
                Path to a PDB file containing the desired protein structure.
            chain_id: str
                Chain identifier (e.g., 'A') corresponding to the chain of interest in the PDB file.
            input_seqs: list of str
                List of amino acid sequences to be evaluated against the structure. Must be length matched.

        Returns:
            scores: list of float
                List of negative PLL scores, one for each input sequence. Higher (less negative)
                values indicate sequences more compatible with the structure.
        """
        # Get structure-based input tensors for inference
        seq_mask, backbone_seq_tokenized, X = get_inference_inputs(pdb_file, chain_id)

        # Decode backbone sequence from tokenized integer representation
        backbone_seq = [
            residue_constants.ID_TO_AA[int(i)] for i in backbone_seq_tokenized[0]
        ]

        # Convert backbone sequence to one-hot encoding using standard AA to ID mapping
        backbone_seq_onehot = residue_constants.sequence_to_onehot(
            sequence=backbone_seq, #type: ignore
            mapping=residue_constants.AA_TO_ID,
        )

        # Convert one-hot numpy array to torch tensor and move to runner device
        backbone_seq_onehot = (
            torch.from_numpy(backbone_seq_onehot).float().unsqueeze(0).to(runner.device)
        )
        # Mask all positions in sequence by setting them to 'X' (unknown amino acid)
        backbone_seq_onehot = torch.zeros_like(backbone_seq_onehot)
        backbone_seq_onehot[:, :, 20] = 1  # 20 = 'X', mask all positions

        scores = []  # list to collect scores for each input sequence

        with torch.no_grad():
            # Run all three ensemble models to get amino acid probabilities
            aaprobs1 = runner.models[0].forward(X, seq_mask, backbone_seq_onehot)
            aaprobs2 = runner.models[1].forward(X, seq_mask, backbone_seq_onehot)
            aaprobs3 = runner.models[2].forward(X, seq_mask, backbone_seq_onehot)

            # Average logits from ensemble models
            aaprobs = (aaprobs1 + aaprobs2 + aaprobs3) / 3  # ensemble model predictions

            # Apply softmax to obtain amino acid probability distributions
            aaprobs = torch.nn.functional.softmax(aaprobs, dim=-1)

            # Only keep probabilities at valid sequence mask positions
            aaprobs = aaprobs[seq_mask]

            # Convert each input sequence to tensor of residue IDs on the runner device
            input_seqs = [
                torch.tensor([residue_constants.AA_TO_ID[aa] for aa in seq])
                .long()
                .to(runner.device)
                for seq in input_seqs
            ] #type: ignore

            # For each input sequence, calculate and collect the negative PLL score (log-likelihood under model)
            for sample in range(len(input_seqs)):
                input_seq_i = input_seqs[sample]
                _neg_pll, avg_neg_pll = get_neg_pll(aaprobs, input_seq_i)
                scores.append(-1 * avg_neg_pll)  # multiply by -1 to return PLL

        return scores  # return list of scores, one per input sequence

    def init_worker():
        thread_local.runner = Frame2seqRunner()

    def worker(name):
        runner = thread_local.runner # get existing runner 
        
        # create "rows of df" that will store results for this input
        rows = [
            {'name': name, 'mut': 'wt'},
            *[
                {'name': name, 'mut': mut}
                for mut in inputs[name]['mutants']
            ]
        ] #list of {'name', 'mut'} dicts

        # for each state
        for i, pdb in enumerate(inputs[name]['pdbs']):

            # score in batch
            scores = frame2seq_score(
                runner,
                pdb,
                [inputs[name]['wt']] + inputs[name]['mutant_seqs'],
                chain
            )

            # save wt score
            wt_score = scores[0]
            rows[0][f'frame2seq_pdb{i}'] = wt_score

            # save score
            for idx, mut in enumerate(inputs[name]['mutants']):
                rows[idx + 1][f'frame2seq_pdb{i}'] = (
                    scores[idx + 1] - wt_score
                )

        return rows

    # distribute and execute with each worker
    print('Scoring with ProteinMPNN ...')
    names = list(inputs) 
    with ThreadPoolExecutor(
        max_workers = max_workers,
        initializer = init_worker, #separate model each worker
    ) as executor:
        results = list(
            tqdm(
                executor.map(worker, names),
                total = len(names)
            )
        )

    # unpack one level of lists to create long df
    results = [
        row
        for result in results # each input
        for row in result # each mutant
    ]

    return pd.DataFrame(results)

#----Run Caliby
def caliby(
    inputs,
    model: str,
    max_workers: int,
    chain: str
):
    print('Initializing Caliby ...')
    from caliby import load_model
    import biotite.structure as struc
    import biotite.structure.io.pdb as pdbio

    # set threading
    thread_local = local()

    # init by loading model
    def init_worker():
        thread_local.caliby_model = load_model(
            model
        )
    
    # utility for writing pdb files
    def create_pdb(
        backbone,
        sequence: str,
        destpath: str
    ):
        # create new structure
        output = backbone.copy()

        # start of residue
        residue_starts = struc.get_residue_starts(output, add_exclusive_stop=True)
        assert (len(sequence) + 1) == len(residue_starts), f'Sequence is {len(sequence)} long, but structure is {len(residue_starts)} long for {destpath}'

        # annotate residue
        for i, one_letter in enumerate(sequence):
            three_letter = aa_code[one_letter.upper()]
            start = residue_starts[i]
            end = residue_starts[i + 1]
            output.res_name[start:end] = three_letter
        
        # write file
        strucio.save_structure(
            destpath,
            output
        )

    # prediction for one input
    def worker(name):
        caliby_model = thread_local.caliby_model

        # create "rows of df" that will store results for this input
        rows = [
            {'name': name, 'mut': 'wt'},
            *[
                {'name': name, 'mut': mut}
                for mut in inputs[name]['mutants']
            ]
        ] #list of {'name', 'mut'} dicts

        # create temp directory to write pdbs to
        with TemporaryDirectory(
            prefix=f'caliby_{name}',
            # create files in machine scratch to minimize file I/O time
            dir=os.environ.get("TMPDIR")
        ) as tmpdir:
                    
            # score for each state
            for i, pdb in enumerate(inputs[name]['pdbs']):

                # read structure
                backbone = strucio.load_structure(
                    pdb
                ) # assume single model

                # get desired chain only
                backbone = backbone[backbone.chain_id == chain] #type: ignore

                pdb_list = []
                # create files for all sequences
                for seq_i, sequence in enumerate(
                    [inputs[name]['wt']] + 
                    inputs[name]['mutant_seqs']
                ):
                    destpath = str(Path(
                        tmpdir,
                        f"seq{seq_i}.pdb"
                    ))
                    create_pdb(
                        backbone,
                        sequence,
                        destpath
                    )
                    pdb_list.append(
                        destpath
                    )
                
                # score as batch
                scores = caliby_model.score(
                    pdb_list
                )
                scores = pd.DataFrame(scores).set_index('example_id')

                # save wt score
                wt_score = float(scores.loc['seq0', 'U']) #type: ignore
                rows[0][f'caliby_pdb{i}'] = wt_score

                # subtract wt score
                scores = scores.drop('seq0')
                scores['U'] = scores['U'] - wt_score

                # parse batched results back into correct format
                for idx, mut in enumerate(inputs[name]['mutants']):
                    rows[idx + 1][f'caliby_pdb{i}'] = (
                        float(scores.loc[f'seq{idx + 1}', 'U']) #type: ignore
                    )

                # delete files
                for path in pdb_list:
                    Path(path).unlink()

            # return results
            return rows

    # distribute and execute each worker
    print('Scoring with Caliby ...')
    names = list(inputs)
    with ThreadPoolExecutor(
        max_workers = max_workers,
        initializer = init_worker,
    ) as executor:
        results = list(
            tqdm(
                executor.map(worker, names),
                total = len(names)
            )
        )

    # unpack one level of lists to create long df
    results = [
        row
        for result in results # each input
        for row in result # each mutant
    ]

    return pd.DataFrame(results)

if __name__ == "__main__":
    main()