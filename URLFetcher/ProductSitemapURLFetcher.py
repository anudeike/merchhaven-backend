import requests
import xml.etree.ElementTree as ET
import logging
from urllib.parse import urljoin, urlparse
from utilites.crawler_util import CrawlerUtil

class ProductSitemapURLFetcher:
    def __init__(self, config=None):

        # Initialize the ProductSitemapURLFetcher
        self.base_url = config['base_url']
        self.sitemap_url = config['sitemap_url']
        self.namespace = config['namespace']
        self.headers = config['headers']
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        self.util = CrawlerUtil(self.logger)
    
    def get_product_sitemap_urls(self):
        """
        Get all of the product sitemap URLs
        
        Returns:
            list: URLs of product-specific sitemaps
        """
        productSitemapUrls = self.util.extract_sitemap_urls(sitemap_url=self.sitemap_url, 
                                                  namespace=self.namespace, 
                                                  headers=self.headers,
                                                  filterBy='product')
        
        logging.info(f"Found {len(productSitemapUrls)} product sitemaps")

        return productSitemapUrls
    
    def get_product_urls(self, productSitemapUrls):
        """
        Get all of the product URLs
        
        Returns:
            list: URLs of products
        """

        productUrls = []
        for productSitemapUrl in productSitemapUrls:
            logging.info(f"Processing product sitemap: {productSitemapUrl}")

            pUrl = self.util.extract_sitemap_urls(sitemap_url=productSitemapUrl, 
                                                  namespace=self.namespace, 
                                                  headers=self.headers)
            
            productUrls.extend(pUrl)

        logging.info(f"Found {len(productUrls)} products")

        return productUrls
    
    def fetch_product_urls(self):
        """
        Fetch all of the product URLs
        
        Returns:
            list: URLs of products
        """
        productSitemapUrls = self.get_product_sitemap_urls()
        productUrls = self.get_product_urls(productSitemapUrls)

        return productUrls


# TODO: Add tests
def testURLConfigurations(config):

    crawler = ProductSitemapURLFetcher(config)

    # one function to do all of the work
    crawler.fetch_product_urls()


boxLunchConfig = {
        'base_url': 'https://www.boxlunch.com/',
        'sitemap_url': 'https://www.boxlunch.com/sitemap_index.xml',
        'namespace': {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'},
        'headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    }

entertainmentEarthConfig = {
        'base_url': 'https://www.entertainmentearth.com/',
        'sitemap_url': 'https://www.entertainmentearth.com/sitemap/sitemap_index.xml',
        'namespace': {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'},
        'headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    }

enchancedHeaders = {
    "authority": "www.google.com",
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-language": "en-US,en;q=0.9",
    "cache-control": "max-age=0",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
}

entertainmentEarthConfig['headers'] = enchancedHeaders

# test
testURLConfigurations(entertainmentEarthConfig)