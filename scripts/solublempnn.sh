#!/bin/bash
#$ -S /bin/bash
#$ -q short.q
#$ -cwd
#$ -N mpnn
#$ -o logs/mpnn/$JOB_ID.log
#$ -j y
#$ -l h_rt=00:15:00
#$ -l mem_free=16G
#$ -l scratch=1G

# metadata
echo "Start: $(date)"
[[ -n "$JOB_ID" ]] && qstat -j "$JOB_ID"
echo "------Start of script-------"
cat "$0"
echo "-------End of script---------"

# setup env
module load CBI miniforge3
conda activate ligandmpnn

# run
python ~/software/LigandMPNN/run.py \
    --model_type "soluble_mpnn" \
    --checkpoint_soluble_mpnn "$HOME/software/LigandMPNN/model_params/solublempnn_v_48_002.pt" \
    --pdb_path_multi "$HOME/multi-state/data/diffusion-output/5KPE-5KPH/pdb/missing.json" \
    --out_folder "$HOME/multi-state/data/mpnn-output/5KPE-5KPH_missing/" \
    --seed 42 \
    --temperature 0.1 \
    --omit_AA "CH" \
    --batch_size 1 \
    --number_of_batches 8 \
    --bias_AA 'A:-0.5'

#end
echo "End: $(date)"