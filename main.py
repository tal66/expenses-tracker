import subprocess
from pathlib import Path


if __name__ == '__main__':
    # streamlit run dashboard.py
    try:
        dashboard_path = Path(__file__).parent / "expenses_tracker/ui/dashboard.py"
        subprocess.run(
            ["streamlit", "run", dashboard_path],
            capture_output=False,
            text=True,
            shell=True
        )
    except Exception as e:
        print(f"failed to start streamlit: {e}")