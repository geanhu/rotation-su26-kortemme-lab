#!/bin/bash
#$ -S /bin/bash
#$ -q short.q
#$ -cwd
#$ -N multi
#$ -o logs/misc/$JOB_ID.log
#$ -j y
#$ -l h_rt=00:30:00
#$ -l mem_free=8G
#$ -l scratch=1G
#$ -pe smp 8

# metadata
echo "Start: $(date)"
echo "$(hostname)"
[[ -n "$JOB_ID" ]] && qstat -j "$JOB_ID"
echo "------Start of script-------"
cat "$0"
echo "-------End of script---------"

# setup env
module load CBI miniforge3
conda activate analysis

# run
python ~/multi-state/scripts/utils/rmsd-score.py \
    '/wynton/home/rotation/geanhu/multi-state/data/colabfold-output/5KPE-5KPH_multi-state/temp2/rmsd_paths_end.json' \
    --mode "CA"

#end
echo "End: $(date)"