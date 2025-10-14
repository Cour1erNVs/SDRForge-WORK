import subprocess
import sys
from setuptools import setup

def install_sdrforge():
    """
    Runs the necessary setup commands, providing text feedback instead of a spinner.
    """
    
    # --- 1. Update package list ---
    command = ["sudo", "apt", "update", "-y"]
    message = "Updating package list..."
    
    print(f"\n[START] {message}")
    
    try:
        # Run the command. The output is captured but will be visible if the 
        # CI runner decides to display subprocess output on error.
        subprocess.run(
            command, 
            check=True, # Raise CalledProcessError for non-zero exit codes
            # Removed stdout/stderr capture so the system output is handled by the runner
        )
        
        # Command succeeded
        print(f"[SUCCESS] {message}")
        
    except subprocess.CalledProcessError as e:
        # Command failed
        print(f"[FAILURE] {message}")
        
        # Print the command output error for debugging
        if e.stderr:
            sys.stderr.write(f"\nError details (stderr):\n{e.stderr.decode()}\n")
        if e.stdout:
            sys.stderr.write(f"\nError details (stdout):\n{e.stdout.decode()}\n")
            
        sys.exit(1) # Exit with a failure code
        
    # --- 2. Final Message ---
    MAGENTA = '\033[35m'
    RESET = '\033[0m'

    print(f"\n{MAGENTA}SDRForge Finished Installing! 🎉{RESET}")
    print("Next suggested step:")
    print("sudo apt-get install gnuradio")


# Define the setup entry point
setup(
    name='SDRForge',
    # Since we are not creating releases, the version is optional here
    # version='1.0.0',
)

if __name__ == "__main__":
    # Note: When pip installs the package, it executes this block after requirements are checked.
    # By running the setup logic here, it acts as a post-installation script.
    install_sdrforge()
