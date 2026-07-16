import os
from dotenv import load_dotenv
from anthropic import Anthropic

# .envファイルの中身を読み込む
load_dotenv()

# APIキーを使ってClaudeのクライアント(接続窓口)を作る
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def ask_claude(user_message: str) -> str:
    """
    ユーザーのメッセージをClaudeに送って、返事を受け取る関数
    """
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        messages=[
            {"role": "user", "content": user_message}
        ]
    )
    return response.content[0].text

# テスト実行(このファイルを直接実行した時だけ動く)
if __name__ == "__main__":
    reply = ask_claude("こんにちは、FALCON")
    print(reply)