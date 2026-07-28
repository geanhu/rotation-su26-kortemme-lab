#!/bin/bash
#$ -S /bin/bash
#$ -q gpu.q
#$ -pe smp 1
#$ -l compute_cap=80,gpu_mem=40G
#$ -cwd
#$ -N fold-array
#$ -o logs/colabfold/$JOB_ID.log
#$ -j y
#$ -l h_rt=01:59:59
#$ -l mem_free=64G
#$ -l scratch=16G
#$ -l h=!qb3-idgpu18
#$ -t 1-21

# metadata
echo "Start: $(date)"
echo "$(hostname)"
[[ -n "$JOB_ID" ]] && qstat -j "$JOB_ID"
echo "------Start of script-------"
cat "$0"
echo ""
echo "-------End of script---------"

export CUDA_VISIBLE_DEVICES=$SGE_GPU

# array job
batch_list="/wynton/home/rotation/geanhu/multi-state/data/caliby-output/5KPE-5KPH/temp10-2/filtered_seqs_batches.txt"
BATCH_FILE=$(sed -n "${SGE_TASK_ID}p" "$batch_list")

# run
exec colabfold_batch \
    --num-recycle 3 \
    --msa-mode single_sequence \
    --random-seed 42 \
    --num-seeds 3 \
    "$BATCH_FILE" \
    /wynton/home/rotation/geanhu/multi-state/data/colabfold-output/5KPE-5KPH_caliby_multi-state/temp10-2/

# end
echo "End: $(date)"
echo "-----------"