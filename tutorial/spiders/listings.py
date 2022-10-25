from bs4 import Script
from cv2 import add
import scrapy
import json
from scrapy import Selector
from scrapy_splash import SplashRequest

class ListingsSpider(scrapy.Spider):
    name = 'listings'
    allowed_domains = ['www.centris.ca']
    positions = {
            "startPosition": 0
        }
    uck = ""
    script = """
                function main(splash, args)
                    assert(splash:go(args.url))
                    assert(splash:wait(0.5))
                    return {
                        html = splash:html(),
                    }
                end
            """

    def start_requests(self):
        yield scrapy.Request(
            url='https://www.centris.ca/UserContext/Lock',
            method='POST',
            headers={
                'x-requested-with': 'XMLHttpRequest',
                'content-type': 'application/json'
            },
            body=json.dumps({'uc': 0}),
            callback=self.generate_uck
        )
    
    def generate_uck(self, response):
        global uck
        uck = response.body
        query = {
                    "query":{
                        "UseGeographyShapes":0,
                        "Filters":[
                            {
                                "MatchType":"CityDistrictAll",
                                "Text":"Montréal (All boroughs)",
                                "Id":5
                            }
                        ],
                        "FieldsValues":[
                            {
                                "fieldId":"CityDistrictAll",
                                "value":5,
                                "fieldConditionId":"",
                                "valueConditionId":""
                            },
                            {
                                "fieldId":"Category",
                                "value":"Residential",
                                "fieldConditionId":"",
                                "valueConditionId":""
                            },
                            {
                                "fieldId":"SellingType",
                                "value":"Rent",
                                "fieldConditionId":"",
                                "valueConditionId":""
                            },
                            {
                                "fieldId":"LandArea",
                                "value":"SquareFeet",
                                "fieldConditionId":"IsLandArea",
                                "valueConditionId":""
                            },
                            {
                                "fieldId":"RentPrice",
                                "value":0,
                                "fieldConditionId":"ForRent",
                                "valueConditionId":""
                            },
                            {
                                "fieldId":"RentPrice",
                                "value":1500,
                                "fieldConditionId":"ForRent",
                                "valueConditionId":""
                            }
                        ]
                    },
                    "isHomePage":True,
                    }
        yield scrapy.Request(
            url="https://www.centris.ca/property/UpdateQuery",
            method="POST",
            body=json.dumps(query),
            headers={
                'Content-Type': 'application/json',
                'x-requested-with': 'XMLHttpRequest',
                'x-centris-uc': 0,
                'x-centris-uck': uck
            },
            callback = self.update_query
        )
    
    def update_query(self, response): 
        yield scrapy.Request(
            url="https://www.centris.ca/Property/GetInscriptions",
            method="POST",
            body=json.dumps(self.positions),
            headers= {
                'Content-Type': 'application/json',
                'x-requested-with': 'XMLHttpRequest',
                'x-centris-uc': 0,
                'x-centris-uck': uck
            },
            callback = self.parse
        )

    def parse(self, response):
        resp_dict = json.loads(response.body)
        html = resp_dict.get('d').get('Result').get('html')
        sel = Selector(text=html)
        listings = sel.xpath("//div[@class='property-thumbnail-item thumbnailItem col-12 col-sm-6 col-md-4 col-lg-3']")
        print(len(listings))
        for listing in listings:
            category = listing.xpath(".//div[@class='description']//div[@class='location-container']//span[@class='category']/div/text()").get().replace(' à louer', "")
            bedrooms = listing.xpath(".//div[@class='description']//div[@class='cac']/text()").extract_first()
            bathrooms = listing.xpath(".//div[@class='description']//div[@class='sdb']/text()").get()
            price = listing.xpath(".//div[@class='description']//div[@class='price']//span/text()").get()
            url = listing.xpath(".//a[@class='a-more-detail']/@href").get()
            abs_url = f"https://www.centris.ca{url}"

            yield SplashRequest (
                    url=abs_url,
                    endpoint = 'execute',
                    callback=self.parse_summary,
                    args={
                        'lua_source': self.script
                    },
                    meta = {
                            'Category' : category,
                            'Bedrooms' : bedrooms,
                            'Bathrooms' : bathrooms,
                            'Price' : price,
                            'URL' : abs_url
                    }
            )

        count = resp_dict.get('d').get('Result').get('count')
        increment_number = resp_dict.get('d').get('Result').get('inscNumberPerPage')
        if self.positions['startPosition'] <= count:
            self.positions['startPosition'] += increment_number
            yield scrapy.Request(
            url="https://www.centris.ca/Property/GetInscriptions",
            method="POST",
            body=json.dumps(self.positions),
            headers= {
                'Content-Type': 'application/json',
                'x-requested-with': 'XMLHttpRequest',
                'x-centris-uc': 0,
                'x-centris-uck': uck
            },
            callback = self.parse
        )

    def parse_summary(self, response):

        address = response.xpath('//h2[@itemprop="address"]/text()').get()
        description = response.xpath('//div[@itemprop="description"]/text()').get()
        category = response.request.meta['Category']
        bedrooms = response.request.meta['Bedrooms']
        bathrooms = response.request.meta['Bathrooms']
        price = response.request.meta['Price']
        url = response.request.meta['URL']

        yield {
            'Address' : address,
            'Description' : description,
            'Category' : category,
            'Bedrooms' : bedrooms,
            'Bathrooms' : bathrooms,
            'Price' : price,
            'URL' : url,
            
        }

