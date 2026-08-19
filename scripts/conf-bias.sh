#!/bin/bash
#$ -S /bin/bash
#$ -q long.q
#$ -cwd
#$ -N conf-bias
#$ -o logs/conf-bias/$JOB_ID.log
#$ -j y
#$ -l h_rt=08:00:00
#$ -l mem_free=8G
#$ -l scratch=1G
#$ -pe smp 4

# metadata
echo "Start: $(date)"
echo "$(hostname)"
[[ -n "$JOB_ID" ]] && qstat -j "$JOB_ID"
echo "------Start of script-------"
cat "$0"
echo "-------End of script---------"

# setup env
module purge
module load CBI miniforge3
conda activate conf-bias

# disable GPU
export CUDA_VISIBLE_DEVICES=""

# run
python ~/multi-state/scripts/utils/conformational-biasing.py \
    '/wynton/home/rotation/geanhu/multi-state/data/conf-bias-output/5KPE-5KPH/designs.json' \
    --proteinmpnn

#end
echo "End: $(date)"