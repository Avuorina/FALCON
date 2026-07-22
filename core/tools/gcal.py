from datetime import datetime, timedelta
from googleapiclient.discovery import build

from core.tools.google_auth import get_calendar_credentials


def get_calendar_service():
    """
    Google Calendar APIを叩くための「サービスオブジェクト」を作る。
    これを経由して予定の取得・作成などを行う。
    """
    creds = get_calendar_credentials()
    return build("calendar", "v3", credentials=creds)

def list_events(days: int = 7, max_results: int = 10) -> dict:
    """
    今日から指定日数分の予定を取得する。

    days:        何日先まで見るか(デフォルト7日)
    max_results: 取得する予定の最大件数
    """
    service = get_calendar_service()

    # 「今」を基準に、探索範囲を決める
    now = datetime.utcnow()
    time_min = now.isoformat() + "Z"
    time_max = (now + timedelta(days=days)).isoformat() + "Z"

    try:
        result = service.events().list(
            calendarId="primary",
            timeMin=time_min,
            timeMax=time_max,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        ).execute()
    except Exception as e:
        return {"error": f"予定の取得に失敗しました: {e}"}

    events = result.get("items", [])

    formatted = []
    for event in events:
        start = event["start"].get("dateTime", event["start"].get("date"))
        formatted.append({
            "summary": event.get("summary", "(タイトルなし)"),
            "start": start,
            "id": event.get("id"),
        })

    return {"events": formatted}

def create_event(summary: str, start: str, end: str, description: str = "") -> dict:
    """
    Googleカレンダーに新しい予定を作成する。

    summary:     予定のタイトル
    start:       開始日時。ISO 8601形式(例: "2026-07-21T14:00:00")
    end:         終了日時。同じくISO 8601形式
    description: 予定の説明(任意)
    """
    service = get_calendar_service()

    event_body = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": start, "timeZone": "Asia/Tokyo"},
        "end": {"dateTime": end, "timeZone": "Asia/Tokyo"},
    }

    try:
        result = service.events().insert(calendarId="primary", body=event_body).execute()
    except Exception as e:
        return {"error": f"予定の作成に失敗しました: {e}"}

    return {
        "id": result.get("id"),
        "summary": result.get("summary"),
        "start": result.get("start", {}).get("dateTime"),
        "link": result.get("htmlLink"),
    }