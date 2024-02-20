import openai
import config


class OpenAiService:
    query_prompt_template = """Below is a history of the conversation so far, and a new question asked by the user that needs to be answered by searching in a knowledge base.
Generate a search query based on the conversation and the new question.
Do not include cited source filenames and document names e.g info.txt or doc.pdf in the search query terms.
Do not include any text inside [] or <<>> in the search query terms.
Do not include any special characters like '+'.
The language of the search query is generated in the language of the string described in the source question.
If you cannot generate a search query, return just the number 0.

source quesion: {user_question}
"""
    def __init__(self):
        openai.api_type = "azure"
        openai.api_base = config.settings['openai_api_base']
        openai.api_version = config.settings['openai_api_version']
        openai.api_key = config.settings['openai_api_key']

    def get_answer(self, query_history: list):
        """
        chatGptに問い合わせる
        """

        response = openai.ChatCompletion.create(
          engine=config.settings['gpt_deployment_name'],
          messages=query_history,
          temperature=0.0)
        
        choices = response.get('choices', [])
        if len(choices) == 0:
            return ''
        content = choices[0].get('message', {}).get('content', '')
        return content
      
    def create_query_to_messages(self, query: str, history: list[dict]):
        """
        クエリと会話履歴から検索用クエリを生成する
        """
        
        # user質問に対するassistant回答例をいれておくと、その形式で返してくれる
        example_assistant_answers = [
            {'role' : "user", 'content' : '出張で車移動はできますか' },
            {'role' : "assistant", 'content' : '出張 車 移動' },
            {'role' : "user", 'content' : '介護休業は何日ありますか' },
            {'role' : "assistant", 'content' : '介護休業 何日' }
        ]
        
        # クエリ生成依頼となるクエリを作成
        messages = []
        query_prompt = self.query_prompt_template.format(user_question=query)
        user_q = 'Generate search query for: ' + query
        messages = [{'role': 'system', 'content': query_prompt}]
        messages.extend(example_assistant_answers)
        messages.append({"role": "user", "content": user_q})
        messages.extend(history)
        
        query = self.get_answer(messages)
        
        return query
