#!/bin/bash
#$ -S /bin/bash
#$ -q gpu.q
#$ -pe smp 1
#$ -l compute_cap=61,gpu_mem=6000M
#$ -cwd
#$ -N fold
#$ -o logs/colabfold/$JOB_ID.log
#$ -j y
#$ -l h_rt=01:55:00
#$ -l mem_free=64G
#$ -l scratch=32G
#$ -l h=!qb3-idgpu18

# metadata
echo "Start: $(date)"
echo "$(hostname)"
[[ -n "$JOB_ID" ]] && qstat -j "$JOB_ID"
echo "------Start of script-------"
cat "$0"
echo ""
echo "-------End of script---------"

export CUDA_VISIBLE_DEVICES=$SGE_GPU

# run
exec colabfold_batch \
    --num-recycle 3 \
    --msa-mode single_sequence \
    --random-seed 42 \
    --num-seeds 3 \
    /wynton/home/rotation/geanhu/multi-state/data/mpnn-output/5KPE-5KPH_refined_multi-state3/temp1/incomplete-seqs2.csv \
    /wynton/home/rotation/geanhu/multi-state/data/colabfold-output/5KPE-5KPH_refined_multi-state3/temp1/

# end
echo "End: $(date)"
echo "-----------"