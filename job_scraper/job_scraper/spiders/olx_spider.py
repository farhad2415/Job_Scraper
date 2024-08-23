import scrapy

class OlxSpider(scrapy.Spider):
    name = 'olx'
    allowed_domains = ['olx.in']
    start_urls = ['https://www.olx.in']

    def parse(self, response):
        # Extract job data here
        pass
