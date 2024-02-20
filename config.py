import os

settings = {
    
    # slack
    'bot_token': os.environ.get('BOT_TOKEN'),
    'slack_signing_secret': os.environ.get('SLACK_SIGNING_SECRET'),
    'bot_token_ai_search': os.environ.get('BOT_TOKEN_AI_SEARCH'),
    'slack_signing_secret_ai_search': os.environ.get('SLACK_SIGNING_SECRET_AI_SEARCH'),

    # chatgpt
    'openai_api_base': os.environ.get('OPENAI_API_BASE'),
    'openai_api_version': os.environ.get('OPENAI_API_VERSION'),   
    'openai_api_key': os.environ.get('OPENAI_API_KEY'),
    'gpt_deployment_name': os.environ.get('GPT_DEPLOYMENT_NAME'),
    'gpt_deployment_model': os.environ.get('GPT_DEPLOYMENT_MODEL'),
    
    # cosmos db
    'cosmos_db_host': os.environ.get('COSMOS_DB_HOST'),
    'cosmos_db_master_key': os.environ.get('COSMOS_DB_MASTER_KEY'),
    'cosmos_db_id': os.environ.get('COSMOS_DB_ID'),
    'cosmos_db_container_id': os.environ.get('COSMOS_DB_CONTAINER_ID'),

    # ai search
    'ai_search_api_key': os.environ.get('AI_SEARCH_API_KEY'),
    'ai_search_endpoint': os.environ.get('AI_SEARCH_ENDPOINT'),
    'ai_search_service_name': os.environ.get('AI_SEARCH_SERVICE_NAME'),
    'ai_search_index_name': os.environ.get('AI_SEARCH_INDEX_NAME'),

}
