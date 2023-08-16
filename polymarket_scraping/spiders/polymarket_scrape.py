import json
import logging
from urllib.parse import urlencode, parse_qs
import scrapy
from ..items import MarketItem, ResolutionItem


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
        search_page_params = {"_sts": "all", "_p": self.first_page, "cardView": 'true'}
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
        
        self.graph_params = {
            'interval': 'max',
            'market': None,
            'fidelity': '1'
        }
        for market in js['props']['pageProps']['dehydratedState']['queries'][0]['state']['data']['markets']:
            market_item = MarketItem()
            market_item['outcomes']: [str, str] = market['outcomes']
            market_item['name']: str = market['question']
            
            logging.info(f'Parsing market {market["question"]}')

            market_item['about']: str = market['description']
            market_item['contract_url'] = f"https://polygonscan.com/address/{market['resolvedBy']}"
            market_item['resolver_url'] = f"https://polygonscan.com/address/{market['marketMakerAddress']}"
            market_item['resolution'] = ResolutionItem()
            market_item['resolution']['status']: str = market['resolutionData']['status']
            if market['resolutionData']['status'] == 'resolved':
                market_item['resolution']['outcome_proposed'] = market_item['outcomes'][int(market['resolutionData']['proposedPrice'] == "0")]
                market_item['resolution']['was_disputed']: bool = market['resolutionData']['wasDisputed']
                market_item['resolution']['final_outcome'] = market_item['outcomes'][int(market['resolutionData']['price'] == "0")]
            if not market['clobTokenIds']:
                logging.info(f"Can't parse market's {market['question']} graph")
                yield market_item
                continue
            yes, no = market['clobTokenIds']

            self.graph_params['market'] = yes
            yield scrapy.FormRequest(f'https://clob.polymarket.com/prices-history',
                                 formdata=self.graph_params,
                                 method='GET',
                                 callback=self.parse_graph_yes,
                                 cb_kwargs={'market_item': market_item, 'next_page_market': no}
            )
# https://polymarket.com/event/will-donald-trump-be-president-of-the-usa-on
# resolutionData
    def parse_graph_yes(self, response, market_item, next_page_market):
        graph_points = response.json()['history']
        point_str = f'p_{market_item["outcomes"][0].lower()}'
        for point in graph_points:
            point[point_str] = point.pop('p')
        market_item['graph_points'] = graph_points
        self.graph_params['market'] = next_page_market
        yield scrapy.FormRequest('https://clob.polymarket.com/prices-history',
                                formdata=self.graph_params,
                                method='GET',
                                callback=self.parse_graph_no,
                                cb_kwargs={'market_item': market_item}
        )

    def parse_graph_no(self, response, market_item):
        points = len(market_item['graph_points'])
        outcome = market_item["outcomes"][1]
        point_str = f'p_{outcome.lower()}'
        error = False
        for i, point_no in enumerate(response.json()['history']):
            if i < points:
                market_item['graph_points'][i][point_str] = point_no['p']
            else:
                error = True
                point_no[point_str] = point_no.pop('p')
                market_item['graph_points'].append(point_no)
        if error:
            outcome2 = market_item["outcomes"][0]
            logging.warn(f'In {market_item["name"]} the number of {outcome} points is more than the {outcome2} points')
        logging.info(f'Parsed {market_item["name"]}')
        return market_item