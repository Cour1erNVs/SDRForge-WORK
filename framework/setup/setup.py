import subprocess
import sys
from halo import Halo
from setuptools import setup

def install_lteforge():
    """
    Runs the necessary setup commands with a blue 'dots' spinner using halo.
    """
    
    # --- 1. Update package list (The original 'sudo apt update -y' command) ---
    command = ["sudo", "apt", "update", "-y"]
    message = "Updating package list..."
    
    # Create the Halo spinner, set text, color, and spinner type
    spinner = Halo(
        text=message, 
        spinner='dots', 
        color='blue' # Set the spinner color to blue
    )
    
    # Start the spinner animation
    spinner.start()
    
    try:
        # Run the command. Output is captured to keep the console clean for the spinner.
        subprocess.run(
            command, 
            check=True, # Raise CalledProcessError for non-zero exit codes
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        
        # Command succeeded
        spinner.succeed(message)
        
    except subprocess.CalledProcessError as e:
        # Command failed
        spinner.fail(f"{message} (Failed)")
        # Optionally print the error output for debugging
        sys.stderr.write(f"\nError details:\n{e.stderr.decode()}\n")
        sys.exit(1) # Exit with a failure code
        
    # --- 2. Final Message ---
    # The original script's final message
    MAGENTA = '\033[35m'
    RESET = '\033[0m'

    print(f"\n{MAGENTA}SDRForge Finished Installing! 🎉{RESET}")
    print("Next suggested step:")
    print("sudo apt-get install gnuradio")


# Define the setup entry point
setup(
    name='SDRForge',
    version='1.0.0',
    # We use a custom command execution here instead of a typical entry point
    # Since this is primarily a shell script wrapper, a standard 'install_requires' 
    # and using the 'pyproject.toml' for build requirements is sufficient.
)

if __name__ == "__main__":
    install_lteforge()
