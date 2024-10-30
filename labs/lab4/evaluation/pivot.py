import pandas as pd
from pathlib import Path

# Directory where all entry_num.csv files are located
csv_dir = Path("/home/baadalvm/dev/col733-cloud/labs/lab4/evaluation/scores")

# Initialize an empty DataFrame to hold all data
combined_df = pd.DataFrame()

# Track all test names for consistent column ordering
all_test_names = set()

# Process each CSV file in the directory
for csv_file in csv_dir.glob("*.csv"):
    entry_num = csv_file.stem  # Get the entry_num from the file name (without '.csv')
    
    # Read the individual CSV file and clean up column names
    try:
        df = pd.read_csv(csv_file)
        df.columns = df.columns.str.strip()  # Remove any extra whitespace from column names
    except Exception as e:
        print(f"Error reading {csv_file}: {e}")
        continue
    
    # Check if required columns are present
    if "TestName" not in df.columns or "Output" not in df.columns:
        print(f"Skipping {csv_file}: Missing 'TestName' or 'Output' column")
        continue
    
    # Map 'Passed' to 1 and everything else to 0
    df["Output"] = df["Output"].apply(
        lambda x: 1 if str(x).strip().strip("'\"").lower() == 'passed' else 0
    )
    
    # Set the 'TestName' as index, convert 'Output' to a dictionary
    test_results = df.set_index("TestName")["Output"].to_dict()
    
    # Add entry_num to the results and collect all test names
    test_results["entry_num"] = entry_num
    all_test_names.update(test_results.keys())
    
    # Append results as a new row in combined_df
    combined_df = pd.concat([combined_df, pd.DataFrame([test_results])], ignore_index=True)

# Ensure all test names appear in the final DataFrame and are ordered
all_test_names.discard("entry_num")  # Remove entry_num from test names set
ordered_columns = ["entry_num"] + sorted(all_test_names)

# Reorder and fill missing values with 0 for tests not attempted by a student
combined_df = combined_df.reindex(columns=ordered_columns).fillna(0)
for column in ordered_columns[1:]:  # Skip 'entry_num'
    combined_df[column] = combined_df[column].astype(int)

# Save the combined DataFrame to a single CSV file
combined_df["Total"] = combined_df["test1"] + combined_df["test2"] + combined_df["test3"] + combined_df["test4"]
combined_df.to_csv("lab4-scores.csv", index=False)
print("Pivoted CSV file saved as 'lab4-scores.csv'")