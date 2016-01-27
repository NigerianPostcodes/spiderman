import re
from scrapy.spiders import BaseSpider
from scrapy.selector import Selector
from nigeriapostcodes.items import UrbanPostcodeItem
from scrapy.http import FormRequest


class UrbanSpider(BaseSpider):
    name = "urban"
    allowed_domains = ["nigeriapostcodes.com"]
    start_urls = ["http://nigeriapostcodes.com/"]

    states = {}
    towns = {}
    areas = {}
    streets = {}
    processed_areas = []
    postcode_re = re.compile('Postcode => (\d+)')

    def parse(self, response):
        sel = Selector(response)
        for option in sel.xpath(
            '//select[@id="state-select"]/option[position()>1]'
        ):
            state_id = option.xpath('@value').extract_first()
            state_name = option.xpath('text()').extract_first()

            self.states[state_id] = state_name

            yield FormRequest(
                "http://nigeriapostcodes.com/index.php/ajax/getUrbanTown/",
                formdata={'state_id': state_id},
                callback=self.parse_towns, meta={'state_id': state_id})

    def parse_towns(self, response):
        sel = Selector(response)
        state_id = response.meta['state_id']
        for option in sel.xpath(
            '//select[@id="town-select"]/option[position()>1]'
        ):
            town_id = option.xpath('@value').extract_first()
            town_name = option.xpath('text()').extract_first()

            self.towns[town_id] = town_name

            yield FormRequest(
                'http://nigeriapostcodes.com/index.php/ajax/getUrbanAreas/',
                formdata={'town_id': town_id},
                callback=self.parse_areas,
                meta={'state_id': state_id, 'town_id': town_id})

    def parse_areas(self, response):
        sel = Selector(response)
        state_id = response.meta['state_id']
        town_id = response.meta['town_id']
        for option in sel.xpath(
            '//select[@id="area-select"]/option[position()>1]'
        ):
            area_id = option.xpath('@value').extract_first()
            area_name = option.xpath('text()').extract_first()

            self.areas[area_id] = area_name

            yield FormRequest(
                'http://nigeriapostcodes.com/index.php/ajax/getUrbanStreets/',
                formdata={'area_id': area_id},
                callback=self.parse_streets,
                meta={'state_id': state_id, 'town_id': town_id,
                      'area_id': area_id})

    def parse_streets(self, response):
        sel = Selector(response)
        state_id = response.meta['state_id']
        town_id = response.meta['town_id']
        area_id = response.meta['area_id']
        streets_in_this_area = []

        for option in sel.xpath(
            '//select[@id="street-select"]/option[position()>1]'
        ):
            street_id = option.xpath('@value').extract_first()
            street_name = option.xpath('text()').extract_first()

            self.streets[street_id] = street_name
            streets_in_this_area.append(street_id)

        # this request wasn't placed in the loop because this only needs to be
        # called once per area reducing excessive requests given that all
        # streets in the same area have the same postcode
        yield FormRequest(
            'http://nigeriapostcodes.com/index.php/welcome/getUrbanPostCode',
            formdata={'state-id': state_id, 'town-id': town_id,
                      'area-id': area_id, 'street-id': street_id,
                      'btn_search': ''},
            callback=self.parse_postcodes,
            meta={'state_id': state_id, 'town_id': town_id,
                  'area_id': area_id, 'streets': streets_in_this_area})

    def parse_postcodes(self, response):
        sel = Selector(response)
        state_id = response.meta['state_id']
        town_id = response.meta['town_id']
        area_id = response.meta['area_id']
        streets = response.meta['streets']

        try:
            postcode = self.postcode_re.match(
                sel.xpath(
                    '//div[contains(.//text(), "Postcode =>")]/text()'
                ).extract_first()).group(1)
            for street_id in streets:
                item = UrbanPostcodeItem()
                item['state'] = self.states[state_id]
                item['town'] = self.towns[town_id]
                item['area'] = self.areas[area_id]
                item['street'] = self.streets[street_id]
                item['postcode'] = postcode
                yield item
        except AttributeError:
            self.logger.warn(
                'Postcode parsing failed for state (' + state_id + ') ' +
                'town (' + town_id + ') area (' + area_id + ')')
