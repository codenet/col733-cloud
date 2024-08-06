import pandas as pd
import sys

def split_csv(input_file, output_dir, num_files, rows_per_file=20000):
    # Read the CSV file into a DataFrame
    df = pd.read_csv(input_file)
    
    # Calculate the total number of rows
    total_rows = len(df)
    
    # Create smaller CSV files
    for i in range(num_files):
        start_row = i * rows_per_file
        end_row = min(start_row + rows_per_file, total_rows)
        
        # Slice the DataFrame
        df_slice = df.iloc[start_row:end_row]
        
        # Define the output filename
        output_file = f'{output_dir}/part_{i + 1}.csv'
        
        # Write the DataFrame slice to a new CSV file with the header
        df_slice.to_csv(output_file, index=False, header=True)
        
        print(f'Saved {output_file} with rows {start_row} to {end_row - 1}')

def main():
    if len(sys.argv) != 4:
        print("Usage: python split_csv.py <input_file> <output_dir> <num_files>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_dir = sys.argv[2]
    num_files = int(sys.argv[3])
    
    # Call the split_csv function with the provided arguments
    split_csv(input_file, output_dir, num_files)

if __name__ == "__main__":
    main()
