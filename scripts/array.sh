# create array job settings
input_dir="$HOME/multi-state/data/string-sampling/end-states"
pdb_list="${input_dir}/5kph.txt"

echo $input_dir
echo $pdb_list

if [ ! -f "$pdb_list" ]; then
    find "$input_dir" -type f -name "5KPH*.pdb" | sort > "$pdb_list"
fi