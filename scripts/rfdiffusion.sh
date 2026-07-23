#!/bin/bash
#$ -S /bin/bash
#$ -q gpu.q
#$ -pe smp 1
#$ -l compute_cap=80,gpu_mem=40G
#$ -cwd
#$ -N diffusion
#$ -o logs/rfdiffusion/$JOB_ID.log
#$ -j y
#$ -l h_rt=00:30:00
#$ -l mem_free=32G
#$ -l scratch=32G
#$ -l h=!qb3-idgpu18
#$ -t 1-10

# metadata
echo "Start: $(date)"
echo "$(hostname)"
[[ -n "$JOB_ID" ]] && qstat -j "$JOB_ID"
echo "------Start of script-------"
cat "$0"
echo ""
echo "-------End of script---------"

export CUDA_VISIBLE_DEVICES=$SGE_GPU

# setup env
module load CBI miniforge3
conda activate SE3nv

# # create array job settings
input_dir="$HOME/multi-state/data/string-sampling/end-states/"

if (( $SGE_TASK_ID <= 3 )); then
    pdb_list="${input_dir}/5kph-missing.txt"
    PDB_FILE=$(sed -n "${SGE_TASK_ID}p" "$pdb_list")

    # run
    python ~/software/RFdiffusion/scripts/run_inference.py \
        inference.num_designs=1 \
        diffuser.partial_T=1 \
        'contigmap.contigs=[72-72]' \
        "inference.input_pdb=$PDB_FILE" \
        "inference.output_prefix=$HOME/multi-state/data/diffusion-output/5KPE-5KPH/$(basename $PDB_FILE .pdb)"
elif (( $SGE_TASK_ID > 3 )); then
    pdb_list="${input_dir}/5kpe-missing.txt"
    PDB_FILE=$(sed -n "$((SGE_TASK_ID - 3))p" "$pdb_list")

    python ~/software/RFdiffusion/scripts/run_inference.py \
        inference.num_designs=1 \
        diffuser.partial_T=1 \
        'contigmap.contigs=[108-108]' \
        "inference.input_pdb=$PDB_FILE" \
        "inference.output_prefix=$HOME/multi-state/data/diffusion-output/5KPE-5KPH/$(basename $PDB_FILE .pdb)"
fi

#end
echo "End: $(date)"
echo "-----------"