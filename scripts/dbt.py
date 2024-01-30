import glob
import subprocess
import argparse
import os
import logging
import json
import datetime
import snowflake.connector
import pandas

logger = logging.getLogger(__name__)

RUN_RESULTS_FILE = "run_results.json"
MANIFEST_FILE = "manifest.json"


def get_args():
    # parse args
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", "-r", type=str, default=os.getcwd())

    # add run subcommand
    subparsers = parser.add_subparsers(help="choose run or explain", dest="command")
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--selection", type=str, default="state:modified+")

    # add explain subcommand
    explain_parser = subparsers.add_parser("explain")
    explain_parser.add_argument("--model", type=str, required=True)

    return parser.parse_args()


def get_current_config_values():
    schema = os.environ["DBT_SCHEMA"]
    database = os.environ["DBT_DATABASE"]
    account = os.environ["DBT_SNOWFLAKE_ACCOUNT"]
    user = os.environ["DBT_USER"]
    password = os.environ["DBT_PASSWORD"]
    warehouse = os.environ["DBT_WAREHOUSE"]
    role = os.environ["DBT_ROLE"]

    return {
        "schema": schema,
        "database": database,
        "account": account,
        "user": user,
        "password": password,
        "warehouse": warehouse,
        "role": role,
    }


def get_snowflake_connection():
    config_values = get_current_config_values()
    return snowflake.connector.connect(
        user=config_values["user"],
        password=config_values["password"],
        account=config_values["account"],
        warehouse=config_values["warehouse"],
        database=config_values["database"],
        schema=config_values["schema"],
        role=config_values["role"],
    )


def get_state_dir(repository_root):
    config_values = get_current_config_values()
    state_path = os.path.join(
        "dbt",
        "state",
        config_values["account"],
        config_values["database"],
        config_values["schema"],
    )
    return os.path.join(repository_root, state_path)


def call_dbt_run(
        repository_root,
        selection="state:modified+",
        profiles_dir="profiles",
        state_path=None,
):
    """
    Run dbt and pipe stderr and stdout to screen
    """
    cmd = ["dbt", "run", "-x", "--profiles-dir", profiles_dir]

    if state_path:
        cmd.extend(["--state", state_path])

    if selection:
        cmd.extend(["--select", selection])

    logger.info(
        "Running dbt with the following command: {}".format(" ".join(cmd))
    )

    subprocess.run(
        cmd,
        check=True,
        cwd=os.path.join(repository_root, "dbt"),
    )


def call_dbt_compile(
        repository_root,
        profiles_dir="profiles",
):
    """
    Run dbt and pipe stderr and stdout to screen
    """
    cmd = ["dbt", "compile", "--profiles-dir", profiles_dir]

    subprocess.run(
        cmd,
        check=True,
        cwd=os.path.join(repository_root, "dbt"),
    )


def get_compiled_query_for_model(model_name, repository_root):
    models_dir = os.path.join(repository_root, "dbt", "target", "compiled")

    for root, dirs, files in os.walk(models_dir):
        for file in files:
            if file == f"{model_name}.sql":
                # return file contents as string
                with open(os.path.join(root, file), "r") as f:
                    return f.read()

    raise ValueError(f"Could not find model {model_name} in {models_dir}")


def run_explain_query(query_string):
    con = get_snowflake_connection()
    try:
        # Create a cursor object
        cur = con.cursor()

        try:
            cur.execute("EXPLAIN " + query_string)
            all_rows = cur.fetchall()
            field_names = [i[0] for i in cur.description]
            df = pandas.DataFrame(all_rows)
            df.columns = field_names

            logger.info("Query plan:")
            # print pandas DF with no truncation
            with pandas.option_context("display.max_rows",
                                       None,
                                       "display.max_columns",
                                       None):
                print(df)

        finally:
            cur.close()

    finally:
        con.close()


def explain_model(model_name, repository_root, profiles_dir="profiles"):
    call_dbt_compile(repository_root, profiles_dir=profiles_dir)
    query_string = get_compiled_query_for_model(model_name, repository_root)
    run_explain_query(query_string)


def copy_python_code(repository_root):
    """
    iterate through all files in dbt/macros and replace any string
    of the form !!<filepath>!! with the contents of that file.
    Edit the files inplace
    """
    for macro_fn in glob.glob(os.path.join(repository_root, "dbt", "macros", "*.sql")):
        with open(macro_fn, "r") as f:
            macro = f.read()
        for line in macro.split("\n"):
            if line.startswith("!!"):
                # strip ! from line
                fn = line.strip().strip("!")
                with open(os.path.join(repository_root, fn), "r") as f:
                    replacement = f.read()
                macro = macro.replace(line, replacement)
        with open(macro_fn, "w") as f:
            f.write(macro)


def get_last_git_editor(fn, repository_root):
    """
    By calling git in a subprocess, get the name of the last person
    to edit the file fn
    """
    return subprocess.run(
        ["git", "log", "-1", "--pretty=format:%an", fn],
        capture_output=True,
        check=True,
        cwd=repository_root,
    ).stdout.decode("utf-8")


def add_file_git(fn, repository_root):
    """
    By calling git in a subprocess, add a new file
    """
    subprocess.run(["git", "add", fn], check=True, cwd=repository_root)


def reset_files_git(fn, repository_root):
    """
    By calling git in a subprocess, add a new file
    """
    subprocess.run(["git", "checkout", "--", fn], check=True, cwd=repository_root)


def format_float_seconds(seconds):
    """
    Format float seconds as a human-readable string HH:MM:SS
    """
    return str(datetime.timedelta(seconds=float(seconds)))


def print_last_results(previous_run_results):
    """
    given a dbt run results file, iterate through it and log
    the total run time as well as an ordered list of the models
    by runtime
    """
    with open(previous_run_results, "r") as f:
        run_results = json.load(f)

    logger.info("Info about the last time this project was run:")
    logger.info(
        "Total run time: {}".format(format_float_seconds(run_results["elapsed_time"]))
    )
    logger.info("Models updated during last run and execution time:")
    for model in sorted(
            run_results["results"], key=lambda x: x["execution_time"], reverse=True
    ):
        logger.info(
            "{:40} {}".format(
                model["unique_id"], format_float_seconds(model["execution_time"])
            )
        )


def copy_state_files(repository_root):
    state_dir = get_state_dir(repository_root)
    if not os.path.exists(state_dir):
        os.makedirs(state_dir)
    with open(os.path.join("dbt", "target", "manifest.json"), "r") as f:
        manifest = f.read()
    with open(os.path.join(state_dir, MANIFEST_FILE), "w") as f:
        f.write(manifest)
    with open(os.path.join("dbt", "target", "run_results.json"), "r") as f:
        run_results = f.read()
    with open(os.path.join(state_dir, RUN_RESULTS_FILE), "w") as f:
        f.write(run_results)


def log_last_run(repository_root):
    state_dir = get_state_dir(repository_root)

    if os.path.exists(os.path.join(state_dir, MANIFEST_FILE)):
        last_editor = get_last_git_editor(
            os.path.join(state_dir, MANIFEST_FILE), repository_root
        )
        logger.info("Last user to run dbt on this database: {}".format(last_editor))
    if os.path.exists(os.path.join(state_dir, RUN_RESULTS_FILE)):
        print_last_results(os.path.join(state_dir, RUN_RESULTS_FILE))


def prompt_user_to_continue():
    """
    Prompt the user to continue. If the user enters 'y', return True.
    Otherwise, return False
    """
    while True:
        response = input("Continue? (y/n) ")
        if response.lower() == "y":
            return True
        elif response.lower() == "n":
            return False
        else:
            print("Invalid response. Please enter 'y' or 'n'")


def main():
    setup_logging()
    args = get_args()
    repository_root = args.repository_root
    state_dir = get_state_dir(repository_root)
    logger.info(f"Using config values: {get_current_config_values()}")
    logger.info(f"Using args: {args}")
    if args.command == "explain":
        explain_model(args.model, repository_root)
    elif args.command == "run":
        copy_python_code(repository_root)

        if os.path.exists(state_dir):
            log_last_run(repository_root)
            state_dir_for_run = state_dir
        else:
            state_dir_for_run = None
            logger.info("No previous state file found. Running dbt from scratch")

        if prompt_user_to_continue():
            call_dbt_run(
                repository_root,
                state_path=state_dir_for_run,
                selection=args.selection
            )
        else:
            reset_files_git(
                fn=os.path.join(repository_root, "dbt", "macros"),
                repository_root=repository_root,
            )
            return

        copy_state_files(repository_root)
        add_file_git(state_dir, repository_root)

        # Reset the interpolation
        reset_files_git(
            fn=os.path.join(repository_root, "dbt", "macros"),
            repository_root=repository_root,
        )


def setup_logging():
    _logger = logging.getLogger(__name__)
    # configure logger
    _logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    _logger.addHandler(ch)
    # add formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)


if __name__ == "__main__":
    main()
