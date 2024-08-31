## How to run
1. Make sure redis server is up and running on port 6379.
2. Make sure you have Python3.10
3. `pip install -r requirements.txt` to install the Python requirements.
4. Run `python generator.py` to generate bunch of csv files in `csv_files` directory.
5. `python main.py [none | test_reducer | test_mapper | test_both | test_all]` to run the system.

Enabling `test_reducer`/`test_mapper` will periodically crash some
reducer/mapper while the system is running. `test_both` will periodically crash
both of them. `test_all` will periodically crash all the workers. `none` will
crash none of them.

You can test your implementation, using `checker.py`. It basically compares the
final checkpoints of both the reducers with the sequential word count. Make sure
to run `seq.py` before running checker. 

### Evaluation
We will test the correctness of the implementation by checking the final
checkpoint files made by the reducers (Reducer_0_0.txt and Reducer_1_0.txt).
The final checkpoint files (with checkpoint_id = 0) should match the sequential
word count.

We will test this against a set of randomly generated csv_files of arbitrary
volume, with and without worker failures.  We will run several tests and in each
test, we will periodically crash one or more reducers/ mappers (same Reducer /
Mapper could be crashed multiple times).

* Correctness without workers failure: 10 marks 
* Correctness with workers failure: 30 marks

### Submission

* Don't make any changes to `main.py` and `_coordinator.py`. We will change them
  during evaluation.
* Don't change any naming conventions that are already being used in the starter
  code.
* Make sure to test your code on Baadal before submitting. The evaluation would
  be done on Baadal VM.
* Run `./zip.sh <entry_num>` to generate the zip file. 
* Submit the generated zip file on Moodle.
