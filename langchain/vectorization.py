import os
from langchain.embeddings import AzureOpenAIEmbeddings
from langchain.document_loaders import PyPDFLoader, CSVLoader, Docx2txtLoader, UnstructuredPowerPointLoader, UnstructuredExcelLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain.vectorstores.azuresearch import AzureSearch
from azure.search.documents.indexes.models import (
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SimpleField
)
from dotenv import load_dotenv
load_dotenv()

import logging
import sys

# Azure OpenAIのデプロイ名
AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_NAME = os.environ.get('AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_NAME')
# Azure SearchのエンドポイントとAPIキー
AZURE_SEARCH_ENDPOINT=os.environ.get('AI_SEARCH_ENDPOINT')
AZURE_SEARCH_SERVICE_NAME=os.environ.get('AI_SEARCH_SERVICE_NAME')
AZURE_SEARCH_API_KEY_ADMIN=os.environ.get('AI_SEARCH_API_KEY')

logging.basicConfig(stream=sys.stdout, level=logging.INFO) # logging.DEBUG for more verbose output
logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))

csv_loader = CSVLoader(
    encoding='utf-8',
    file_path="langchain/mapping.csv",
    metadata_columns=["type", "name", "url"]
)
docs = csv_loader.load()
directory = "files"
documents = []
for doc in docs:
    url = doc.metadata['url']
    name = doc.metadata['name']
    type = doc.metadata['type']
    # pdf,docx,ppt,xlsx対応
    try:
        if type == "pdf":
            loader = PyPDFLoader(f'langchain/{directory}/{name}')
        elif type == "doc":
            loader = Docx2txtLoader(f'langchain/{directory}/{name}')
        elif type == "pptx":
            loader = UnstructuredPowerPointLoader(f'langchain/{directory}/{name}')
        else:
            loader = UnstructuredExcelLoader(f'langchain/{directory}/{name}', mode="elements")
        pages = loader.load_and_split()
        text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
        text = text_splitter.split_documents(pages)
        # 改行コード削除
        texts = [doc.page_content.replace('\n', '') for doc in text]
        metadatas = []
        for meta in text:
            meta.metadata['url'] = url
            metadatas.append(meta.metadata)
        document = text_splitter.create_documents(texts, metadatas)
        for split_doc in document:
            documents.append(split_doc)
    except Exception as e:
        print(e)
        
embeddings = AzureOpenAIEmbeddings(
    azure_deployment=AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_NAME,
)

# # AI Searchのインデックスを作成
fields = [
    SimpleField(
        name="id",
        type=SearchFieldDataType.String,
        key=True,
        filterable=True,
    ),
    SearchableField(
        name="content",
        type=SearchFieldDataType.String,
        searchable=True,
        analyzer_name="ja.lucene",
    ),
    SearchField(
        name="content_vector",
        type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
        searchable=True,
        vector_search_dimensions=len(embeddings.embed_query("Text")),
        vector_search_configuration="default",
        
    ),
    SearchableField(
        name="metadata",
        type=SearchFieldDataType.String,
        searchable=True,
    ),
]

# # インデックス名
index_name = os.environ.get('AI_SEARCH_INDEX_NAME')
vector_store = AzureSearch(
    azure_search_endpoint=AZURE_SEARCH_ENDPOINT,
    azure_search_key=AZURE_SEARCH_API_KEY_ADMIN,
    index_name=index_name,
    embedding_function=embeddings.embed_query,
    fields=fields
)

vector_store.add_documents(documents=documents)
