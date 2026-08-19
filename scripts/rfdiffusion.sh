#!/bin/bash
#$ -S /bin/bash
#$ -q short.q
#$ -pe smp 1
#$ -cwd
#$ -N diffusion
#$ -o logs/rfdiffusion/$JOB_ID.log
#$ -j y
#$ -l h_rt=00:30:00
#$ -l mem_free=16G
#$ -l scratch=16G
#$ -l h=!qb3-idgpu18
#$ -t 1-120

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
input_dir="/wynton/home/rotation/geanhu/multi-state/data/string-sampling/5KPH-4a"
pdb_list="${input_dir}/5KPH.txt"
if [ ! -f "$pdb_list" ]; then
    find "$input_dir" -type f -name "5KPH*.pdb" | sort > "$pdb_list"
fi
PDB_FILE=$(sed -n "${SGE_TASK_ID}p" "$pdb_list")

# run
python ~/software/RFdiffusion/scripts/run_inference.py \
    inference.num_designs=1 \
    diffuser.partial_T=1 \
    'contigmap.contigs=[72-72]' \
    "inference.input_pdb=$PDB_FILE" \
    "inference.output_prefix=$HOME/multi-state/data/diffusion-output/5KPH-4a/$(basename $PDB_FILE .pdb)"

#end
echo "End: $(date)"
echo "-----------"