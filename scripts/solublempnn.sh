#!/bin/bash
#$ -S /bin/bash
#$ -q long.q
#$ -cwd
#$ -N mpnn
#$ -o logs/mpnn/$JOB_ID.log
#$ -j y
#$ -l h_rt=03:00:00
#$ -l mem_free=16G
#$ -l scratch=1G

# metadata
echo "Start: $(date)"
echo "$(hostname)"
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
    --pdb_path_multi "$HOME/multi-state/data/diffusion-output/5KPE-5KPH/filtered/5KPE-5KPH-filtered_combined.json" \
    --out_folder "$HOME/multi-state/data/mpnn-output/5KPE-5KPH_multi-state2/temp3" \
    --seed 45 \
    --temperature 0.3 \
    --omit_AA "CH" \
    --batch_size 1 \
    --number_of_batches 24 \
    --bias_AA 'A:-0.5,E:-0.25' \
    --homo_oligomer 1

#end
echo "End: $(date)"