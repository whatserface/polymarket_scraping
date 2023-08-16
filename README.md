# Polymarket scraper

- This scraper allows you to specify the first page to start the crawling from and the number of pages to go through
- First page can be thought of as an index in an array, hence first_page=0 means that you want to start the crawling from the first page
- Be mindful when choosing the number of pages: one page takes about 250 MB.
- To specify params, type in a terminal: scrapy crawl polymarket_scrape -a first_page=1 -a pages=2 -o output.json
  - -o specifies the output
- By default, first_page=0 and pages=1, hence, if you don't specify any parameters you'll just crawl the first page
- To stop crawling, press Ctrl+C on Windows or Command-C on Mac.
- If you encounter HTTP errors like 500, 503, it means the crawler is sending requests too frequently. To fix this, go to settings.py, lower CONCURRENT_REQUESTS or increase DOWNLOAD_DELAY, or do both