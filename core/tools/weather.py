import requests
import json
import os

# area_codes.jsonのファイルパス(このファイルから見た相対位置)
AREA_CODES_PATH = os.path.join(os.path.dirname(__file__), "area_codes.json")

# デフォルト地域(現在地の代わり、隼のよく行く場所)
DEFAULT_LOCATION = "瀬戸"


def _load_area_data() -> dict:
    """area_codes.json を読み込む"""
    with open(AREA_CODES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def resolve_location(location_name: str) -> dict | None:
    """
    地名から {"file": 予報ファイルのコード, "area": 県内の区分コード} を引く
    完全一致 → 部分一致の順で探す。見つからなければNoneを返す
    """
    aliases = _load_area_data()["aliases"]

    # 完全一致でまず探す
    if location_name in aliases:
        return aliases[location_name]

    # 部分一致で探す(「名古屋市」→「名古屋」でヒットさせる)
    for key in aliases:
        if key in location_name or location_name in key:
            return aliases[key]

    return None


def get_pref_name(file_code: str) -> str:
    """予報ファイルのコードから都道府県名を引く。未登録なら空文字を返す"""
    return _load_area_data()["areas"].get(file_code, "")


def get_weather(location: str = None, lat: float = None, lon: float = None) -> dict:
    """
    気象庁のデータから天気予報を取得する

    location: 地名(例: "名古屋")。指定なければデフォルト地域を使う
    lat, lon: 緯度経度(将来のスマホ対応用、現時点では未使用)
    """
    # 現時点ではlocationが無ければデフォルト地域を使う
    target_location = location if location else DEFAULT_LOCATION

    target = resolve_location(target_location)
    if target is None:
        return {"error": f"「{target_location}」の地域コードが見つかりませんでした。area_codes.jsonのaliasesに追加してください。"}

    file_code = target["file"]   # 予報ファイル(府県予報区)のコード 例: 230000
    area_code = target["area"]   # 県内の区分(一次細分区域)のコード 例: 230010
    pref_name = get_pref_name(file_code)

    url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{file_code}.json"

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
        dates = time_series["timeDefines"]  # 対応する日付リスト

        # ★区分コードで該当エリアを探す★
        # 気象庁のareasの並び順は当てにできない(静岡は 中部→西部→東部→伊豆 でコード順ですらない)
        target_area = None
        for a in time_series["areas"]:
            if a["area"]["code"] == area_code:
                target_area = a
                break

        # 見つからなければエラーにする。areas[0]にフォールバックしないこと。
        # 「別の場所の天気を、正しい顔で返す」のが最悪の失敗だから、黙って代替しない
        if target_area is None:
            return {"error": f"区分コード {area_code} が {file_code} の予報データ内に見つかりませんでした。area_codes.jsonを確認してください。"}

        area_name = target_area["area"]["name"]
        weather_codes = target_area["weathers"]  # 天気の説明文リスト
    except (KeyError, IndexError) as e:
        return {"error": f"天気データの解析に失敗しました: {e}"}

    forecast = []
    for date, weather in zip(dates, weather_codes):
        forecast.append({"date": date, "weather": weather})

    # 気象庁が返すのは「西部」のような県内区分だけなので、県名を前に付けて曖昧さをなくす
    # 県名が未登録(空文字)なら、区分名だけで返す
    full_name = f"{pref_name}{area_name}" if pref_name else area_name

    return {
        "location": full_name,
        "forecast": forecast
    }


# テスト実行(このファイルを直接実行した時だけ動く)
if __name__ == "__main__":
    # 西部/東部が別々に取れているか確認するため、複数地点を叩く
    for name in ["名古屋", "豊橋", "浜松", "熱海"]:
        result = get_weather(name)
        print(f"--- {name} ---")
        print(json.dumps(result, ensure_ascii=False, indent=2))