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


def resolve_location(location_name: str) -> list[dict] | None:
    """
    地名から対象区分のリストを引く。要素は {"file":.., "area":.., "label"(任意):..}
    完全一致 → 部分一致の順で探す。見つからなければNoneを返す

    通常は要素数1のリスト(例: 名古屋 → [{"file": "230000", "area": "230010"}])だが、
    豊田市のように天気予報の区分そのものをまたぐ地名は要素数2以上になる
    (aliases側で単一dictの代わりにリストとして登録してあるものをそのまま返す)。
    """
    aliases = _load_area_data()["aliases"]

    entry = None
    if location_name in aliases:
        # 完全一致でまず探す
        entry = aliases[location_name]
    else:
        # 部分一致で探す(「名古屋市」→「名古屋」でヒットさせる)
        for key in aliases:
            if key in location_name or location_name in key:
                entry = aliases[key]
                break

    if entry is None:
        return None

    # aliases側が単一dict(通常の地名)ならリストに揃える。
    # 豊田市のように最初からリストで登録されているものはそのまま
    return entry if isinstance(entry, list) else [entry]


def get_pref_name(file_code: str) -> str:
    """予報ファイルのコードから都道府県名を引く。未登録なら空文字を返す"""
    return _load_area_data()["areas"].get(file_code, "")

def _fetch_forecast(file_code: str, area_code: str) -> dict:
    """
    1つの区分(file_code + area_code)について、気象庁から予報を取って
    {"forecast": [...]} または {"error": ...} を返す。

    get_weatherから、単一区分・複数区分どちらの場合も同じ処理を呼べるように
    ここに切り出してある(豊田市のような複数区分の地名でも、この関数を
    区分の数だけ呼ぶだけで済む)。
    """
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

    forecast = [{"date": date, "weather": weather} for date, weather in zip(dates, weather_codes)]
    return {"area_name": area_name, "forecast": forecast}

def get_weather(location: str = None, lat: float = None, lon: float = None) -> dict:
    """
    気象庁のデータから天気予報を取得する

    location: 地名(例: "名古屋")。指定なければデフォルト地域を使う
    lat, lon: 緯度経度(将来のスマホ対応用、現時点では未使用)

    通常の地名は今まで通り {"location":.., "forecast": [...]} を返す。
    豊田市のように天気予報の区分そのものをまたぐ地名は、区分ごとの結果を
    {"location":.., "areas": [{"area_name":.., "forecast": [...]}, ...]} の形で返す。
    どちらの形になっているかはFALCON側が"forecast"キーの有無で判断する。
    """
    # 現時点ではlocationが無ければデフォルト地域を使う
    target_location = location if location else DEFAULT_LOCATION

    targets = resolve_location(target_location)
    if targets is None:
        return {"error": f"「{target_location}」の地域コードが見つかりませんでした。area_codes.jsonのaliasesに追加してください。"}

    areas_result = []

    for target in targets:
        file_code = target["file"]
        area_code = target["area"]
        label = target.get("label")

        # ★あえてキャッシュしない★
        # file_codeが同じでもarea_codeが違えば結果は別物になるため、
        # 「file単位でキャッシュ」は中途半端に賢くしただけで意味が薄い。
        # 通信は軽いローカルAPIではなく気象庁への実リクエストなので回数は気になるが、
        # 豊田のような複数区分の地名は稀なため、まずは単純・正直な実装を優先する
        result = _fetch_forecast(file_code, area_code)
        if "error" in result:
            return result  # 1区分でも失敗したら、黙って残りだけ返さずエラーで止める

        pref_name = get_pref_name(file_code)
        # 気象庁が返すのは「西部」のような県内区分だけなので、県名を前に付けて曖昧さをなくす
        base_name = f"{pref_name}{result['area_name']}" if pref_name else result["area_name"]
        # label(「西部」等)が指定されていれば、地名+labelの形で表示名を作る
        # (「豊田西部」のように、問い合わせた地名がそのまま分かる名前にするため)
        display_name = f"{target_location}{label}" if label else base_name

        areas_result.append({"area_name": display_name, "forecast": result["forecast"]})

    if len(areas_result) == 1:
        # 通常の地名(区分1つ)は今まで通りの形で返す
        return {"location": areas_result[0]["area_name"], "forecast": areas_result[0]["forecast"]}

    # 複数区分にまたがる地名(現状は豊田市のみ)
    return {"location": target_location, "areas": areas_result}


# テスト実行(このファイルを直接実行した時だけ動く)
if __name__ == "__main__":
    # 西部/東部が別々に取れているか確認するため、複数地点を叩く
    for name in ["名古屋", "豊橋", "浜松", "熱海", "豊田"]:
        result = get_weather(name)
        print(f"--- {name} ---")
        print(json.dumps(result, ensure_ascii=False, indent=2))