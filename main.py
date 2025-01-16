import json
import logging
import re
from concurrent.futures import as_completed
from concurrent.futures.thread import ThreadPoolExecutor

import selenium.common.exceptions

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from driver_pool import WebDriverPool

PAGE_COUNT: int = 4
ITEM_PER_PAGE: int = 15


def run_contractor_page_parser(driver_pool: WebDriverPool, contractor: dict) -> dict:
    driver: webdriver.Chrome = driver_pool.acquire()
    try:
        return parse_contractor_page(driver, contractor)
    except Exception as e:
        logging.error(f'Error parsing {contractor["url"]}: {e}')
        return contractor
    finally:
        driver_pool.release(driver)


def parse_contractor_page(driver, contractor: dict) -> dict:
    logging.info(f'Parsing: {contractor["url"]}')
    driver.get(contractor['url'])
    for _ in range(3):
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-component="Pro Name"'))
            )
        except selenium.common.exceptions.TimeoutException:
            driver.get(contractor['url'])

    # get only number from string
    try:
        projects_link = driver.find_element(By.CSS_SELECTOR, '#projects-label')
    except (selenium.common.exceptions.NoSuchElementException, selenium.common.exceptions.TimeoutException):
        return contractor
    else:
        contractor['project_count'] = int(
            re.findall(r'\d+', projects_link.text)[0]
        )

    business_details = driver.find_elements(By.CSS_SELECTOR, '.hui-cell')
    for item in business_details:
        try:
            key = item.find_element(By.CSS_SELECTOR, 'h3').text
            value = item.find_element(By.CSS_SELECTOR, 'p').text
        except selenium.common.exceptions.NoSuchElementException:
            break
        contractor[key] = value
    try:
        rating_element = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.ReviewAggregation__StyledRating-sc-11mmvxo-1'))
        )
        reviews_element = driver.find_element(By.CSS_SELECTOR,
                                              '.ReviewAggregation__StyledReviewNumber-sc-11mmvxo-3')

        contractor['review_count'] = int(
            re.findall(r'\d+', reviews_element.text)[0]
        )
        contractor['rating'] = float(rating_element.text)

    except selenium.common.exceptions.TimeoutException:
        pass

    return contractor


def gather_links(driver: webdriver.Chrome, url: str) -> list:
    driver.get(url)
    anywhere_location_button = WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, '#hui-menu-1-item-4'))
    )
    driver.execute_script("arguments[0].click();", anywhere_location_button)
    driver.get(url)

    contractor_items = WebDriverWait(driver, 5).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, '.hz-pro-search-results__item'))
    )
    page_num = WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, '.hz-pagination-link--selected'))
    ).text

    expected_page_num = url.split('fi=')[-1]

    return [
        {
            'name': WebDriverWait(contractor_card, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-component="Pro Name"'))
            ).text,
            'url': contractor_card.find_element(By.CSS_SELECTOR, 'a').get_attribute('href'),
            'page': page_num,
            'expected_page': expected_page_num
        }
        for contractor_card in contractor_items
    ]


def run_gather_links(driver_pool: WebDriverPool, url) -> list:
    driver: webdriver.Chrome = driver_pool.acquire()
    try:
        return gather_links(driver, url)
    except Exception as e:
        logging.error(f'Error gathering links: {e}')
        return []
    finally:
        driver_pool.release(driver)


def main() -> None:
    logging.basicConfig(level=logging.INFO)

    with WebDriverPool(2) as pool:
        with ThreadPoolExecutor(max_workers=pool.max_workers) as executor:
            contractors = []
            futures = []

            for page in range(1, PAGE_COUNT + 1):
                futures.append(
                    executor.submit(run_gather_links, pool, f'https://www.houzz.com/professionals/general-contractor/probr0-bo~t_11786?fi={ITEM_PER_PAGE * (page - 1)}')
                )

            for result in as_completed(futures):
                contractors.extend(result.result())
                logging.info(f'Gathered: {len(contractors)}')

            logging.info(f'Total: {len(contractors)}', )

            futures = []
            for contractor in contractors:
                futures.append(
                    executor.submit(run_contractor_page_parser, pool, contractor)
                )

            for result in as_completed(futures):
                contractor = result.result()
                logging.info(f'Parsed: {contractor["name"]}')

            with open('contractors.json', 'w') as f:
                json.dump(contractors, f, indent=4)


if __name__ == '__main__':
    main()
