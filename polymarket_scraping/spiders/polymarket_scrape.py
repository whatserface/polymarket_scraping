import json
import logging
from urllib.parse import urlencode, parse_qs
import scrapy
from ..items import MarketItem, ResolutionItem

from decimal import Decimal, getcontext

# only resolved events with graphs

class PolymarketScrapeSpider(scrapy.Spider):
    name = "polymarket_scrape"
    allowed_domains = ["polymarket.com"]

    def __init__(self, first_page='0', pages='1', **kwargs):
        '''
        first_page is the index of the page to start scraping from.
        It's smaller by one than the real page's number (1 means the 2nd page)
        
        pages is the total number of pages to go through.
        For first_page=0 and pages=2, the spider will go through all the events from
        1st page to the 3rd page
        '''
        super().__init__(**kwargs)

        assert first_page.isdigit() and 0 <= int(first_page), "first_page must be greater than or equal to zero"
        assert pages.isdigit() and 0 < int(pages), "pages must be a natural number"
        self.first_page, self.pages = int(first_page), int(pages)
        
    def start_requests(self):
        search_page_params = {"_sts": "active", "_p": self.first_page, "cardView": 'true'}
        start_requests = []
        for _ in range(self.pages):
            start_requests.append(
                scrapy.http.JsonRequest(url='https://polymarket.com/api/events?'
                                        + urlencode(search_page_params),
                                        data={'show_favorites': False})
            )
            search_page_params['_p'] += 1
        return start_requests

    def parse(self, response):
        page_num = parse_qs(response.url)['_p'][0]
        if response.json():
            logging.info(f"Parsing page {page_num}")
            for event in response.json():
                yield scrapy.Request(f'https://polymarket.com/event/{event["slug"]}',
                                    callback=self.get_clob_token_ids,
                                    )
        else:
            logging.warn(f"Got an empty json in response for the page {page_num}. Stopping the parsing...")
        
    
    def get_clob_token_ids(self, response):
        js = json.loads(response.css('script[id="__NEXT_DATA__"]::text').get())
        
        graph_params = {
            'interval': 'max',
            'market': None,
            'fidelity': '1'
        }
        for market in js['props']['pageProps']['dehydratedState']['queries'][0]['state']['data']['markets']:
            if not market['clobTokenIds']:
                logging.info(f"Can't parse market's {market['question']} graph")
                yield None
                continue

            if not market.get('resolutionData'):
                logging.debug(f'Dropped {market["question"]}, check {response.url} out')
                yield None
                continue

            market_item = MarketItem()
            market_item['url'] = response.url
            market_item['outcomes']: [str, str] = market['outcomes']
            market_item['name']: str = market['question']
            
            logging.info(f'Parsing market {market["question"]}')

            market_item['about']: str = market['description']
            market_item['contract_url'] = f"https://polygonscan.com/address/{market['resolvedBy']}"
            market_item['resolver_url'] = f"https://polygonscan.com/address/{market['marketMakerAddress']}"
            market_item['resolution'] = ResolutionItem()
            if market.get('resolutionData'):
                market_item['resolution']['status']: str = market['resolutionData']['status']
                if market['resolutionData']['status'] == 'resolved':
                    market_item['resolution']['outcome_proposed'] = market_item['outcomes'][int(market['resolutionData']['proposedPrice'] == "0")]
                    market_item['resolution']['was_disputed']: bool = market['resolutionData']['wasDisputed']
                    market_item['resolution']['final_outcome'] = market_item['outcomes'][int(market['resolutionData']['price'] == "0")]
            else:
                market_item['resolution']['final_outcome'] = response.css('p.c-dqzIym-eYAYgJ-weight-semi.c-dqzIym-kVdbTu-size-xl::text').getall()[1]


            _, no = market['clobTokenIds']
            graph_params['market'] = no
            yield scrapy.FormRequest(f'https://clob.polymarket.com/prices-history',
                                 formdata=graph_params,
                                 method='GET',
                                 callback=self.parse_graph_no,
                                 cb_kwargs={'market_item': market_item}
            )


    def parse_graph_no(self, response, market_item):
        graph_points = response.json()['history']
        if not graph_points:
            logging.warn(f"{market_item['name']} doesn't have a graph")
            return {}
        
        getcontext().prec = 2
        point_str1 = f'p_{market_item["outcomes"][0].lower()}'
        point_str2 = f'p_{market_item["outcomes"][1].lower()}'
        for point in graph_points:
            point[point_str2] = point.pop('p')
            point[point_str1] = float(1 - Decimal(point[point_str2]))
        market_item['graph_points'] = graph_points
        logging.info(f'Parsed {market_item["name"]}')
        return market_item