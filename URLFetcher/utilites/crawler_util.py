import requests
import xml.etree.ElementTree as ET
import logging
from urllib.parse import urljoin, urlparse
import hashlib

class CrawlerUtil:
    def __init__(self, logger):
        self.logger = logger

    def extract_sitemap_urls(self, sitemap_url, headers, namespace, filterBy=None):
        """
        Extract URLs from a specific sitemap
        
        Args:
            sitemap_url (str): URL of the sitemap to crawl
        
        Returns:
            list: URLs extracted from the sitemap
        """
        try:
            # Fetch sitemap
            response = requests.get(sitemap_url, headers=headers)
            response.raise_for_status()
            
            # Parse XML
            root = ET.fromstring(response.text)
            
            # Extract URLs
            urls = []
            
            # simply return all of the urls and filter if needed
            sitemapUrls = root.findall('.//ns:loc', namespace)
            urls = [url.text.strip() for url in sitemapUrls]

            self.logger.info(f"Extracted {len(urls)} URLs from sitemap {sitemap_url}")

            # filter by if needed
            if filterBy:
                urls = [url for url in urls if filterBy in url]
            
            return urls
        
        except requests.RequestException as e:
            self.logger.error(f"Error fetching sitemap {sitemap_url}: {e}")
            return []
        except ET.ParseError as e:
            self.logger.error(f"Error parsing sitemap XML: {e}")
            return []
        
        
