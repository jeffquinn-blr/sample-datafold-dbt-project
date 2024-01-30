# Set the working directory to the script's directory
Set-Location -Path $PSScriptRoot

cd ..

# Create a new virtual environment named 'venv'
python -m venv venv

# Activate the virtual environment
. .\venv\Scripts\Activate.ps1

# Upgrade pip
pip install --upgrade pip

# Install the desired packages
pip install -e ".[test,dev]"
pip install -r requirements-dbt.txt

# Execute setup_precommit.ps1
. .\scripts\setup_precommit.ps1
