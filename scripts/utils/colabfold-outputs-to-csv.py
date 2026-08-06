import argparse
from pathlib import Path
import orjson
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor
import os
#
import pandas as pd
import numpy as np

'''
NOTE: `orjson` used because base json module is disgustingly slow, but only slightly faster
'''
def process_file(item):
    # open file
    itemdata = orjson.loads(item.read_text())

    # parse scores
    try:
        return {
            'name': item.name.split('_scores_')[0],
            'seed': int(item.name.split('_seed_')[1].split('.')[0]),
            'model': int(item.name.split('_model_')[1].split('_')[0]),
            'plddt': np.mean(itemdata['plddt']),
            'ptm': np.mean(itemdata['ptm'])
        }
    except:
        print(f'Failed to parse metadata for {item.name}')
        raise

def main():
    parser = argparse.ArgumentParser(
        description="Take folder of colabfold outputs and compile scoring metrics to csv"
    )
    parser.add_argument(
        "input",
        type=str,
        help="Path to colabfold output folder"
    )
    args = parser.parse_args()

    # collect list of all files 
    files = [
        item for item in Path(args.input).iterdir() 
        if item.name.endswith('.json') and ('scores' in item.name)
    ]

    # distribute file opening
    try:
        max_workers = int(os.environ.get('NSLOTS', os.cpu_count())) #type: ignore
    except:
        max_workers = 4 # dev nodes gives each user 4 slots, presumably
    print(f'Using {max_workers} threads to process {len(files)} files')
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(tqdm(executor.map(
            process_file, files
        ), total=len(files), desc="Processing files"))

    '''
    Single thread execution
    # store data
    data = {
        'name': [],
        'seed': [],
        'model': [],
        'plddt': [],
        'ptm': []
    }
    
    # iterate through all output items
    for item in tqdm(list(Path(args.input).iterdir())):
        
        # get score files only
        if item.name.endswith('.json') and ('scores' in item.name):

            # open file
            itemdata = orjson.loads(item.read_text())
            # with base json module
            with open(item, 'r') as file:
                itemdata = json.load(file)
            
            # metadata
            try:
                data['name'].append(
                    item.name.split('_scores_')[0],
                )
                data['seed'].append(
                    int(item.name.split('_seed_')[1].split('.')[0])
                )
                data['model'].append(
                    int(item.name.split('_model_')[1].split('_')[0])
                )
            except:
                print(f'Failed to parse metadata for {item.name}')
                raise

            # plddt
            data['plddt'].append(
                np.mean(itemdata['plddt'])
            )

            # i?ptm
            data['ptm'].append(
                np.mean(itemdata['ptm'])
            )
    
    df = pd.DataFrame(data)
    '''
    
    # save
    df = pd.DataFrame(results)
    df.to_csv(
        f'{args.input}/scores.csv'
    )
    print(f'Wrote scores for {len(df)} structures to {args.input}/scores.csv')

if __name__ == "__main__":
    main()