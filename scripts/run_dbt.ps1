# The script should stop if any command fails.
$ErrorActionPreference = "Stop"

# Define the path to the Python virtual environment.
$venv_path = ".\venv\Scripts\Activate.ps1"

# Activate the virtual environment.
. $venv_path

# Run the powershell script in .\scripts\source_env.ps1
. .\scripts\source_env.ps1

# Change the working directory to the dbt directory
Set-Location .\dbt

# Run the DBT command.
dbt run

# If there were no errors, print a success message.
if ($? -eq $True) {
    Write-Host "DBT run command has been successfully executed."
} else {
    Write-Host "There was an error executing the DBT run command."
}
