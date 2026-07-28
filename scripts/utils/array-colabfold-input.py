import argparse
from pathlib import Path
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
        default=200,
        help='Sequences to input per array job'
    )
    parser.add_argument(
        "--new_chunk_threshold",
        type=int,
        default=25,
        help='Sequences needed to separate into new chunk, otherwise appends to existing (i.e. upper limit of seqs/job - chunk size)'
    )
    args = parser.parse_args()

    # read in df
    df = pd.read_csv(args.input)
    assert df['id'].is_unique, df[df['id'].duplicated()]

    # divide
    dfs = [df.iloc[i:i+args.chunk_size] for i in range(0, len(df), args.chunk_size)]

    # handle last chunk
    if len(dfs[-1]) < args.new_chunk_threshold:
        dfs[-2] = pd.concat([dfs[-2], dfs[-1]])
        dfs = dfs[:-1] #remove last element

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
    print(f'Created {len(paths)} batches of max size {max(len(dfs[-2]), len(dfs[-1]))} with paths written to {file_list_path}')


if __name__ == "__main__":
    main()