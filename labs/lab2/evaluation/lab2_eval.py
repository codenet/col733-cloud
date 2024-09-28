import os
import signal
import zipfile
import csv
import subprocess
import shutil
import psutil
from collections import deque
from pathlib import Path
from redis import Redis
from datetime import datetime
from locations import submissions_folder, _coordinator_file, constants_file, main_file, seq_file, checker_script, csv_file, checkpoint_dir

from grade_log import Logger
logging = Logger().get_logger()

# DAG of test cases
"""
        reducer_once -> test_reducer
none ->                              -> test_both -> test_all
        mapper_once  -> test_mapper
"""
test_case_dag = {
    "none": ["reducer_once", "mapper_once"],
    "reducer_once": ["test_reducer"],
    "mapper_once": ["test_mapper"],
    "test_reducer": ["test_both"],
    "test_mapper": ["test_both"],
    "test_both": ["test_all"],
    "test_all": []
}
marks = {'none': 10, 'reducer_once': 2.5, 'mapper_once': 2.5, 'test_mapper': 5, 'test_reducer': 5, 'test_both': 5, 'test_all': 10}
timeouts = {'none': 50, 'reducer_once': 50, 'mapper_once': 50, 'test_mapper': 200, 'test_reducer': 200, 'test_both': 200, 'test_all': 200}


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

def run_test(main_py_path: str, test_case: str) -> int:
    logging.info(f"Running {test_case}")

    # Clear the checkpoint directory and Redis
    subprocess.run(["rm", "-rf", checkpoint_dir])
    rds = Redis(host='localhost', port=6379, password='', db=0, decode_responses=False)
    rds.flushall()

    command = ['python3.10', main_py_path, test_case]
    logging.critical(command)
    try:
        subprocess.run(command, timeout=timeouts[test_case], capture_output=True, text=True)
    except subprocess.TimeoutExpired:
        logging.critical(f"Timeout expired for {submission_folder} on test case {test_case}")
    except subprocess.CalledProcessError as e:
        logging.critical(f"CalledProcessError for {submission_folder} on test case {test_case}: {e}")
    except Exception as e:
        logging.critical(f"Error for {submission_folder} on test case {test_case}: {e}")

    # Run the checker script
    if not os.path.exists(checker_script):
        logging.error(f"checker.py not found for {submission_folder}")
        exit()


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

    return score



def write_score(entry_num, test_case, score, total_time):
     with open(csv_file, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([entry_num, test_case, score, total_time])


# Iterate over each submission zip
total_submissions = len([_ for _ in os.listdir(submissions_folder) if _.endswith('.zip')])
for i, file_name in enumerate(os.listdir(submissions_folder)):
    entry_num = file_name[:-4]
    kill_all()
    if not file_name.endswith('.zip'):
        logging.critical(f"Warning non-zip found: {file_name}")
        continue

    submission_folder = Path(f"/tmp/eval_{file_name[:-3]}")
    submission_folder.mkdir(exist_ok=True)

    logging.info(f"Evaluating {i}/{total_submissions} {file_name}")
    zip_file = submissions_folder / file_name 

    # Extract the zip file
    try:
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(submission_folder)
    except zipfile.BadZipFile:
        logging.critical(f"Bad zip file for {submission_folder}")
        continue

    # inject the files
    for file_path in [_coordinator_file, constants_file, checker_script, main_file, seq_file]:
        destination = submission_folder/os.path.basename(file_path)
        shutil.copy(file_path, destination)
    shutil.copy("locations.py", submission_folder / "locations.py")
    shutil.copy("assets/mylog.py", submission_folder / "mylog.py")
    
    main_py_path = os.path.join(submission_folder, 'main.py')
    if not os.path.exists(main_py_path):
        logging.critical(f"main.py not found for {submission_folder}")
        exit()

    test_results = {}

    queue = deque(["none"])
    while queue:
        node = queue.popleft()

        if node in test_results:
            continue

        kill_all()
        start_time = datetime.now()
        score = run_test(main_py_path, node)
        total_time = datetime.now() - start_time

        logging.info(f"Score for {submission_folder} on test case {node}: {score}")
        test_results[node] = score, total_time

        if score == 0:
            logging.critical(f"{node} failed, skipping its children...")
            continue

        for child in test_case_dag[node]:
            if child not in test_results:
                queue.append(child)

    # Write the results
    for test_name, result in test_results.items():
        write_score(entry_num, test_name, result[0], result[1])
