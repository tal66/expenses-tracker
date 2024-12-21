import logging
from datetime import datetime

from expenses_tracker.config import Config
import os
from pathlib import Path
import google.generativeai as genai

config = Config()
DATA_DIR = config.data_folder
GEMINI_KEY = config.gemini['key']

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


def get_user_background():
    user_background_file = Path(DATA_DIR) / "user_background.txt"
    with open(user_background_file, 'r') as f:
        return f.read()


def get_user_expenses():
    if os.getenv('DEMO') == '1':
        logger.info("using demo files")
        files = list(Path(DATA_DIR).glob('*demo_expenses*.md'))
    else:
        files = list(Path(DATA_DIR).glob('*transactions*.md'))

    logger.info(f"found {len(files)} expenses files")
    return "\n\n".join([f"{Path(f).read_text()}" for f in files])


def get_user_insights(prompt="") -> Path or None:
    if os.getenv('DEMO') == '1':
        insights_file = Path(DATA_DIR) / "demo_insights.md"
        return insights_file
    else:
        if not GEMINI_KEY:
            logger.error("Gemini key not configured")
            return None
        genai.configure(api_key=GEMINI_KEY)

        model_str = "gemini-1.5-flash"
        model = genai.GenerativeModel(model_str)
        logger.info(f"generating content from gemini. model={model_str}")
        response = model.generate_content(prompt)

    print(response.text)

    insights_file = Path(DATA_DIR) / f"user_insights_gemini_{datetime.now().strftime("%d-%m-%Y, %H-%M")}.md"
    insights_file.write_text(response.text)
    logger.info(f"insights saved to {insights_file}")

    return insights_file


def get_prompt():
    expenses = get_user_expenses()
    if not expenses:
        logger.error("No expenses files found")
        exit(1)

    prompt = f"""You are helping the user to manage and get insights about their expenses.
User background:
{get_user_background()}

User expenses are credit card transactions from markdown files provided here:
{expenses}

Please read the user's background and understand the user's expenses. 
then provide insights in markdown format. be concise:
- What are the user's main expenses?
- Short recommendations
- Summary and any other insights you can provide
"""

    return prompt


if __name__ == "__main__":
    p = get_prompt()
    print(get_user_insights(p))
