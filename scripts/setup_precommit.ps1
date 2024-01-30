# Set the working directory to the script's directory
Set-Location -Path $PSScriptRoot

cd ..

# Activate the virtual environment
. .\venv\Scripts\activate

pip install pre-commit
pre-commit install
