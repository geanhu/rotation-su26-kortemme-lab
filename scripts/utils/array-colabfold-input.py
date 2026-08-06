import argparse
from pathlib import Path
import math
#
import pandas as pd

def main():
    parser = argparse.ArgumentParser(
            description="Take .csv of batch colabfold inputs and divide into chunks of designated size for array job"
        )
    parser.add_argument(
        "input",
        type=str,
        help="Path to full .csv of sequence inputs"
    )
    parser.add_argument(
        "--chunk_size",
        type=int,
        default=150, # reduced from 200, since seems to time out on some nodes
        help='Maximum number of sequences to input per array job'
    )
    args = parser.parse_args()

    # read in df
    df = pd.read_csv(args.input)
    assert df['id'].is_unique, df[df['id'].duplicated()]

    # determine balanced batch size
    num_batches = math.ceil(len(df) / args.chunk_size)
    batch_size = math.ceil(len(df) / num_batches)

    # divide
    dfs = [df.iloc[i:i+batch_size] for i in range(0, len(df), batch_size)]

    # save
    paths = []
    for idx, df in enumerate(dfs):
        this_path = Path(
            Path(args.input).parent,
            f'{Path(args.input).stem}_batch{idx}.csv'
        )
        paths.append(str(this_path))
        df.to_csv(this_path, index=False)

    # save list of files
    file_list_path = Path(
        Path(args.input).parent,
        f'{Path(args.input).stem}_batches.txt'
    )
    with open(file_list_path, 'w') as file:
        for file_path in paths:
            file.write(file_path)
            file.write('\n')

    # print completed
    print(f'Created {len(paths)} batches of max size {max([len(df) for df in dfs])} with paths written to {file_list_path}')


if __name__ == "__main__":
    main()