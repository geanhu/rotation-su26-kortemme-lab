import argparse
from pathlib import Path
import orjson
from tqdm import tqdm
#
import pandas as pd
import numpy as np

'''
NOTE: `orjson` used because base json module is disgustingly slow, but only slightly faster
'''
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

    # store data
    data = {
        'name': [],
        'rank': [],
        'plddt': [],
        'ptm': []
    }
    
    # iterate through all output items
    for item in tqdm(list(Path(args.input).iterdir())):
        
        # get score files only
        if item.name.endswith('.json') and ('scores' in item.name):

            # open file
            itemdata = orjson.loads(item.read_text())
            '''
            with open(item, 'r') as file:
                itemdata = json.load(file)
            '''
            
            # metadata
            data['name'].append(
                item.name.split('_scores')[0],
            )
            data['rank'].append(
                int(item.name.split('_rank_')[1].split('_')[0])
            )

            # plddt
            data['plddt'].append(
                np.mean(itemdata['plddt'])
            )

            # i?ptm
            data['ptm'].append(
                np.mean(itemdata['ptm'])
            )
    
    # save
    df = pd.DataFrame(data)
    df.to_csv(
        f'{args.input}/scores.csv'
    )
    print(f'Wrote scores for {len(df)} structures to {args.input}/scores.csv')

if __name__ == "__main__":
    main()