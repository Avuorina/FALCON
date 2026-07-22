// ★キャッシュのバージョン管理★
// 静的ファイル(アイコン・manifest等)を後で更新した時は、この文字列を必ず変える
// (例: falcon-cache-v1 → falcon-cache-v2)。変えないと、ブラウザが古いキャッシュを
// 掴んだままになり、更新したはずのファイルが反映されない事態になる。
const CACHE_NAME = "falcon-cache-v1";
const OFFLINE_URL = "/static/offline.html";

// インストール時にあらかじめキャッシュしておくファイル
const PRECACHE_URLS = [
    OFFLINE_URL,
    "/static/manifest.json",
    "/static/icons/icon-192.png",
    "/static/icons/icon-512.png",
    "/static/icons/apple-touch-icon.png",
    "/static/icons/favicon-32.png",
];

self.addEventListener("install", (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE_URLS))
    );
    self.skipWaiting(); // 新しいService Workerをすぐ有効にする
});

self.addEventListener("activate", (event) => {
    // 古いバージョンのキャッシュを掃除する
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(
                keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
            )
        )
    );
    self.clients.claim();
});

self.addEventListener("fetch", (event) => {
    const url = new URL(event.request.url);

    // ★ページ本体へのナビゲーション★
    // ネットワークで取りに行き、失敗した時だけオフライン用ページを返す
    if (event.request.mode === "navigate") {
        event.respondWith(
            fetch(event.request).catch(() => caches.match(OFFLINE_URL))
        );
        return;
    }

    // ★静的ファイル(/static/配下)★
    // ネットワーク優先、失敗したらキャッシュから返す。成功時はキャッシュを更新しておく
    if (url.pathname.startsWith("/static/")) {
        event.respondWith(
            fetch(event.request)
                .then((response) => {
                    const clone = response.clone();
                    caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
                    return response;
                })
                .catch(() => caches.match(event.request))
        );
        return;
    }

    // /chat, /history, /system-stats 等のAPIリクエストには関与しない。
    // index.html側の既存のtry/catchが処理するので、ここでは何もしない。
});