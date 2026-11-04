import os
import sys
import subprocess

def main():
    # Fix PermissionError: [Errno 13] by unsetting the system-level SSLKEYLOGFILE variable
    # This must be done before streamlit is imported or launched
    env = os.environ.copy()
    env.pop('SSLKEYLOGFILE', None)
    
    print("Launching Metaheuristics Challenge...")
    try:
        # Launch streamlit using the current python interpreter
        cmd = [sys.executable, "-m", "streamlit", "run", "app.py"]
        # Pass any additional arguments through
        if len(sys.argv) > 1:
            cmd.extend(sys.argv[1:])
            
        subprocess.run(cmd, env=env)
    except Exception as e:
        print(f"Error launching app: {e}")

if __name__ == "__main__":
    main()
