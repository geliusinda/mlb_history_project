START_YEAR = 1980
END_YEAR = 2025
DATASETS = ["standings"]

BASE_URL_YEAR_MENU = "https://www.baseball-almanac.com/yearmenu.shtml"

LEAGUE_URLS = {
    "AL": "https://www.baseball-almanac.com/yearly/yr{year}a.shtml",
    "NL": "https://www.baseball-almanac.com/yearly/yr{year}n.shtml",
}

REQUEST_DELAY_SEC = 1.5
MAX_RETRIES = 2
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36 (Educational Project)"
