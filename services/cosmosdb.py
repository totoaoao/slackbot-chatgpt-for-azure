
import config
import azure.cosmos.cosmos_client as cosmos_client

class CosmosDBService:
    def __init__(self) -> None:
        HOST = config.settings['cosmos_db_host']
        MASTER_KEY = config.settings['cosmos_db_master_key']
        DATABASE_ID = config.settings['cosmos_db_id']
        CONTAINER_ID = config.settings['cosmos_db_container_id']
        
        client = cosmos_client.CosmosClient(HOST, {'masterKey': MASTER_KEY}, user_agent="CosmosDBPythonQuickstart", user_agent_overwrite=True)
        db = client.get_database_client(DATABASE_ID)
        self.container = db.get_container_client(CONTAINER_ID)
        
    def insertItems(self, items):
        self.container.create_item(body=items)

    def query_items(self, partition_key):
        items = list(self.container.query_items(
            query="SELECT * FROM c WHERE c.partitionKey=@partition_key",
            parameters=[
                { "name":"@partition_key", "value": partition_key }
            ]
        ))
        return items
