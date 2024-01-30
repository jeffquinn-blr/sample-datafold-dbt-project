# Set the working directory to the script's directory
Set-Location -Path $PSScriptRoot
# Move up one directory level
cd ..

# File path for .env file
$envFilePath = ".\.env"

# Read the content of the .env file
$content = Get-Content -Path $envFilePath

foreach ($line in $content) {
    # Strip out empty lines or lines that start with a #
    if (-Not [string]::IsNullOrWhiteSpace($line) -and $line[0] -ne '#') {
        # Split the line on the equals sign
        $split = $line -split '=', 2

        # Get the key and value
        $key = $split[0].Trim()
        $value = $split[1].Trim()

        # Remove prefix 'export ' from the key if it exists
        if ($key.StartsWith("export ")) {
            $key = $key.Substring(7)
        }

        # If the value is wrapped in quotes, remove them
        if ($value[0] -eq '"' -and $value[-1] -eq '"') {
            $value = $value.Substring(1, $value.Length - 2)
        }

        # Set the environment variable
        [Environment]::SetEnvironmentVariable($key, $value, "Process")
    }
}
