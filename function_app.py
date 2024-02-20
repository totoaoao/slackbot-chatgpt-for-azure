from dotenv import load_dotenv
load_dotenv()
import re
import uuid
import config
import azure.functions as func
from slack_bolt import App
from slack_bolt.adapter.fastapi import SlackRequestHandler
from fastapi import FastAPI, Request
from azure.storage.blob import BlobServiceClient
from services.aisearch import AiSearchService
from services.cosmosdb import CosmosDBService
from services.openai import OpenAiService
import logging
import sys

logging.basicConfig(stream=sys.stdout, level=logging.INFO) # logging.DEBUG for more verbose output
logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))

# 初期化
fast_app = FastAPI()
cosmos_db_service = CosmosDBService()
openai_service = OpenAiService()
aisearch_service = AiSearchService(openai_service)

slack_app = App(token=config.settings['bot_token'], signing_secret=config.settings['slack_signing_secret'])
slack_handler = SlackRequestHandler(slack_app)
slack_app_ai_search = App(token=config.settings['bot_token_ai_search'], signing_secret=config.settings['slack_signing_secret_ai_search'])
slack_handler_ai_search = SlackRequestHandler(slack_app_ai_search)


@fast_app.post("/")
async def any_route(request: Request):
    """
    通常質問用
    slackリクエストを受信する
    request: object
    """

    if is_retry(request):
        return
    
    # command_handlerへ
    return await slack_handler.handle(request)

@slack_app.event("app_mention")
def command_handler(body: dict, say: object):
    """
    通常質問用
    スレッドコメントをChatGPT問い合わせしてSlackに返答する
    """

    comment, thread_ts, channel = get_comment_and_thread_ts_and_channel(body)
    comment = re.sub(r"^<@(.+?)>", "", comment).strip()

    # 対象チャネルの対象スレッド内の会話履歴取得
    partition = channel + '_' + thread_ts
    query_history = get_history(partition)

    # 今回の質問を追加
    query_history.append({'role': 'user','content': comment})

    answer = openai_service.get_answer(query_history)

    # 今回スレッドコメント、ChatGPT回答を会話履歴にインサート
    save_query_to_history(answer, partition, body)

    # Slackに返答
    say(text=answer, thread_ts=thread_ts, channel=channel)
    return

@fast_app.post("/ai_search")
async def any_route_ai_search(request: Request):
    """
    aisearch検索用
    slackリクエストを受信する
    request: object
    """

    if is_retry(request):
        return
    
    # command_handler_ai_searchへ
    return await slack_handler_ai_search.handle(request)

@slack_app_ai_search.event("app_mention")
def command_handler_ai_search(body: dict, say: object):
    """
    aisearch検索用
    スレッドコメントをChatGPT問い合わせしてSlackに返答する
    """

    comment, thread_ts, channel = get_comment_and_thread_ts_and_channel(body)
    comment = re.sub(r"^<@(.+?)>", "", comment).strip()

    # 対象チャネルの対象スレッド内の会話履歴取得
    partition = channel + '_' + thread_ts
    query_history = get_history(partition)
    
    answer = aisearch_service.search(comment, query_history)

    # 今回スレッドコメント、ChatGPT回答を会話履歴にインサート
    save_query_to_history(answer, partition, body)

    # Slackに返答
    say(text=answer, thread_ts=thread_ts, channel=channel)
    return

def is_retry(request: Request):
    """
    リトライリクエスト判定
      slackは3秒以上レスポンスがないと再リクエストを数回送ってくる
      のでリトライは無視できるようにする
    request: object
    """
    # ヘッダーにX-Slack-Retry-Numキーが存在する=リトライによるリクエストとなる
    headers = request.get('headers', [])
    for k, _ in headers:
        if k == b'x-slack-retry-num':
            return True
    return False

def get_comment_and_thread_ts_and_channel(body: dict):
    """
    slackコメント,スレッドタイムスタンプ,チャネルを取得する
    """
    query = body.get('event', {}).get('text', None)
    thread_ts = body.get('event', {}).get('thread_ts', None) or body.get('event', {}).get('ts', None) or body.get('event', {}).get('event_ts', None)
    channel = body.get('event', {}).get('channel', None)

    if query is None or thread_ts is None or channel is None:
        raise ValueError("Invalid value")
    return query, thread_ts, channel

def get_history(partition: str):
    """
    会話履歴を取得する
    """

    # 対象チャネルの対象スレッド内の会話履歴をDBから取得
    items = cosmos_db_service.query_items(partition)

    history = []
    for item in items:
        history.append({'role': 'user','content': item.get('event', {}).get('text', '')})
        history.append({'role': 'assistant','content': item.get('chatgpt_answer', '')})
    return history
  
def save_query_to_history(answer: str, partition: str, body: dict):
  """
  クエリを会話履歴に保存する
  """
  insert_body = body.copy()
  insert_body['id'] = str(uuid.uuid4())
  insert_body['chatgpt_answer'] = answer
  insert_body['partitionKey'] = partition
  insert_body['event']['text'] = re.sub(r"^<@(.+?)>", "", insert_body.get('event', {}).get('text', '')).strip()
  cosmos_db_service.insertItems(insert_body)

app = func.AsgiFunctionApp(app=fast_app, http_auth_level=func.AuthLevel.FUNCTION)