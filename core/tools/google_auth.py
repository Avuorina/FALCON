import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# 読み書き権限。予定の閲覧・作成・変更・削除まで含む
SCOPES = ["https://www.googleapis.com/auth/calendar"]

# このファイルから見て2つ上がプロジェクト直下 → config/
CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "config")
CLIENT_SECRET_PATH = os.path.join(CONFIG_DIR, "google_client_secret.json")
TOKEN_PATH = os.path.join(CONFIG_DIR, "google_token.json")

def get_calendar_credentials() -> Credentials:
    """
    Google Calendarへのアクセスに使う認証情報(Credentials)を用意する。

    優先順位:
    1. 既存のトークン(google_token.json)があればそれを使う
    2. 期限切れなら自動更新(refresh)する
    3. どちらも無理なら、ブラウザを開いて隼に許可を求める(初回のみ)
    """
    creds = None

    # 1. 既にトークンファイルがあれば読み込む(2回目以降はここで済む)
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    # 2. トークンが無い、または失効していたら対処する
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # 期限切れだが refresh_token があれば、ブラウザを開かずに更新できる
            creds.refresh(Request())
        else:
            # トークンが1度も無い(初回) → ブラウザでの同意フローを回す
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_PATH, SCOPES)
            creds = flow.run_local_server(port=0)

        # 更新・新規取得した認証情報を保存する(次回以降ブラウザを開かずに済むように)
        with open(TOKEN_PATH, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

    return creds

