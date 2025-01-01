import azure.functions as func
import logging
import azure.functions as func
from azure.cosmos import CosmosClient
from azure.data.tables import TableServiceClient, TableClient
from azure.core.exceptions import AzureError
import json
import os
from ProductSitemapURLFetcher import ProductSitemapURLFetcher
from utilites._util_functions import url_to_hash


app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

"""
 Utility Functions
"""
def get_cosmos_client():
    """
    Creates and returns a CosmosDB client and container client.
    
    Returns:
        container_client: CosmosDB container client
    """
    endpoint = os.environ["CosmosEndpoint"]
    key = os.environ["CosmosKey"]
    database_name = os.environ["CosmosDatabase"]
    container_name = os.environ["CosmosContainer"]

    client = CosmosClient(endpoint, key)
    database = client.get_database_client(database_name)
    container = database.get_container_client(container_name)
    
    return container

def get_cosmos_items(container, query_id=None, max_items=100, isEnabled=True):
    """
    Retrieves items from CosmosDB.
    
    Args:
        container: CosmosDB container client
        query_id (str, optional): Specific ID to query for
        max_items (int, optional): Maximum number of items to return when querying all

    Returns:
        list: List of dictionaries containing the query results
    """
    try:
        if query_id:
            query = f"SELECT * FROM c WHERE c.id = '{query_id}'"
            items = list(container.query_items(
                query=query,
                enable_cross_partition_query=True
            ))
        else:
            #  only select those that are enabled
            query = f"SELECT * FROM c WHERE c.isEnabled = {str.lower(str(isEnabled))}"
            items = list(container.query_items(
                query=query,
                enable_cross_partition_query=True
            ))
        return [dict(item) for item in items]
    
    except Exception as e:
        logging.error(f"Error retrieving items from CosmosDB: {str(e)}")
        raise

"""
Azure Table Storage functions
"""

def get_table_client() -> TableClient:
    """
    Creates and returns an Azure Table Storage client.
    
    Returns:
        TableClient: Azure Table Storage client
    """
    connection_string = os.environ["AzureTableStorageConnection"]
    table_name = os.environ["TableName"]
    
    # Create the table if it doesn't exist
    table_service = TableServiceClient.from_connection_string(connection_string)
    try:
        table_client = table_service.create_table(table_name)
    except Exception:
        table_client = table_service.get_table_client(table_name)
    return table_client

def prepare_entities(urls):
    """
    Prepares the entities for batch upload by ensuring required fields.
    
    Args:
        data: List of dictionaries containing the data to upload
        
    Returns:
        List of prepared entities
    """
    entities = []
    for i, item in enumerate(data):
        if 'PartitionKey' not in item or 'RowKey' not in item:
            # If PartitionKey and RowKey are not provided, generate them
            item['PartitionKey'] = str(i // 1000)  # Group items into partitions of 1000
            item['RowKey'] = str(i)
        entities.append(item)
    return entities

def process_sitemap(domainMetadata):

    productUrlsResult = []

    # go thru each of the domains and print them out
    for metadata in domainMetadata:
        domainId = metadata['id']
        baseUrl = metadata['base_url']
        sitemapURLs = metadata['sitemap_urls']

        logging.info(f"Processing Domain: {domainId} with Base URL: {baseUrl}")

        for sitemapUrl in sitemapURLs:
            logging.info(f"[{domainId}] Processing Sitemap URL: {sitemapUrl}")

            # create the config object
            urlFetcherConfig = {
                'base_url': baseUrl,
                'sitemap_url': sitemapUrl,
                'namespace': {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'},
                'headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
                }
            }
            
            logging.info(f"[{domainId}] URL Fetcher Config: {urlFetcherConfig}")

            # Create the Product Sitemap URL Fetcher
            productSitemapURLFetcher = ProductSitemapURLFetcher(urlFetcherConfig)

            # Get all of the product sitemap URLs
            productUrls = productSitemapURLFetcher.fetch_product_urls()

            logging.info(f"[{domainId}] Sitemap URL: {sitemapUrl} has completed processing.\nFound {len(productUrls)} products")

            # extend the list of product URLs
            productUrlsResult.extend(productUrls)



    return productUrlsResult


def upload_to_azure_table(productUrls):

    # Create the Azure Table Storage client
    table_client = get_table_client()

    # Prepare the entities
    entities = prepare_entities(productUrls)

    # Upload the entities to Azure Table Storage
    table_client.upsert_entities(entities)
    pass
    

@app.route(route="URLFetcherFunc")
def URLFetcherFunc(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    try:
        # Initialize Cosmos client
        container = get_cosmos_client()

        # Get query parameters
        query_id = req.params.get('query')

        # Get items from CosmosDB
        domainMetadata = get_cosmos_items(container, query_id)

        # Process in the Domain Metadata
        productUrlsDiscovered = process_sitemap(domainMetadata)
        logging.info(f"Found {len(productUrlsDiscovered)} total product URLs")

        # Upload to Azure Table Storage
        # upload_to_azure_table(productUrlsDiscovered)

        # Return response
        return func.HttpResponse(json.dumps(productUrlsDiscovered), mimetype="application/json")

    except Exception as e:
        logging.error(f"Error processing domain metadata: {str(e)}")
        return func.HttpResponse(f"Error processing domain metadata: {str(e)}", status_code=500)