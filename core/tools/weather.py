import requests
import json
import os

# area_codes.jsonのファイルパス(このファイルから見た相対位置)
AREA_CODES_PATH = os.path.join(os.path.dirname(__file__), "area_codes.json")

# デフォルト地域(現在地の代わり、隼のよく行く場所)
DEFAULT_LOCATION = "瀬戸"


def get_area_code(location_name: str) -> str | None:
    """
    地名から気象庁の地域コードを検索する
    完全一致 → 部分一致の順で探す。見つからなければNoneを返す
    """
    with open(AREA_CODES_PATH, "r", encoding="utf-8") as f:
        area_data = json.load(f)

    # 完全一致でまず探す
    if location_name in area_data:
        return area_data[location_name]

    # 部分一致で探す(「名古屋市」→「名古屋」でヒットさせる)
    for key in area_data:
        if key in location_name or location_name in key:
            return area_data[key]

    return None


def get_weather(location: str = None, lat: float = None, lon: float = None) -> dict:
    """
    気象庁のデータから天気予報を取得する

    location: 地名(例: "名古屋")。指定なければデフォルト地域を使う
    lat, lon: 緯度経度(将来のスマホ対応用、現時点では未使用)
    """
    # 現時点ではlocationが無ければデフォルト地域を使う
    target_location = location if location else DEFAULT_LOCATION

    area_code = get_area_code(target_location)
    if area_code is None:
        return {"error": f"「{target_location}」の地域コードが見つかりませんでした。area_codes.jsonに追加してください。"}

    url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{area_code}.json"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # エラーがあれば例外を発生させる
        data = response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"天気データの取得に失敗しました: {e}"}

    # 気象庁JSONの構造から必要な情報を取り出す
    try:
        # data[0]が短期予報(今日・明日・明後日)のブロック
        time_series = data[0]["timeSeries"][0]
        area_name = time_series["areas"][0]["area"]["name"]
        weather_codes = time_series["areas"][0]["weathers"]  # 天気の説明文リスト
        dates = time_series["timeDefines"]  # 対応する日付リスト
    except (KeyError, IndexError) as e:
        return {"error": f"天気データの解析に失敗しました: {e}"}

    forecast = []
    for date, weather in zip(dates, weather_codes):
        forecast.append({"date": date, "weather": weather})

    return {
        "location": area_name,
        "forecast": forecast
    }


# テスト実行(このファイルを直接実行した時だけ動く)
if __name__ == "__main__":
    result = get_weather("名古屋")
    print(json.dumps(result, ensure_ascii=False, indent=2))