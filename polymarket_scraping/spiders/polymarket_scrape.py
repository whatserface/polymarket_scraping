import json
import logging
from urllib.parse import urlencode, parse_qs
import scrapy
from ..items import MarketItem, ResolutionItem


class PolymarketScrapeSpider(scrapy.Spider):
    name = "polymarket_scrape"
    allowed_domains = ["polymarket.com"]

    def start_requests(self):
        self.search_page_params = {"_sts": "all", "_p": 0, "cardView": True}
        return [scrapy.http.JsonRequest('https://polymarket.com/api/events?' + urlencode(self.search_page_params),
                                   data={'show_favorites': False})]

    def parse(self, response):
        if response.json():
            logging.info(f"Parsing page {self.search_page_params['_p']}")
            for event in response.json():
                yield scrapy.Request(f'https://polymarket.com/event/{event["slug"]}',
                                    callback=self.get_clob_token_ids,
                                    )
            # else:
            #     self.search_page_params['_p'] += 1
            #     if self.search_page_params['_p'] == 1:
            #         yield scrapy.http.JsonRequest('https://polymarket.com/api/events?' + urlencode(self.search_page_params),
            #                        data={'show_favorites': False})
        
    
    def get_clob_token_ids(self, response):
        js = json.loads(response.css('script[id="__NEXT_DATA__"]::text').get())
        
        self.graph_params = {
            'interval': 'all',
            'market': None,
            'fidelity': 1
        }
        for market in js['props']['pageProps']['dehydratedState']['queries'][0]['state']['data']['markets']:
            market_item = MarketItem()
            outcomes = market['outcomes']
            market_item['name'] = market['question']
            market_item['about'] = market['description']
            market_item['contract_url'] = f"https://polygonscan.com/address/{market['resolvedBy']}"
            market_item['resolver_url'] = f"https://polygonscan.com/address/{market['marketMakerAddress']}"
            market_item['resolution'] = ResolutionItem()
            market_item['resolution']['status'] = market['resolutionData']['status']
            if market['resolutionData']['status'] == 'resolved':
                market_item['resolution']['outcome_proposed'] = outcomes[0] if market['resolutionData']['proposedPrice'] != "0" else outcomes[1]
                market_item['resolution']['was_disputed'] = market['resolutionData']['wasDisputed']
                market_item['resolution']['final_outcome'] = outcomes[0] if market['resolutionData']['price'] != "0" else outcomes[1]
            if not market['clobTokenIds']:
                # todo: get other params herefrom
                continue
            yes, no = market['clobTokenIds']

            self.graph_params['market'] = yes
            yield scrapy.Request(f'https://clob.polymarket.com/prices-history?' +
                                 urlencode(self.graph_params),
                                 callback=self.parse_graph_yes,
                                 cb_kwargs={'market_item': market_item, 'next_page_market': no}
            )
# https://polymarket.com/event/will-donald-trump-be-president-of-the-usa-on
# resolutionData
    def parse_graph_yes(self, response, market_item, next_page_market):
        market_item['graph_points_yes'] = response.json()['history']
        self.graph_params['market'] = next_page_market
        yield scrapy.Request(f'https://clob.polymarket.com/prices-history?' +
                                urlencode(self.graph_params),
                                callback=self.parse_graph_no,
                                cb_kwargs={'market_item': market_item}
        )

    def parse_graph_no(self, response, market_item):
        market_item['graph_points_no'] = response.json()['history']
        return market_item