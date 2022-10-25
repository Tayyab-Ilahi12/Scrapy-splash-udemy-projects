from math import prod
from pkg_resources import yield_lines
import scrapy


class ShophiveSpider(scrapy.Spider):
    name = 'shophive'
    allowed_domains = ['www.shophive.com']
    start_urls = ['http://www.shophive.com/apple']

    def parse(self, response):
        olTag = response.css("ol.product-grid")
        for product in olTag.css("li.product-item-toki"):
            yield{
                "Product Name": product.css("h3.product-name").css("a::text").extract_first(),
                "Product Link": product.css("h3.product-name").css("a::attr(href)").extract(),
                "Product Price": product.css("span.price::text").extract_first()
            }
