from pathlib import Path

BASE_DIR: Path = Path(__file__).resolve().parent

OUTPUT_DIR = BASE_DIR / 'output'
OUTPUT_DIR.mkdir(exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / 'contractors.json'

CONTRACTOR_PARSER_MAX_WORKERS: int = 1
GATHERER_THREAD_MAX_WORKERS: int = 1
PAGE_RETRY_COUNT: int = 3
PAGE_COUNT: int = 2
ITEM_PER_PAGE: int = 15
ELEMENT_FIND_TIMEOUT: int = 10