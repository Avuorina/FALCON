import time

import psutil

# NET(ネットワーク使用率)の「100%」とみなす基準値。
# 実際の回線速度を表すものではなく、バー表示用の暫定的な目安。
# 体感に合わなければこの値を調整すればいい。
_NET_REFERENCE_BYTES_PER_SEC = 2 * 1024 * 1024  # 2MB/秒

# 直前に計測した(時刻, 累計バイト数)を覚えておくためのモジュール変数。
# NETは「瞬間の値」ではなく「前回からの増加量÷経過時間」でしか出せないため必要
_last_net_sample: tuple[float, int] | None = None


def get_system_stats() -> dict:
    """CPU/メモリ/ネットワークの使用状況をパーセンテージで返す。

    cpu: psutil.cpu_percent(interval=None) を使う。
         intervalを指定すると呼び出しがその秒数だけブロックしてしまうため、
         意図的にNoneにして「前回のこの関数呼び出しからの変化率」を返す方式にしている。
         定期的にポーリングされる前提(index.htmlが2秒おきに叩く)なので、これで十分機能する。
    mem: psutil.virtual_memory().percent をそのまま使う。
    net: 送受信バイト数の合計の増加量を、経過時間で割って速度(バイト/秒)を出し、
         _NET_REFERENCE_BYTES_PER_SEC に対する割合として返す(100%で頭打ち)。
    """
    global _last_net_sample

    cpu = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory().percent

    now = time.time()
    counters = psutil.net_io_counters()
    total_bytes = counters.bytes_sent + counters.bytes_recv

    net_percent = 0.0
    if _last_net_sample is not None:
        prev_time, prev_total = _last_net_sample
        elapsed = now - prev_time
        if elapsed > 0:
            rate = (total_bytes - prev_total) / elapsed  # バイト/秒
            net_percent = min(100.0, (rate / _NET_REFERENCE_BYTES_PER_SEC) * 100)

    _last_net_sample = (now, total_bytes)

    return {
        "cpu": round(cpu, 1),
        "mem": round(mem, 1),
        "net": round(net_percent, 1),
    }