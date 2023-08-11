from urllib.parse import urlencode
import scrapy
from ..items import MarketItem


class PolymarketScrapeSpider(scrapy.Spider):
    name = "polymarket_scrape"
    allowed_domains = ["polymarket.com"]

    def start_requests(self):
        first_page_params = {"_sts": "all", "_p": 0, "cardView": True}
        return [scrapy.http.JsonRequest('https://polymarket.com/api/events?' + urlencode(first_page_params),
                                   data={'show_favorites': False})]

    def parse(self, response):
        for event in response.json():
            yield scrapy.Request(f'https://polymarket.com/api/event?slug={event["slug"]}',
                                 callback=self.get_clob_token_ids)
    
    def get_clob_token_ids(self, response):
        params = {
            'interval': 'all',
            'market': None,
            'fidelity': 1
        }
        for market in response.json()['markets']:
            item = MarketItem()
            if market['clobTokenIds']:
                # todo: get other params herefrom
                continue
            yes, no = market['clobTokenIds']

            params['market'] = yes
            yield scrapy.Request(f'https://clob.polymarket.com/prices-history?' +
                                 urlencode(params),
                                 callback=self.parse_graph,
                                 cb_kwargs={'item': item}
            )
            params['market'] = no
            yield scrapy.Request(f'https://clob.polymarket.com/prices-history?' +
                                 urlencode(params),
                                 callback=self.parse_graph,
                                 cb_kwargs={'item': item}
            )

    def parse_graph_yes(self, response, item):
        item['graph_points_yes'] = response.json()

    def parse_graph_no(self, response, item):
        item['graph_points_no'] = response.json()