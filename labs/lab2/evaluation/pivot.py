import pandas as pd

# Load the CSV file
df = pd.read_csv("scores.csv")

# Pivot the data: set EntryNumber as index, test_case as columns, and score as values
pivot_df = df.pivot(index="entry_num", columns="test_case", values="score")

# Rename the columns to match the desired output
pivot_df.columns = [f"{col}_score" for col in pivot_df.columns]

# Reset the index to convert EntryNumber from index to column
pivot_df.reset_index(inplace=True)

pivot_df.fillna(0, inplace=True)

pivot_df["TotalScore"] = sum(
    [
        pivot_df[f"{col}_score"]
        for col in [
            "none",
            "reducer_once",
            "mapper_once",
            "test_all",
            "test_both",
            "test_mapper",
            "test_reducer",
        ]
    ]
)

# Save the reshaped DataFrame to a new CSV
pivot_df.to_csv("output.csv", index=False)

# Display the reshaped DataFrame (for checking purposes)
print(pivot_df)
