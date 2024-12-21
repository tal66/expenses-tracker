import logging
import os
import subprocess
import sys
from pathlib import Path

from expenses_tracker.ai.gemini import get_user_insights
from expenses_tracker.config import Config
from expenses_tracker.credit_cards.get_max_visa_files import login_and_download_from_max
from expenses_tracker.data_process import process_credit_files

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

config = Config()


def run_ui():
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


if __name__ == '__main__':

    # os.environ['DEMO'] = '1'
    if ((len(sys.argv) == 2) and (sys.argv[1] == 'demo')) or os.getenv('DEMO'):
        os.environ['DEMO'] = '1'
        logger.info("demo mode")

        excel_files = list(Path(config.data_folder).glob('demo*.xlsx'))
        for file in excel_files:
            process_credit_files.to_markdown(str(file))

        run_ui()
    else:
        # download from MAX
        max_creds = config.max_credentials
        excel_files = login_and_download_from_max(max_creds['username'], max_creds['password'])

        # convert to md
        for file in excel_files:
            process_credit_files.to_markdown(file)

        # gemini
        insights_file = get_user_insights()

        run_ui()
