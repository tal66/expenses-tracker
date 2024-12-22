import logging
import os
import time
from datetime import datetime

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
            page.goto("https://www.max.co.il/", wait_until="domcontentloaded")

            # personal area button
            page.wait_for_selector("span:has-text('כניסה לאיזור האישי')", timeout=5_000)
            page.locator("span:has-text('כניסה לאיזור האישי')").click()

            page.locator("a#login-password-link").click()

            # fill in the login form
            logger.info(f"logging in...")
            page.locator("input#user-name").fill(username)
            page.locator("input#password").fill(password)
            logger.info(f"filled in login form")
            page.get_by_text("לכניסה לאזור האישי").click()

            # Wait
            page.wait_for_selector("li.all-actions", timeout=7_000)
            logger.info(f"logged in")

            # popup may appear
            close_button = page.locator("button.close[aria-label='סגירה']")
            logger.debug(f"close_button.count(): {close_button.count()}")
            if close_button.count() > 0:
                try:
                    close_button.first.click()
                    logger.info(f"closed start message")
                except Exception as e:
                    # ignoring errors for popup close (works for me)
                    logger.error(e)

            page.wait_for_load_state("domcontentloaded")

            # click "פעולות" in the menu
            page.locator("li.all-actions > a:has-text('פעולות')").click()
            # page.wait_for_selector("div.all-actions-popup", state="visible")
            logger.info(f"clicked on 'פעולות'")

            # wait for menu "פירוט החיובים והעסקאות"
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
                f = download_month(page, num_months_offset=i, selected_month_index=selected_month_idx)
                downloaded_files.append(f)
                # website bug: current month is last on purpose
                # (it downloads partial file if pressing first on current month)

        except Exception as e:
            logger.exception(e)

        finally:
            time.sleep(7)  # keep browser open for debugging
            browser.close()
            return downloaded_files


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


def download_month(page: Page, num_months_offset: int = 1, selected_month_index=None):
    """num_months_offset could be negative (previous months) or positive"""

    # open dates menu
    page.locator("div.combo-text.dates").click()
    month_items = page.locator("li.month").all()

    if selected_month_index is None:
        selected_month_index = get_selected_month_index(page)

    logger.debug(f"selected_month_index: {selected_month_index}")

    if (selected_month_index is not None) and (selected_month_index > 0):
        selected_month_index = selected_month_index + num_months_offset

        target_month = month_items[selected_month_index]
        target_month_text = target_month.text_content().strip()
        target_month.click()
        logger.info(f"month: '{target_month_text}'")

        page.wait_for_load_state("networkidle")

        return download_transactions_for_month(page, target_month_text)

    return None


def download_transactions_for_month(page: Page, month_text: str):
    """download transactions for a specific month"""
    logger.debug(f"download_transactions_for_month '{month_text}'")

    page.wait_for_load_state("networkidle", timeout=5_000)

    with page.expect_download(timeout=18_000) as download_info:
        print_excel_div = page.locator("div.print-excel")
        excel_button = print_excel_div.locator("span.download-excel")
        logger.info(f"click excel export button..")
        page.wait_for_timeout(1000)
        # page.mouse.click(btn_position['x'], btn_position['y'], click_count=1)
        excel_button.hover()
        excel_button.click()

        page.wait_for_load_state("networkidle", timeout=5_000)
        download = download_info.value
        filename = f"transactions_{month_text}.xlsx"
        target_path = f"{DOWNLOADS_DIR}/{filename}"

        if os.path.exists(target_path):
            timestamp = datetime.now().strftime("%H%M%S")
            new_filename = f"transactions_{month_text}_{timestamp}.xlsx"
            target_path = f"{DOWNLOADS_DIR}/{new_filename}"
            logger.info(f"file already exists. saving as: {new_filename}")

        download.save_as(target_path)

    logger.info(f"excel file downloaded: {filename}")
    return target_path


if __name__ == "__main__":
    username = config.max_credentials['username']
    password = config.max_credentials['password']

    if (not password) or (not username):
        logger.error("in project config: set username and password")
        exit(1)

    downloaded_files = login_and_download_from_max(username, password)
    logger.info(f"downloaded {len(downloaded_files)} files: {downloaded_files}")
