import requests
import xml.etree.ElementTree as ET
import logging
from urllib.parse import urljoin, urlparse

def extract_sitemap_urls(self, sitemap_url, headers):
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
            
            # Namespace handling
            namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            
            # Extract URLs
            urls = []
            
            # Check if it's a sitemap index or a regular sitemap
            if root.tag.endswith('sitemapindex'):
                # If it's a sitemap index, return the sitemap locations
                sitemap_locs = root.findall('.//ns:loc', namespace)
                urls = [loc.text.strip() for loc in sitemap_locs]
            else:
                # If it's a regular sitemap, extract URL locations
                url_elements = root.findall('.//ns:loc', namespace)
                urls = [url.text.strip() for url in url_elements]
            
            return urls
        
        except requests.RequestException as e:
            self.logger.error(f"Error fetching sitemap {sitemap_url}: {e}")
            return []
        except ET.ParseError as e:
            self.logger.error(f"Error parsing sitemap XML: {e}")
            return []