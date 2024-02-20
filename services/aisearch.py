import re
import config
import json
from services.openai import OpenAiService
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential


class AiSearchService():

    system_message_chat_conversation = """Assistant helps the customer questions. Be brief in your answers.
Answer ONLY with the facts listed in the list of sources below. If there isn't enough information below, say you don't know. Do not generate answers that don't use the sources below. If asking a clarifying question to the user would help, ask the question.
For tabular information return it as an html table. Do not return markdown format. If the question is not in English, answer in the language used in the question.
Each source has a name followed by colon and the actual information, always include the source name for each fact you use in the response. Use square brackets to reference the source, e.g. [info1.txt]. Don't combine sources, list each source separately, e.g. [info1.txt][info2.pdf].
Answer in Japanese.
"""

    def __init__(self, openai_service: OpenAiService):
        
        search_credential = AzureKeyCredential(config.settings['ai_search_api_key'])
        ai_search_endpoint = config.settings['ai_search_endpoint']
        search_client = SearchClient(
          endpoint=f'{ai_search_endpoint}',
          index_name=config.settings['ai_search_index_name'],
          credential=search_credential)
        
        self.openai_service = openai_service
        self.search_client = search_client
         
        
    def search(self, query: str, history: list[dict]) -> any:

        # クエリと会話履歴から検索用クエリ取得
        aisearch_query = self.openai_service.create_query_to_messages(query, history)
        print(aisearch_query)

        # ai search検索
        res_ai_search = self.search_client.search(aisearch_query, top=1)

        # クエリ用ソース, URL取得
        query_source, url = self.get_query_source_and_urls(res_ai_search)
        print(query_source, url)
        
        if not query_source:
            return '参考になる情報源が無いので回答できません。'

        # 回答生成依頼となるクエリを作成
        messages = [{'role': 'system', 'content': self.system_message_chat_conversation}]
        messages.append({"role": "user", "content": query + "\n\nSources:\n" + query_source})
        messages.extend(history)
        messages.append({"role": "user", "content": query})

        # 回答取得依頼
        answer = self.openai_service.get_answer(messages)
        
        # 過去会話のURLを回答に使われた場合URLが重複するため削除
        answer = re.sub("\[ドキュメントURL\]\n.+", "", answer).strip()

        if len(url) != '':
            answer += '\n[ドキュメントURL]\n' + url
        
        print(answer)

        return answer

    @staticmethod
    def get_query_ai_search(res_query_for_ai_search: dict) -> any:
        choices = res_query_for_ai_search.get('choices', [])
        if len(choices) == 0:
            return ''
        query_ai_search = choices[0].get('message', {}).get('content', '')
        return query_ai_search

    @staticmethod
    def get_query_source_and_urls(res_ai_search: dict) -> any:
        results = []
        urls_array = []
        for doc in res_ai_search:
            if not doc.get('metadata'):
                continue
            m = json.loads(doc.get('metadata'))
            if not m.get('source') or not doc.get('content') or not m.get('url'):
                continue
        
            content = doc.get('content')
            # result = m.get('source') + ': ' + content.replace('\n', ' ').replace('\r', ' ')
            result = content.replace('\n', ' ').replace('\r', ' ')
            results.append(result)
          
            urls_array.append(m.get('url'))

        urls = '\n'.join(set(urls_array))
        query_source = "\n".join(results)
        return query_source, urls

    @staticmethod
    def get_answer(res_answer: dict, urls: str) -> any:
        choices = res_answer.get('choices', [])
        if len(choices) == 0:
            return ''
        answer = choices[0].get('message', {}).get('content', '')
        answer += '[ドキュメントURL]\n' + urls
        return answer
