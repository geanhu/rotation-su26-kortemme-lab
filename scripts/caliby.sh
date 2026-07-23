#!/bin/bash
#$ -S /bin/bash
#$ -q long.q
#$ -cwd
#$ -N caliby
#$ -o logs/caliby/$JOB_ID.log
#$ -j y
#$ -l h_rt=48:00:00
#$ -l mem_free=32G
#$ -l scratch=4G

# metadata
echo "Start: $(date)"
echo "$(hostname)"
[[ -n "$JOB_ID" ]] && qstat -j "$JOB_ID"
echo "------Start of script-------"
cat "$0"
echo ""
echo "-------End of script---------"

# setup env
cd '/wynton/home/rotation/geanhu/software/caliby'

# Load python version
module load CBI miniforge3/24.7.1-0

# Activate environment
ENV_DIR=/wynton/home/rotation/geanhu/software/caliby/envs  # set this to your environment directory
source ${ENV_DIR}/caliby/bin/activate

# Required for AtomWorks.
# We don't need these environment variables for our use case,
# but AtomWorks requires them to be set, so we set them to empty strings.
export PDB_MIRROR_PATH=""
export CCD_MIRROR_PATH=""

# Directory where model weights are stored. Weights are automatically
# downloaded from HuggingFace on first use.
export MODEL_PARAMS_DIR="/wynton/home/rotation/geanhu/software/caliby/model_params"

# run
python '/wynton/home/rotation/geanhu/software/caliby/caliby/eval/sampling/seq_des_ensemble.py' \
    ckpt_name_or_path=soluble_caliby \
    sampling_cfg_overrides.num_seqs_per_pdb=24 \
    sampling_cfg_overrides.batch_size=1 \
    seed=0 \
    max_num_conformers=10 \
    '++sampling_cfg_overrides.omit_aas=["C", "H"]' \
    ++sampling_cfg_overrides.potts_sampling_cfg.potts_temperature=0.01 \
    input_cfg.conformer_dir='/wynton/home/rotation/geanhu/multi-state/data/string-sampling/ensembles' \
    out_dir='/wynton/home/rotation/geanhu/multi-state/data/caliby-output/5KPE-5KPH/temp10-2'