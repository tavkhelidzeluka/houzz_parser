import json
import logging
import multiprocessing
import re
import selenium.common.exceptions

from dataclasses import dataclass, field

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC



@dataclass
class ContractorsParser:
    contractors: list[dict]
    logger: logging.Logger = field(default_factory=multiprocessing.get_logger)
    driver: webdriver.Chrome = field(default_factory=webdriver.Chrome)

    def __post_init__(self) -> None:
        self.driver.set_window_size(1280, 720)
        self.logger.info('Initialized ContractorsParser')

    def parse_contractors(self) -> list[dict]:
        for contractor in self.contractors:
            contractor.update(self.__parse_contractor(contractor))
        return self.contractors

    def __parse_contractor(self, contractor) -> dict:
        self.logger.info(f'Parsing: {contractor["url"]}')
        self.driver.get(contractor['url'])
        for _ in range(3):
            try:
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '[data-component="Pro Name"'))
                )
            except selenium.common.exceptions.TimeoutException:
                self.driver.get(contractor['url'])

        # get only number from string
        try:
            projects_link = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '#projects-label'))
            )
        except (selenium.common.exceptions.NoSuchElementException, selenium.common.exceptions.TimeoutException):
            self.logger.error(f'No projects found for {contractor["name"]} - {contractor["url"]}')
        else:
            contractor['project_count'] = int(
                re.findall(r'\d+', projects_link.text)[0]
            )
            self.logger.info(f'Found {contractor["project_count"]} projects for {contractor["name"]}')

        business_details = self.driver.find_elements(By.CSS_SELECTOR, '.hui-cell')
        for item in business_details:
            try:
                key = item.find_element(By.CSS_SELECTOR, 'h3').text
                value = item.find_element(By.CSS_SELECTOR, 'p').text
            except selenium.common.exceptions.NoSuchElementException:
                break
            contractor[key] = value
        try:
            rating_element = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.ReviewAggregation__StyledRating-sc-11mmvxo-1'))
            )
            reviews_element = self.driver.find_element(By.CSS_SELECTOR,
                                                       '.ReviewAggregation__StyledReviewNumber-sc-11mmvxo-3')

            contractor['review_count'] = int(
                re.findall(r'\d+', reviews_element.text)[0]
            )
            contractor['rating'] = float(rating_element.text)

            self.logger.info(f'Found {contractor["review_count"]} reviews for {contractor["name"]}')
        except selenium.common.exceptions.TimeoutException:
            self.logger.error(f'No reviews found for {contractor["name"]} - {contractor["url"]}')

        return contractor


def run_contractors_parser(contractors: list) -> list:
    return ContractorsParser(contractors).parse_contractors()


if __name__ == '__main__':
    cp = ContractorsParser([
        {
            "name": "Hoboken Kitchen and Bath",
            "url": "https://www.houzz.com/professionals/general-contractors/hoboken-kitchen-and-bath-pfvwus-pf~1043068120",
            "page": "2",
            "expected_page": "15"
        }
    ]).parse_contractors()

    with open('test.json', 'w') as f:
        json.dump(cp, f, indent=4)