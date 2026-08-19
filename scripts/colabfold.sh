#!/bin/bash
#$ -S /bin/bash
#$ -q long.q
#$ -pe smp 1
##$ -l compute_cap=61,gpu_mem=6000M
#$ -cwd
#$ -N fold
#$ -o logs/colabfold/$JOB_ID.log
#$ -j y
#$ -l h_rt=20:00:00
#$ -l mem_free=16G
#$ -l scratch=16G
#$ -l h=!qb3-idgpu18

# metadata
echo "Start: $(date)"
echo "$(hostname)"
[[ -n "$JOB_ID" ]] && qstat -j "$JOB_ID"
echo "------Start of script-------"
cat "$0"
echo ""
echo "-------End of script---------"

# disable GPU
export CUDA_VISIBLE_DEVICES=""

# run
exec colabfold_batch \
    --num-recycle 3 \
    --msa-mode single_sequence \
    --random-seed 42 \
    --num-seeds 1 \
    /wynton/home/rotation/geanhu/multi-state/notebooks/data/mutants/5KPE-5KPH_2a.csv \
    /wynton/home/rotation/geanhu/multi-state/data/colabfold-output/5KPE-5KPH_mutants/2a/

# end
echo "End: $(date)"
echo "-----------"