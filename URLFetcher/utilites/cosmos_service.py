import azure.functions as func
import logging
import azure.functions as func
from azure.cosmos import CosmosClient


class CosmosService():
    def __init__(self, endpoint, key):

        # Initialize the CosmosService
        """
        Initialize the CosmosService

        Args:
            endpoint (str): The endpoint for the Azure Cosmos DB
            key (str): The key for the Azure Cosmos DB
        """

        self.endpoint = endpoint
        self.key = key

        # start logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        # create the client automatically
        self.client = self.get_cosmos_client()

    def get_cosmos_client(self):
        """
        Creates and returns a CosmosClient instance for connecting to Azure Cosmos DB using the provided endpoint and key.

        Returns:
            CosmosClient: An instance of the CosmosClient to interact with Azure Cosmos DB.
        """

        client = CosmosClient(self.endpoint, self.key)
        return client
    
    def get_container_client(self, database_name, container_name):
        """
        Gets a container client for the specified database and container names.

        Args:
            database_name (str): The name of the database to get the container from.
            container_name (str): The name of the container to get.

        Returns:
            ContainerClient: An instance of the ContainerClient to interact with the specified container.
        """
        database = self.client.get_database_client(database_name)
        container = database.get_container_client(container_name)
        return container
    

# TODO: Add tests - This is a work in progress