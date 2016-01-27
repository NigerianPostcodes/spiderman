# -*- coding: utf-8 -*-

import scrapy


class UrbanPostcodeItem(scrapy.Item):
    state = scrapy.Field()
    town = scrapy.Field()
    area = scrapy.Field()
    street = scrapy.Field()
    postcode = scrapy.Field()

class RuralPostcodeItem(scrapy.Item):
    state = scrapy.Field()
    lga = scrapy.Field()
    district = scrapy.Field()
    town = scrapy.Field()
    postcode = scrapy.Field()

class PostalFacilityPostcodeItem(scrapy.Item):
    state = scrapy.Field()
    lga = scrapy.Field()
    facility = scrapy.Field()
    postcode = scrapy.Field()
