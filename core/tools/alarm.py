from urllib.parse import quote

# iPhone側で作成済みのショートカット名と一致させる必要がある
SHORTCUT_NAME = "FalconAlarm"


def build_alarm_url(time: str) -> dict:
    """
    HH:MM形式の時刻から、iPhone側のショートカット「FalconAlarm」を起動するURLを組み立てる。

    ★このURLを実際に開くのはiPhone側(ブラウザ)であって、サーバー側ではない★
    ここではURL文字列を作って返すだけ。アラームをセットする実処理は
    iPhone側のショートカットアプリ(FalconAlarm)が担う。
    """
    encoded_time = quote(time)  # 念のためURLエンコード(":"はそのままでも動くが、崩れる環境を考慮)
    url = f"shortcuts://run-shortcut?name={SHORTCUT_NAME}&input=text&text={encoded_time}"
    return {"time": time, "url": url}