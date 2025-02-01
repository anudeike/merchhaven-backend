import azure.functions as func
import logging
import azure.functions as func
from azure.cosmos import CosmosClient
from azure.data.tables.aio import TableClient
from azure.data.tables import TableClient as TableClientSync
from azure.core.exceptions import AzureError
from azure.storage.queue import QueueClient
import json
import asyncio
import os
from ProductSitemapURLFetcher import ProductSitemapURLFetcher
from utilites._util_functions import url_to_hash
from datetime import datetime
import uuid

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
Table Functions
"""
def prepare_rows(urls):
    """
    Prepares the entities for batch upload by ensuring required fields.
    
    Args:
        urls: List of urls that have been fetched
        
    Returns:
        List of prepared entities
    """

    rows = []
    for url in urls:
        currentTime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        hash = url_to_hash(url)
        # initialize a new row
        rows.append({
            "PartitionKey": str(hash[:5]),
            "RowKey": str(hash),
            "URL": str(url),
            "timeCreated": str(currentTime),
            "lastFetchTime": str(currentTime),
            "lastCrawlTime": "",
            "s3Link": "",
            "depth": 0
        })

    return rows

# this is a generic upsert function
# TODO: Move this into a utility file
async def upsert(row, table_client, mode):
    try:
        await table_client.upsert_entity(row, mode=mode)
        logging.info(f"Upserted entity with URL: {row['RowKey']}")
    except Exception as e:
        logging.error(f"Error upserting entity with URL: {row['RowKey']}: {str(e)}")

async def upsert_url_metadata(rows, mode="merge"):

    # we need to get the table client here
    table = TableClient.from_connection_string(
        os.environ["AzureTableStorageConnectionString"],
        os.environ["TableName"]
    )

    # find the type of object table client is
    logging.info(type(table))

    async with table:
        try:
            await table.create_table()
        except AzureError as e:
            logging.info(f"Table already exists: {str(e)}")
        
        # create a list of tasks to upsert the entities
        tasks = [upsert(row, table, mode=mode) for row in rows]

        # wait for all tasks to complete
        await asyncio.gather(*tasks)
    

def upload_to_azure_table(productUrls):

    # Prepare the entities
    """
    Uploads a list of URLs to Azure Table Storage (async)
    
    Args:
        productUrls (list): List of URLs to upload
        
    Returns:
        None
    """
    rows = prepare_rows(productUrls)

    # upsert the entities to Azure Table Storage
    try:
        asyncio.run(upsert_url_metadata(rows=rows))
    except Exception as e:
        logging.error(f"Async Function Error: {str(e)}")

    # log the number of entities uploaded
    logging.info(f"Uploaded {len(rows)} URLs to Azure Table Storage")


def query_urls_not_crawled():
    # Initialize Table Client
    """
    Queries Azure Table Storage for entities where lastCrawlTime is NULL or empty

    Returns:
        list: List of entities from Azure Table Storage where lastCrawlTime is empty
    """
    table_client = TableClientSync.from_connection_string(
        os.environ["AzureTableStorageConnectionString"],
        os.environ["TableName"]
    )

    # Query entities where lastCrawlTime is NULL or empty
    logging.info("Querying entities where lastCrawlTime is NULL or empty...")
    parameters = {
        "lastCrawlTime": ''
    }
    filter_query = "lastCrawlTime eq @lastCrawlTime"
    entities = table_client.query_entities(query_filter=filter_query, parameters=parameters)

    return entities

def send_urls_to_queue(messages):

    queue_client = QueueClient.from_connection_string(conn_str=os.environ["AzureTableStorageConnectionString"], queue_name="urldataqueue")

    # create queue if it doesn't exist
    try:
        queue_client.create_queue()
    except Exception as e:
        logging.info(f"Queue already exists: {str(e)}")

    # send messages
    try:
        ind = 0
        for msg in messages:

            logging.info(f"Sending message to queue: {msg}")
            queue_client.send_message(msg)
            logging.info(f"Sent message to queue: {msg}")
            ind += 1

        logging.info(f'{ind} messages sent to queue')
    except Exception as e:
        logging.error(f"Error sending messages to queue: {str(e)}")
    
def create_queue_messages(entities):
    
    logging.info('Creating queue messages...')
    messages = []
    try:
        for entity in entities:
            url = entity.get("URL")
            rowKey = entity.get("RowKey")

            message = json.dumps({
                "url": url,
                "rowKey": rowKey
            })

            messages.append(message)

        logging.info('All queue messages created')
    except Exception as e:
        logging.error(f"Error creating queue messages: {str(e)}")
    
    return messages
    

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

# entry point
@app.function_name(name="URLFetcherFunction")
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
        
        response = {
            "Product Urls Discovered": len(productUrlsDiscovered),
            "Sample Product Urls": productUrlsDiscovered[:10],
            "timeCreated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        # Return response
        return func.HttpResponse(json.dumps(response), mimetype="application/json")

    except Exception as e:
        logging.error(f"Error processing domain metadata: {str(e)}")
        return func.HttpResponse(f"Error processing domain metadata: {str(e)}", status_code=500)

# Get the delta urls from the url metadata that haven't been processed yet (last crawl time is null or older than last fetch time)
@app.function_name(name="DeltaUrlsToQueueFunction")
@app.timer_trigger(schedule="0 */10 * * * *", arg_name="myTimer", run_on_startup=True, use_monitor=False) 
def timer_trigger(myTimer: func.TimerRequest) -> None:

    logging.info('DeltaUrlsToQueueFunction timer trigger function started at %s.', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # Query entities where lastCrawlTime is empty
    entities = query_urls_not_crawled()

    # create the messages
    msgs = create_queue_messages(entities)

    # Send Message to Queue
    send_urls_to_queue(msgs)
    
    logging.info('DeltaUrlsToQueueFunction timer trigger function completed at %s.', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))        