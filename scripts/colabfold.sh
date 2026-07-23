#!/bin/bash
#$ -S /bin/bash
##$ -q gpu.q
##$ -pe smp 1
##$ -l compute_cap=80,gpu_mem=40G
#$ -cwd
#$ -N fold
#$ -o logs/colabfold/$JOB_ID.log
#$ -j y
#$ -l h_rt=72:00:00
#$ -l mem_free=64G
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

#export CUDA_VISIBLE_DEVICES=$SGE_GPU

# run
exec colabfold_batch \
    --num-recycle 3 \
    --msa-mode single_sequence \
    --random-seed 42 \
    --num-seeds 3 \
    $HOME/multi-state/data/mpnn-output/5KPE-5KPH_multi-state2/temp3/seqs/filtered-seqs.csv \
    $HOME/multi-state/data/colabfold-output/5KPE-5KPH_multi-state2/temp3/

# end
echo "End: $(date)"
echo "-----------"