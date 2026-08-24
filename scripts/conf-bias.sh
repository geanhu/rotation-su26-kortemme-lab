#!/bin/bash
#$ -S /bin/bash
#$ -q gpu.q
#$ -cwd
#$ -l compute_cap=61,gpu_mem=6000M
#$ -N conf-bias
#$ -o logs/conf-bias/$JOB_ID.log
#$ -j y
#$ -l h_rt=24:00:00
#$ -l mem_free=16G
#$ -l scratch=8G
#$ -l h=!qb3-idgpu18
#$ -pe smp 1

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
#export CUDA_VISIBLE_DEVICES=""

# enable GPU
export CUDA_VISIBLE_DEVICES=$SGE_GPU

# set local scratch
if [[ -z "$TMPDIR" ]]; then
  if [[ -d /scratch ]]; then TMPDIR=/scratch/$USER; else TMPDIR=/tmp/$USER; fi
  mkdir -p "$TMPDIR"
  export TMPDIR
fi

# for caliby
export PDB_MIRROR_PATH=""
export CCD_MIRROR_PATH=""
export MODEL_PARAMS_DIR="/wynton/home/rotation/geanhu/software/caliby/model_params"

# run
python ~/multi-state/scripts/utils/conformational-biasing.py \
    '/wynton/home/rotation/geanhu/multi-state/data/conf-bias-output/5KPE-5KPH/designs.json' \
    --caliby

#end
echo "End: $(date)"