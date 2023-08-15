# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class MarketItem(scrapy.Item):
    # define the fields for your item here like:
    name = scrapy.Field()
    graph_points_yes = scrapy.Field()
    graph_points_no = scrapy.Field()
    about = scrapy.Field()
    contract_url = scrapy.Field()
    resolver_url = scrapy.Field()
    resolution_status = scrapy.Field()

class ResolutionItem(scrapy.Item):
    status = scrapy.Field()
    outcome_proposed = scrapy.Field()
    was_disputed = scrapy.Field()
    final_outcome = scrapy.Field()