import os
from dataclasses import dataclass, field
from queue import Queue
from typing import Self

from selenium import webdriver


@dataclass
class WebDriverPool:
    max_workers: int = field(default_factory=os.cpu_count)
    workers: Queue = field(default_factory=Queue)

    def __post_init__(self) -> None:
        for _ in range(self.max_workers):
            driver: webdriver.Chrome = webdriver.Chrome()
            driver.set_window_size(1280, 720)

            self.workers.put(driver)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        while not self.workers.empty():
            self.workers.get().quit()

    def acquire(self) -> webdriver.Chrome:
        return self.workers.get(block=True)

    def release(self, worker: webdriver.Chrome) -> None:
        self.workers.put(worker)
