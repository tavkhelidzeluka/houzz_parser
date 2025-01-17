import json
import logging
import multiprocessing
import logging
import time
from concurrent.futures import as_completed
from concurrent.futures.process import ProcessPoolExecutor
from concurrent.futures.thread import ThreadPoolExecutor


from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from settings import (
    CONTRACTOR_PARSER_MAX_WORKERS,
    GATHERER_THREAD_MAX_WORKERS,
    ELEMENT_FIND_TIMEOUT,
    PAGE_COUNT,
    ITEM_PER_PAGE,
    PAGE_RETRY_COUNT, OUTPUT_FILE,
)
from driver_pool import WebDriverPool
from contractor_parser import run_contractors_parser


def gather_links(driver: webdriver.Chrome, url: str) -> list:
    logging.info(f'Gathering links from: {url}')

    driver.get(url)

    radius_field = WebDriverWait(driver, ELEMENT_FIND_TIMEOUT).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, '[data-component="Radius"'))
    )

    logging.info(f'Radius Text: {radius_field.text}')
    if radius_field.text != 'Anywhere':
        logging.info('Radius is not set to anywhere')
        # set filters
        radius_field.click()
        anywhere_location_button = WebDriverWait(driver, ELEMENT_FIND_TIMEOUT).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '#hui-menu-1-item-4'))
        )
        anywhere_location_button.click()
        # driver.execute_script("arguments[0].click();", anywhere_location_button)
        logging.info('Set location to anywhere')
        if driver.current_url != url:
            driver.get(url)


    contractor_items = WebDriverWait(driver, ELEMENT_FIND_TIMEOUT).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, '.hz-pro-search-results__item'))
    )
    page_num = WebDriverWait(driver, ELEMENT_FIND_TIMEOUT).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, '.hz-pagination-link--selected'))
    ).text

    expected_page_num = url.split('fi=')[-1]

    return [
        {
            'name': WebDriverWait(contractor_card, ELEMENT_FIND_TIMEOUT).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-component="Pro Name"'))
            ).text,
            'url': contractor_card.find_element(By.CSS_SELECTOR, 'a').get_attribute('href'),
            'page': page_num,
            'expected_page': expected_page_num
        }
        for contractor_card in contractor_items
    ]


def run_gather_links(driver_pool: WebDriverPool, url) -> list:
    for _ in range(PAGE_RETRY_COUNT):
        driver: webdriver.Chrome = driver_pool.acquire()
        try:
            return gather_links(driver, url)
        except Exception as e:
            logging.error(f'Error gathering links: {e}')
        finally:
            driver_pool.release(driver)
    return []




def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(processName)s - %(levelname)s - %(message)s')
    multiprocessing.log_to_stderr(logging.INFO)

    with WebDriverPool(GATHERER_THREAD_MAX_WORKERS) as pool:
        with ThreadPoolExecutor(max_workers=pool.max_workers) as executor:
            contractors = []
            futures = []

            for page in range(1, PAGE_COUNT + 1):
                futures.append(
                    executor.submit(run_gather_links, pool, f'https://www.houzz.com/professionals/general-contractor/probr0-bo~t_11786?fi={ITEM_PER_PAGE * (page - 1)}')
                )

            for result in as_completed(futures):
                contractors.extend(result.result())
                logging.info(f'Gathered: {len(contractors)} contractor urls')

            logging.info(f'Total: {len(contractors)} contractor urls', )


    futures = []
    results = []
    with ProcessPoolExecutor(CONTRACTOR_PARSER_MAX_WORKERS) as executor:
        items_per_core = len(contractors) // CONTRACTOR_PARSER_MAX_WORKERS

        chunks = [
            contractors[i:i + items_per_core]
            for i in range(0, len(contractors), items_per_core)
        ]
        for chunk in chunks:
                futures.append(executor.submit(run_contractors_parser, chunk))

        for future in as_completed(futures):
            contractor_details = future.result()
            logging.info(f'Parsed: {len(contractor_details)} contractor pages')
            results.extend(contractor_details)

    with OUTPUT_FILE.open('w') as f:
        json.dump(results, f, indent=4)



if __name__ == '__main__':
    main()
