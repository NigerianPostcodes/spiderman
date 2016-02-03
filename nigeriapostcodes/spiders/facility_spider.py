import re
from scrapy.spiders import BaseSpider
from scrapy.selector import Selector
from nigeriapostcodes.items import PostalFacilityPostcodeItem
from scrapy.http import FormRequest


class FacilitySpider(BaseSpider):
    name = "facility"
    allowed_domains = ["nigeriapostcodes.com"]
    start_urls = ["http://nigeriapostcodes.com/index.php/welcome/facility"]

    states = {}
    lgas = {}
    facilities = {}
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
                "http://nigeriapostcodes.com/index.php/ajax/getPFLGA/",
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
                'http://nigeriapostcodes.com/index.php/ajax/getPF/',
                formdata={'lga_id': lga_id},
                callback=self.parse_facilities,
                meta={'state_id': state_id, 'lga_id': lga_id})

    def parse_facilities(self, response):
        sel = Selector(response)
        state_id = response.meta['state_id']
        lga_id = response.meta['lga_id']
        for option in sel.xpath(
            '//select[@id="facility-select"]/option[position()>1]'
        ):
            facility_id = option.xpath('@value').extract_first()
            facility_name = option.xpath('text()').extract_first()

            self.facilities[facility_id] = facility_name

            yield FormRequest(
                'http://nigeriapostcodes.com/index.php/welcome/getPFPostCode',
                formdata={
                    'state-id': state_id,
                    'lga-id': lga_id,
                    'facility-id': facility_id,
                    'btn_search': ''},
                callback=self.parse_postcode,
                meta={'state_id': state_id, 'lga_id': lga_id,
                      'facility_id': facility_id})

    def parse_postcode(self, response):
        sel = Selector(response)
        state_id = response.meta['state_id']
        lga_id = response.meta['lga_id']
        facility_id = response.meta['facility_id']

        try:
            postcode = self.postcode_re.match(
                sel.xpath(
                    '//div[contains(.//text(), "Postcode =>")]/text()'
                ).extract_first()).group(1)
            item = PostalFacilityPostcodeItem()
            item['state'] = self.states[state_id]
            item['lga'] = self.lgas[lga_id]
            item['facility'] = self.facilities[facility_id]
            item['postcode'] = postcode
            yield item
        except AttributeError:
            self.logger.warn(
                'Postcode parsing failed for state (' + state_id + ') ' +
                'lga (' + lga_id + ') facility (' + facility_id + ')')
