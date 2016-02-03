import re
from scrapy.spiders import BaseSpider
from scrapy.selector import Selector
from nigeriapostcodes.items import RuralPostcodeItem
from scrapy.http import FormRequest


class RuralSpider(BaseSpider):
    name = "rural"
    allowed_domains = ["nigeriapostcodes.com"]
    start_urls = ["http://nigeriapostcodes.com/index.php/welcome/rural"]

    states = {}
    lgas = {}
    districts = {}
    towns = {}
    processed_districts = []
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
                "http://nigeriapostcodes.com/index.php/ajax/getRuralLGA/",
                formdata={'state_id': state_id},
                callback=self.parse_lgas, meta={'state_id': state_id})

    def parse_lgas(self, response):
        sel = Selector(response)
        state_id = response.meta['state_id']
        for option in sel.xpath(
            '//select[@id="lga-select"]/option[position()>1]'
        ):
            lga_id = option.xpath('@value').extract_first()
            lga_name = option.xpath('text()').extract_first()

            self.lgas[lga_id] = lga_name

            yield FormRequest(
                'http://nigeriapostcodes.com/index.php/ajax/getRuralDistrict/',
                formdata={'lga_id': lga_id},
                callback=self.parse_districts,
                meta={'state_id': state_id, 'lga_id': lga_id})

    def parse_districts(self, response):
        sel = Selector(response)
        state_id = response.meta['state_id']
        lga_id = response.meta['lga_id']
        for option in sel.xpath(
            '//select[@id="district-select"]/option[position()>1]'
        ):
            district_id = option.xpath('@value').extract_first()
            district_name = option.xpath('text()').extract_first()

            self.districts[district_id] = district_name

            yield FormRequest(
                'http://nigeriapostcodes.com/index.php/ajax/getRuralDistrictTown/',
                formdata={'district_id': district_id},
                callback=self.parse_towns,
                meta={'state_id': state_id, 'lga_id': lga_id,
                      'district_id': district_id})

    def parse_towns(self, response):
        sel = Selector(response)
        state_id = response.meta['state_id']
        lga_id = response.meta['lga_id']
        district_id = response.meta['district_id']
        towns_in_this_district = []

        for option in sel.xpath(
            '//select[@id="town-select"]/option[position()>1]'
        ):
            town_id = option.xpath('@value').extract_first()
            town_name = option.xpath('text()').extract_first()

            self.towns[town_id] = town_name
            towns_in_this_district.append(town_id)

        # this request wasn't placed in the loop because this only needs to be
        # called once per district reducing excessive requests given that all
        # towns in the same district have the same postcode
        yield FormRequest(
            'http://nigeriapostcodes.com/index.php/welcome/getRuralPostCode',
            formdata={'state-id': state_id, 'lga-id': lga_id,
                      'district-id': district_id, 'town-name': town_name,
                      'btn_search': ''},
            callback=self.parse_postcodes,
            meta={'state_id': state_id, 'lga_id': lga_id,
                  'district_id': district_id, 'towns': towns_in_this_district})

    def parse_postcodes(self, response):
        sel = Selector(response)
        state_id = response.meta['state_id']
        lga_id = response.meta['lga_id']
        district_id = response.meta['district_id']
        towns = response.meta['towns']

        try:
            postcode = self.postcode_re.match(
                sel.xpath(
                    '//div[contains(.//text(), "Postcode =>")]/text()'
                ).extract_first()).group(1)
            for town_id in towns:
                item = RuralPostcodeItem()
                item['state'] = self.states[state_id]
                item['lga'] = self.lgas[lga_id]
                item['district'] = self.districts[district_id]
                item['town'] = self.towns[town_id]
                item['postcode'] = postcode
                yield item
        except AttributeError:
            self.logger.warn(
                'Postcode parsing failed for state (' + state_id + ') ' +
                'lga (' + lga_id + ') district (' + district_id + ')')
