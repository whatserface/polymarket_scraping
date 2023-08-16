# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy
from pprint import pformat


class MarketItem(scrapy.Item):
    # define the fields for your item here like:
    name = scrapy.Field()
    graph_points = scrapy.Field()
    about = scrapy.Field()
    outcomes = scrapy.Field()
    contract_url = scrapy.Field()
    resolver_url = scrapy.Field()
    resolution = scrapy.Field()

    def __repr__(self):
        return pformat({"name": self['name'], "resolution": self['resolution'], "contract_url": self['contract_url'], "resolver_url": self['resolver_url']})

class ResolutionItem(scrapy.Item):
    status = scrapy.Field()
    outcome_proposed = scrapy.Field()
    was_disputed = scrapy.Field()
    final_outcome = scrapy.Field()