from pathlib import Path
import zipfile
import subprocess
import sys
from io import StringIO
import unittest
import shutil


SUBMISSION_DIR = Path(".")
SCORES_DIR = Path("scores")
SCORES_DIR.mkdir(exist_ok=True)
BASE_PATH = Path("base")


def copy_base(to: Path):
    if to.exists():
        shutil.rmtree(to)
    shutil.copytree(BASE_PATH, to)


def evaluate_test():
    test_mod = __import__("test_all")


    # Run the test module
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(test_mod)

    test_names = set()
    for test in suite:
        for subtest in test:
            test_names.add(str(subtest._testMethodName))

    # print(test_names)

    old_stdout = sys.stdout
    sys.stdout = StringIO()
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2, failfast=False).run(suite)
    sys.stdout = old_stdout

    
    failure_tests = set([
        str(test[0]._testMethodName)
        for test in result.failures
    ])
    # print(failure_tests)

    error_tests = set([
        str(test[0]._testMethodName)
        for test in result.errors
    ])
    # print(error_tests)

    skipped_tests = set([
        str(test[0]._testMethodName)
        for test in result.skipped
    ])
    # print(skipped_tests)

    passing_tests = test_names - failure_tests - error_tests - skipped_tests

    return passing_tests


def evaluate(sub_zip: Path):
    entry_num = sub_zip.name[:-4]
    print(f"Evaluating {sub_zip}")
    extract_dir = Path("/tmp") / f"eval_l4_{entry_num}"

    copy_base(extract_dir)

    try:
        with zipfile.ZipFile(sub_zip, "r") as zip_ref:
            zip_ref.extractall(extract_dir)
    except zipfile.BadZipFile:
        print(f"Bad zip file for {sub_zip}")
        return 0

    # Install the student's submission
    try:
        # Run 'pip install .' to install the student's project
        subprocess.check_call(
            [sys.executable, "-m", "pip", "uninstall", "-y", "bayou"], cwd=extract_dir
        )
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "."], cwd=extract_dir
        )
        print(f"Project installed successfully from {extract_dir}")
    except subprocess.CalledProcessError as e:
        print(f"Error during installation: {e}")
        sys.exit(1)

    print("Starting Evaluation. Logs will be silent during evaluation...")
    passing_tests = evaluate_test()
    print("Evaluation Complete")

    with open(Path("scores") / f"{entry_num}.csv", mode="w", newline="") as file:
        file.write("TestName, Output\n")
        for test in passing_tests:
            file.write(f"{test}, 'Passed'\n")
        file.flush()
    print("Wrote Scores in file")


if __name__ == "__main__":
    assert Path(sys.argv[1]).exists()
    evaluate(Path(sys.argv[1]))
