import os
import signal
import zipfile
import csv
import subprocess
import shutil
import psutil
from pathlib import Path
from redis import Redis
from datetime import datetime
from locations import submissions_folder, _coordinator_file, constants_file, main_file, seq_file, checker_script, csv_file, checkpoint_dir

from grade_log import Logger
logging = Logger().get_logger()

# List of test cases
test_cases = ['none', 'once', 'test_mapper', 'test_reducer', 'test_both', 'test_all']
marks = {'none': 10, 'once': 5, 'test_mapper': 5, 'test_reducer': 5, 'test_both': 5, 'test_all': 10}
timeouts = {'none': 50, 'once': 50, 'test_mapper': 200, 'test_reducer': 200, 'test_both': 200, 'test_all': 200}


def kill_all():
    p_2_kill = set()
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            # Check if the process name contains 'python'
            if 'python' in proc.info['name']:
                p_2_kill.add(proc.info['pid'])
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    p_2_kill.remove(os.getpid())

    for p in p_2_kill:
        try:
            os.kill(p, signal.SIGKILL)
        except:
            pass

# Iterate over each submission zip
total_submissions = len([_ for _ in os.listdir(submissions_folder) if _.endswith('.zip')])
for i, file_name in enumerate(os.listdir(submissions_folder)):
    kill_all()
    #if i%2==0:
    #    logging.warning(f"Skipping {i}")
    #    continue
    if not file_name.endswith('.zip'):
        logging.critical(f"Warning non-zip found: {file_name}")
        # print("Warning non-zip found")
        continue

    submission_folder = Path(f"/tmp/eval_{file_name[:-3]}")
    submission_folder.mkdir(exist_ok=True)

    logging.info(f"Evaluating {i}/{total_submissions} {file_name}")
    # print(f"Evaluating {i}/{total_submissions} {file_name}")
    zip_file = submissions_folder / file_name 

    # Extract the zip file
    try:
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(submission_folder)
    except zipfile.BadZipFile:
        logging.critical(f"Bad zip file for {submission_folder}")
        # print(f"Bad zip file for {submission_folder}")
        continue

    # inject the files
    for file_path in [_coordinator_file, constants_file, checker_script, main_file, seq_file]:
        destination = submission_folder/os.path.basename(file_path)
        shutil.copy(file_path, destination)
    shutil.copy("locations.py", submission_folder / "locations.py")
    shutil.copy("assets/mylog.py", submission_folder / "mylog.py")
    
    main_py_path = os.path.join(submission_folder, 'main.py')
    if not os.path.exists(main_py_path):
        # print(f"main.py not found for {submission_folder}")
        logging.critical(f"main.py not found for {submission_folder}")
        exit()

    # Run the test cases
    for test_case in test_cases:
        logging.info(f"Running {test_case}")
        # print(f"Running {test_case}")

        # Clear the checkpoint directory and Redis
        subprocess.run(["rm", "-rf", checkpoint_dir])
        rds = Redis(host='localhost', port=6379, password='', db=0, decode_responses=False)
        rds.flushall()

        command = ['python3.10', main_py_path, test_case]
        start_time = datetime.now()
        try:
            subprocess.run(command, timeout=timeouts[test_case], capture_output=True, text=True)
        except subprocess.TimeoutExpired:
            logging.critical(f"Timeout expired for {submission_folder} on test case {test_case}")
            # print(f"Timeout expired for {submission_folder} on test case {test_case}")
        except subprocess.CalledProcessError as e:
            logging.critical(f"CalledProcessError for {submission_folder} on test case {test_case}: {e}")
            # print(f"CalledProcessError for {submission_folder} on test case {test_case}: {e}")
        except Exception as e:
            logging.critical(f"Error for {submission_folder} on test case {test_case}: {e}")
            # print(f"Error for {submission_folder} on test case {test_case}: {e}")

        # Run the checker script
        if not os.path.exists(checker_script):
            logging.error(f"checker.py not found for {submission_folder}")
            exit()

        total_time = datetime.now() - start_time

        checker_command = ['python3.10', checker_script, checkpoint_dir, seq_file]
        checker_result = subprocess.run(checker_command, capture_output=True, text=True)

        subprocess.run(["rm", "-rf", checkpoint_dir])

        # Calculate the score
        output = checker_result.stdout.strip()
        logging.info(f"Output for {submission_folder} on test case {test_case}: {output}")
        if output == "CORRECT":
            score = marks[test_case]
        elif output == "INCORRECT":
            score = 0
        elif output == "NOSEQ":  # this should not happen. it means seq.txt not present.
            score = -1
        else:
            score = 0

        # Write the score to the CSV file
        logging.info(f"Score for {submission_folder} on test case {test_case}: {score}")
        # Open the CSV file in write mode
        with open(csv_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([file_name[:-3], test_case, score, total_time])

        if test_case in ['none', 'once', 'test_reducer', 'test_both', 'test_all']:
            if score == 0:
                kill_all()
                logging.warning(f"Skipping rest of the test. If '{test_case}' one is not working, rest will not work")
                break

        kill_all()
