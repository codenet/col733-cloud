from pathlib import Path


root_dir = Path("/home/baadalvm/lab2_evaluation")

# Path to the folder containing all the submission directories
submissions_folder = root_dir / Path('submissions')

# Path to the files that need to be injected into the submission folder
_coordinator_file = root_dir / Path('assets/_coordinator.py')
constants_file = root_dir / Path('assets/constants.py')
main_file = root_dir / Path('assets/main.py')

# Path to the sequential wc file
seq_file = root_dir / Path('assets/seq.txt')

# Path to the checker script
checker_script = root_dir / Path('assets/checker.py')

# Path to the CSV file to store the scores
csv_file = root_dir / Path('scores.csv')

# Path to the checkpoint directory
checkpoint_dir = root_dir / Path('checkpoints')

# where to generate the csv files using generator
input_path = root_dir / Path('csv_files')
