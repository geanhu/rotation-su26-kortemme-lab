#!/bin/bash
#$ -S /bin/bash
#$ -q gpu.q
#$ -pe smp 1
#$ -l compute_cap=61,gpu_mem=6000M
#$ -cwd
#$ -N fold
#$ -o logs/af2ig/$JOB_ID.log
#$ -j y
#$ -l h_rt=12:00:00
#$ -l mem_free=64G
#$ -l scratch=8G
##$ -l h=!(qb3-idgpu18)

# metadata
echo "Start: $(date)"
echo "$(hostname)"
[[ -n "$JOB_ID" ]] && qstat -j "$JOB_ID"
echo "------Start of script-------"
cat "$0"
echo ""
echo "-------End of script---------"

export CUDA_VISIBLE_DEVICES=$SGE_GPU

# env
module load CBI miniforge3
conda activate af2_ig

# run
python '/wynton/home/rotation/geanhu/software/dl_binder_design/af2_initial_guess/predict.py' \
    -pdbdir '/wynton/home/rotation/geanhu/multi-state/data/mpnn-output/5KPE-5KPH_multi-state/temp3/separated' \
    -outpdbdir '/wynton/home/rotation/geanhu/multi-state/data/af2ig-output/5KPE-5KPH/temp3' \
    -force_monomer \
    -recycle 3 \
    -start_seed 42 \
    -num_seeds 5 \
    -debug