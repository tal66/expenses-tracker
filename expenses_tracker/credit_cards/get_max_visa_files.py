import logging
import os
import re
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import pypdf
from playwright.sync_api import sync_playwright, Page

from expenses_tracker.config import Config

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

########

config = Config()
DOWNLOADS_DIR = config.data_folder

if not DOWNLOADS_DIR:
    DOWNLOADS_DIR = './data'
if not os.path.exists(DOWNLOADS_DIR):
    os.makedirs(DOWNLOADS_DIR)  # raises if exists

logger.info(f"Downloads folder: {DOWNLOADS_DIR}")

MONTHS_OFFSETS_TO_DOWNLOAD = [-2, -1, 0]

MONTHS_HEB_TO_NUM = {
    "ינואר": "01", "פברואר": "02", "מרץ": "03", "אפריל": "04",
    "מאי": "05", "יוני": "06", "יולי": "07", "אוגוסט": "08",
    "ספטמבר": "09", "אוקטובר": "10", "נובמבר": "11", "דצמבר": "12",
}

URL = "https://www.max.co.il/"


########

def login_and_download_from_max(username: str, password: str):
    downloaded_files = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            accept_downloads=True,
            service_workers="block"
        )
        page = context.new_page()

        try:
            logger.info(f"open page...")
            page.goto(URL, wait_until="domcontentloaded")

            # menu איזור אישי
            page.wait_for_selector("span:has-text('כניסה לאיזור האישי')", timeout=5_000)
            page.locator("span:has-text('כניסה לאיזור האישי')").click()
            # sub menu לקוחות פרטיים
            page.wait_for_selector("span:has-text('לקוחות פרטיים')", timeout=5_000)
            page.locator("span:has-text('לקוחות פרטיים')").click()

            # fill in login form
            page.locator("a#login-password-link").click()
            logger.info(f"logging in...")
            page.locator("input#user-name").fill(username)
            page.locator("input#password").fill(password)
            logger.info(f"filled in login form")
            page.get_by_text("לכניסה לאזור האישי").click()

            page.wait_for_selector("li.all-actions", timeout=7_000)
            logger.info(f"logged in")

            # (note: decided to handle unexpected popups, if any, manually)

            page.wait_for_load_state("domcontentloaded")

            # download excel
            download_excel_files(page, downloaded_files)
            # display excel sum
            for f in downloaded_files:
                if f.endswith('.xlsx'):
                    get_excel_sums(f)

            # pdf
            download_pdf_files(page, downloaded_files)
            compare_excel_to_pdf(downloaded_files)

        except Exception as e:
            logger.exception(e)

        finally:
            sec = 10
            logger.info(f"closing browser in {sec} sec...")
            time.sleep(sec)  # keep browser open for debugging
            browser.close()
            return downloaded_files


def download_excel_files(page, downloaded_files):
    # menu "פעולות"
    page.locator("li.all-actions > a:has-text('פעולות')").click()
    # page.wait_for_selector("div.all-actions-popup", state="visible")
    logger.info(f"clicked on 'פעולות'")

    # menu "פירוט החיובים והעסקאות"
    all_links = page.get_by_text("פירוט החיובים והעסקאות").all()
    if len(all_links) >= 2:
        all_links[1].click()
    else:
        all_links[0].click()
    logger.info(f"clicked on 'פירוט החיובים והעסקאות'")

    page.wait_for_load_state("domcontentloaded")

    current_month = page.locator("div.combo-text.dates").text_content().strip()
    logger.info(f"current_month: '{current_month}'")

    selected_month_idx = get_selected_month_index(page)

    for i in MONTHS_OFFSETS_TO_DOWNLOAD:
        page.wait_for_load_state("domcontentloaded")
        f = download_excel_for_month(page, months_offset=i,
                                     selected_month_index=selected_month_idx)
        downloaded_files.append(f)
        # website bug: current month is last on purpose
        # (it downloads partial file if pressing first on current month)


def download_excel_for_month(page: Page, months_offset: int = -1, selected_month_index=None):
    """num_months_offset could be negative (previous months) or positive"""
    if selected_month_index is None:
        selected_month_index = get_selected_month_index(page)

    # open dates menu
    page.locator("div.combo-text.dates").click()
    month_items = page.locator("li.month").all()

    logger.debug(f"selected_month_index: {selected_month_index}")

    if (selected_month_index is not None) and (selected_month_index > 0):
        selected_month_index = selected_month_index + months_offset

        logger.debug(f"clicking month {selected_month_index} from menu")
        target_month = month_items[selected_month_index]
        target_month_text_heb = target_month.text_content().strip()
        target_month.click()
        logger.info(f"clicked month {selected_month_index} from menu")

        target_month_text = format_month(target_month_text_heb)
        logger.info(f"month: '{target_month_text_heb}' '{target_month_text}'")

        # page.wait_for_load_state("networkidle")

        ext = "xlsx"
        out_filename = f"transactions_{target_month_text}.{ext}"
        if months_offset > 0:
            out_filename = f"{Path(out_filename).stem}_future{Path(out_filename).suffix}"

        # page.wait_for_load_state("domcontentloaded", timeout=5_000)
        page.wait_for_load_state("networkidle")
        print_excel_div = page.locator("div.print-excel")
        excel_button = print_excel_div.locator("span.download-excel")

        logger.info(f"start download process for {out_filename}")
        return click_download(excel_button, out_filename, page)

    return None


def click_download(download_btn, out_filename, page: Page) -> str:
    """click btn and save file. return downloaded file path"""
    with page.expect_download(timeout=22_000) as download_info:
        page.wait_for_timeout(500)
        download_btn.hover()
        page.wait_for_timeout(500)
        download_btn.click()
        logger.info(f"clicked on download button")
        page.wait_for_timeout(500)

        out_filepath = Path(DOWNLOADS_DIR) / out_filename
        if os.path.exists(out_filepath):
            timestamp = datetime.now().strftime("%H%M%S")
            new_filename = Path(out_filename).stem + f"_{timestamp}{Path(out_filename).suffix}"
            out_filepath = Path(DOWNLOADS_DIR) / new_filename
            logger.info(f"file already exists. saving as: {new_filename}")

        logger.debug(f"before download_info.value")
        download = download_info.value
        download.save_as(out_filepath)

    logger.info(f"file downloaded: {out_filepath}")
    return str(out_filepath)


def get_excel_sums(f):
    excel_sum_col = 5  # 6th column 'סכום חיוב'
    excel_df = pd.read_excel(f, sheet_name=[0, 1])

    excel_sums = []
    for i in range(2):
        sheet = excel_df[i]
        s = 0
        for val in sheet.iloc[:, excel_sum_col]:
            if type(val) in [int, float] and not pd.isna(val):
                num = float(val)
                s += num
        s = round(s, 2)
        excel_sums.append(s)

    f_name = Path(f).name
    logger.info(f"{f_name}: {sum(excel_sums):,} = {excel_sums}")
    return excel_sums


#### pdf

def download_pdf_files(page: Page, downloaded_files):
    # "פעולות" menu
    page.locator("li.all-actions > a:has-text('פעולות')").click()
    # page.wait_for_selector("div.all-actions-popup", state="visible")
    logger.info(f"clicked on 'פעולות'")

    # menu "דפי הפירוט והמכתבים"
    menu_target_text = "דפי הפירוט והמכתבים"
    all_links = page.get_by_text(menu_target_text).all()
    if len(all_links) >= 2:
        all_links[1].click()
    else:
        all_links[0].click()
    logger.info(f"clicked on 'דפי הפירוט והמכתבים'")

    page.wait_for_load_state("domcontentloaded")

    dates_menu = page.locator("div.combo-text.dates")
    selected_month_idx = get_selected_month_index(page)
    logger.info(f"selected_month_idx in pdf menu: {selected_month_idx}")

    for i in MONTHS_OFFSETS_TO_DOWNLOAD:
        if i > 0:
            continue
        month_idx = selected_month_idx + i
        page.locator("div.combo-text.dates").click()
        month_items = page.locator("li.month").all()
        month_items[month_idx].click()
        page.wait_for_load_state("domcontentloaded")
        curr_month_text = dates_menu.text_content().strip()
        logger.info(f"selected {curr_month_text}")

        curr_month_elements = page.query_selector_all(f':text("{curr_month_text}")')
        month_second_el = curr_month_elements[1]
        month_second_el.hover()
        logger.info(f"hovered {curr_month_text}")

        download_button = page.locator('a:has-text("להורדה")')

        month_text = format_month(curr_month_text)
        filename = f"{month_text}.pdf"
        logger.info(f"start download process for {filename}")

        out_filepath = click_download(download_button, filename, page)
        downloaded_files.append(out_filepath)


#### util

def get_selected_month_index(page: Page, month_items=None):
    # find index of selected month

    if month_items is None:
        page.locator("div.combo-text.dates").click()
        month_items = page.locator("li.month").all()

    selected_month_index = None
    for i, item in enumerate(month_items):
        if "selected-month" in item.get_attribute("class"):
            selected_month_index = i
            logger.debug(f"selected_month_index: {selected_month_index}")

            # click on the selected month to close the menu
            target_month = month_items[selected_month_index]
            target_month.click()
            break

    return selected_month_index


def format_month(month_str: str) -> str:
    """convert for example 'דצמבר 2024' to '2024-12'"""
    month, year = month_str.split()
    month_num = MONTHS_HEB_TO_NUM[month]
    return f"{year}-{month_num}"


def compare_excel_to_pdf(downloaded_files, allowed_diff=0.01):
    filtered_files = [f for f in downloaded_files if "future" not in f]
    pdfs = [f for f in filtered_files if f.endswith(".pdf")]
    excels = [f for f in filtered_files if f.endswith(".xlsx")]

    for pdf_file in pdfs:
        pdf_file_name = Path(pdf_file).stem
        try:
            pdf_sums = get_pdf_sums(pdf_file)
            pdf_sums.sort()
        except Exception as e:
            logger.exception(e)
            continue

        # lookup dddd-dd
        match = re.search(r"\d{4}-\d{2}", pdf_file_name)
        if match:
            yyyy_mm = match.group()
            excel_files_match = [f for f in excels if (yyyy_mm in f)]
            logging.debug(f"pdf: '{pdf_file}', match excel_files: {excel_files_match}")
            for f in excel_files_match:  # supposed to be just one file, but anyway
                if not os.path.exists(f):
                    logger.warning(f"{f} not found")
                    continue

                logger.info(f"comparing {pdf_file} to {f}")
                excel_sums = get_excel_sums(f)
                logger.debug(f"pdf: {pdf_sums}, excel: {excel_sums}")

                # cmp
                excel_sums.sort()
                sums_ok = True
                for i in range(len(pdf_sums)):
                    if i >= len(excel_sums):
                        logger.warning(f"pdf: {pdf_sums[i]}, excel: missing")
                        break
                    if abs(pdf_sums[i] - excel_sums[i]) > allowed_diff:
                        logger.warning(f"pdf: {pdf_sums[i]}, excel: {excel_sums[i]}")
                        sums_ok = False

                if sums_ok:
                    logger.info(f"sums OK")


def get_pdf_sums(pdf_file) -> list:
    reader = pypdf.PdfReader(pdf_file)
    num_pages = len(reader.pages)
    texts = []
    for i in range(num_pages):
        page = reader.pages[i]
        text = page.extract_text()
        texts.append(text)
    text = "\n".join(texts)

    lines = text.splitlines()
    pdf_sums = []
    for i in range(len(lines)):
        line = lines[i]
        if ("חיובים" in line) and ("בתאריך" in line):
            sum_line = lines[i + 2]
            sum = sum_line.replace(",", "")
            sum = float(sum)
            pdf_sums.append(sum)
    return pdf_sums


if __name__ == "__main__":
    username = config.max_credentials['username']
    password = config.max_credentials['password']

    if (not password) or (not username):
        logger.error("in project config: set username and password")
        exit(1)

    downloaded_files = login_and_download_from_max(username, password)
    logger.info(f"downloaded {len(downloaded_files)} files: {downloaded_files}")
