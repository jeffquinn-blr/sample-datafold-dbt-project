# sample-datafold-dbt-project

## Developer Setup

### On OSX or Linux

1. Install `python3.11` on your computer, this is the version of python used on this project. Ensure it is available on the `PATH` as `python3.10`
2. Clone this repository: `git clone https://github.com/Big-Little-Robots-Org/sample-datafold-dbt-project.git`
3. `cd sample-datafold-dbt-project`
4. Create virtualenv for development: `make venv`
5. Setup pre-commit hooks (auto format all code on every commit) - `make .git/hooks/pre-commit`
6. Setup your `.env` file by running `cp .env_template .env`, and filling out all the blank entries
in the template. This file will include your passwords etc. and should not be checked into git.
When you are done, run `source .env` or run `.\scripts\source_env.ps1` if on windows.

### On Windows

1. Install `python3.11` on your computer, this is the version of python used on this project.
2. Run powershell and enter a powershell terminal
3. Clone this repository: `git clone https://github.com/Big-Little-Robots-Org/sample-datafold-dbt-project.git`
4. `cd claims_engine`
5. Create virtualenv and precommit hooks for development: `.\scripts\setup.ps1`
6. Setup your `.env` file by running `cp .env_template .env`, and filling out all the blank entries
in the template. This file will include your passwords etc. and should not be checked into git.
When you are done, run `.\scripts\source_env.ps1`.

## Running DBT

This repository uses a wrapper around `dbt` in `scripts/dbt.py`

To run dbt, execute `python script/dbt.py run`.

This script has the following command line options:

```
usage: dbt.py run [-h] [--selection SELECTION]

options:
  -h, --help            show this help message and exit
  --selection SELECTION
```

`--repository-root` should be the full path to the root of the repository. If this flag is not provided,
the current working directory will be used.

`--selection` will be threaded through to the dbt `--select` option. If this is not provided,
"state:modified+" will be used by default, which means all models that have been modified since the last run
and their dependents will be modified.

After running `scripts/dbt.py` the dbt state will be saved in the `dbt/state` directory. The directory structure will
be setup as follows: `dbt/state/<snowflake account>/<db name>/<schema name>`

You should commit these changes after each run and push them to `main`, especially if you are running on prod
data.

### DBT Environment Variables

You *must* setup your .env file yourself.

Anytime any of the code in this repository needs to connect to snowflake,
it will use the username/password/database/etc. defined in the .env file.

You must "source" the env file to activate it, see [Developer Setup](#developer-setup) for more information.
You can think of this as "logging in".

If you have different snowflake instances you want to use, for example separate "DEV" and "PROD"
databases, you need to make different .env files for each one. You can then source the correct
`.env` file before running dbt to point to the correct instance.

Do not check your `.env` file into github, it contains the password.
It is in the `.gitignore` file to make it harder for you to accidentally check into github

### DBT State Files

Please read the documentation about the state method in DBT.

https://docs.getdbt.com/reference/node-selection/methods#the-state-method

This project template, and the dbt wrapper, enforce that state files will be used
for all dbt runs.

DBT state files will be organized in the `state` directory under `dbt`. Further subdirectories
will be created for each DBT database/schema that the project is run against.

It is up to the user to make sure the files that are created in that directory are commited
and pushed to github.

The purpose of using these state files and pushing them to github is that it allows multiple
users working on a dbt project to synchronize.

For example:

Alice creates a new model X. She runs the new model in the prod environment,
and commits the updated state file for that environment to github.

Bob pulls Alice's latest changes and then creates a new model Y that depends on X.
He runs the new model in the prod environment. DBT will determine from reading the
state file in the state file X has already been run,
and it will skip needing to run the queries to create model X again.

Without state files Bob would need to guess if he needs to run X again or not, most of the time
he would probably need to just run it again to be safe. This is a waste of DBT cost.


### EXPLAINing DBT Queries

When debugging a model that is taking a long time, you should inspect the EXPLAIN statement. You can use
`python script/dbt.py explain` to explain the query behind any model.

```
usage: dbt.py explain [-h] --model MODEL

options:
  -h, --help     show this help message and exit
  --model MODEL
```

See https://docs.snowflake.com/en/sql-reference/sql/explain.html for more information on EXPLAIN.


## Project Structure

### Python

All python scripts are in a python package under `src/claims_engine`.

Any python script which is intended to be called from the command line should have an entry
in `[project.scripts]` in the `src/claims_engine/pyproject.toml` file. This will allow the script to be
called from the command line.

For instance an entry like this:

```toml
[project.scripts]
ydata_profiler_reports = "claims_engine.ydata_profiler:main"
```

Means that the `main()` method defined in `chobani/ydata_profiler.py` can be called from the command line
using the command `ydata_profiler_reports`

All "actions" are defined in the `Makefile`. If you are creating a new script to run,
etc., you should also make a new `Makefile` entry for it so that other developers can easily
discover it.

#### Python UDFs

Python UDFs are defined in `dbt/macros` but the python code for the udf is in `src/claims_engine`.

When defining a new macro that defines a UDF you can insert `!!<path to python sourcefile relative to root of repo>!!`.
The `dbt.py` script will automatically interpolate in the correct python sourcefile before running dbt.

You also must add all macros that define UDFs to the `dbt/macros/create_udfs.sql`. This ensures they are refreshed
on each dbt run.

### SQL

The claims_engine dbt project is under `dbt/claims_engine`

Please see the [README.md](dbt/README.md) in that directory for more information.

## CI/CD

This project uses Github Actions for CI/CD.

The CI/CD pipelines are defined under `.github/workflows`.

The current workflows are:
`.github/workflows/black.yml`: checks that python code is formatted correctly
`.github/workflows/sqlfluff.yml`: checks that SQL code is formatted correctly
`.github/workflows/dbt.yml`: Runs dbt models and dbt tests

These workflows will trigger every time a new pull request is created, and subsequently any time an
update is made to that pull request.

## Pre-commit Hooks

This project also uses pre-commit hooks. These run on the client side and will autoformat
your SQL/Python/etc files every time you run `git commit`. If autoformatting is not needed,
git commit will succeed. If autoformatting is needed, the source files will change and a failure
will be printed to the screen. The failure looks like this:

```commandline
(venv) (base) Jeffs-MBP:dbt jeffquinn$ git commit -a -m "minimal requirement set"
Trim Trailing Whitespace.................................................Passed
Fix End of Files.........................................................Failed
- hook id: end-of-file-fixer
- exit code: 1
- files were modified by this hook

Fixing requirements-dbt.txt

Check for merge conflicts................................................Passed
black................................................(no files to check)Skipped
sqlfluff-fix.........................................(no files to check)Skipped
```

When you have a `Failed` action, you will need to re-run the same `git commit` command.
Pre-commit will not let the commit action go through until all the checks pass. This keeps
the git history clean of tiny formatting changes.

If you see output like this

```
(venv) (base) Jeffs-MBP:dbt jeffquinn$ git commit -a -m "minimal requirement set"
Trim Trailing Whitespace.................................................Passed
Fix End of Files.........................................................Passed
Check for merge conflicts................................................Passed
black................................................(no files to check)Skipped
sqlfluff-fix.........................................(no files to check)Skipped
[jq_improve_fact_hourly_state 9fa555a] minimal requirement set
 3 files changed, 2 insertions(+), 1 deletion(-)
 create mode 100644 requirements-dbt.txt
 rename requirements.txt => requirements-dev.txt (100%)
```

It means all the checks passed and your commit is accepted.

So in practice, you'll need to get used to running `git commit` multiple times in a row, it's
a little weird but that's just how it has to work.

## SQLFluff

This project uses SQLFluff to lint SQL code.
SQLFluff is a linter and also an autoformatter.

A linter is a program that checks your code for errors. It will not change your code, it will
only tell you if there are errors.

An autoformatter is a program that automatically formats your code to a standard format.
It will change your code.


To run SQLFluff as a linter, run

```
sqlfluff lint
```

To run SQLFluff as an autoformatter, run

```
sqlfluff fix
```

SQLFluff does very in depth checking of SQL code, this means it can take some time,
 please be patient.

*SQLFluff needs an active snowflake connection to run*.

The only way it can check if your SQL runs is if it has access to a live snowflake instance.
By default it is configured to use the whatever snowflake instance is specified in your
.env file. It will not change any data in this instance, it will just check that all your
SQL syntax will work in that particular instance.


## Black Python Formatting

This project uses [black](https://github.com/psf/black) to autoformat python code. All `.py` files will be autoformatted
by the precommit hooks. Github actions will validate that all `.py` files are correctly
formatted.

To run black manually, run `black .` from the root of the repository.