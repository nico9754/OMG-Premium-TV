#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Resolver per dlhd.pk - usa EasyProxy su Hugging Face
# Versione 4.0.0
#

import sys
import json
import requests
from urllib.parse import urlparse

RESOLVER_VERSION = "4.0.0"

# URL del tuo Space HuggingFace
EASYPROXY_BASE = "https://jizko249-stremio.hf.space"

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://dlhd.pk/",
    "Origin": "https://dlhd.pk",
}


def resolve_with_easyproxy(url):
    """Usa EasyProxy HF per estrarre il vero stream da dlhd"""
    try:
        print(f"[RESOLVER] Chiamo EasyProxy extractor per: {url}", file=sys.stderr)

        # Chiama l'extractor con host=dlhd e redirect_stream=false per avere JSON
        extractor_url = f"{EASYPROXY_BASE}/extractor/video"
        params = {
            "d": url,
            "host": "dlhd",
            "redirect_stream": "false"
        }
        resp = requests.get(extractor_url, params=params, timeout=30)

        if resp.status_code == 200:
            try:
                data = resp.json()
                print(f"[RESOLVER] EasyProxy risposta: {json.dumps(data)[:300]}", file=sys.stderr)

                # Cerca stream_url o url nella risposta
                stream_url = (
                    data.get("stream_url") or
                    data.get("url") or
                    data.get("resolved_url") or
                    data.get("direct_url")
                )

                if stream_url and stream_url.startswith("http"):
                    print(f"[RESOLVER] Stream trovato: {stream_url}", file=sys.stderr)
                    # Prendi anche gli header se presenti
                    headers = data.get("headers", {})
                    return stream_url, headers

            except Exception as e:
                print(f"[RESOLVER] Errore parsing JSON: {e} - risposta: {resp.text[:200]}", file=sys.stderr)

        else:
            print(f"[RESOLVER] EasyProxy status: {resp.status_code} - {resp.text[:200]}", file=sys.stderr)

    except Exception as e:
        print(f"[RESOLVER] Errore EasyProxy: {e}", file=sys.stderr)

    return None, {}


def resolve_with_proxy_manifest(url):
    """Fallback: usa il proxy manifest diretto di EasyProxy"""
    try:
        print(f"[RESOLVER] Provo proxy/manifest per: {url}", file=sys.stderr)
        proxy_url = f"{EASYPROXY_BASE}/proxy/manifest.m3u8?url={url}&host=dlhd"
        # Verifica che l'URL risponda
        resp = requests.head(proxy_url, timeout=15, allow_redirects=True)
        if resp.status_code in [200, 302, 301]:
            print(f"[RESOLVER] proxy/manifest OK: {proxy_url}", file=sys.stderr)
            return proxy_url
    except Exception as e:
        print(f"[RESOLVER] Errore proxy/manifest: {e}", file=sys.stderr)
    return None


def _build_headers(referer_url, extra_headers=None):
    parsed = urlparse(referer_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    headers = {
        "User-Agent": BROWSER_HEADERS["User-Agent"],
        "Referer": referer_url,
        "Origin": origin,
    }
    if extra_headers:
        headers.update(extra_headers)
    return headers


def resolve_link(url, headers=None, channel_name=None):
    """Funzione principale chiamata da OMG Premium TV"""
    print(f"[RESOLVER] Risoluzione: {url} (canale: {channel_name})", file=sys.stderr)

    if 'dlhd' not in url and 'watch.php' not in url and 'stream-' not in url:
        print(f"[RESOLVER] Non è un link dlhd, uso originale", file=sys.stderr)
        final_headers = headers.copy() if headers else {}
        if 'User-Agent' not in final_headers:
            final_headers['User-Agent'] = BROWSER_HEADERS['User-Agent']
        return {"resolved_url": url, "headers": final_headers}

    # Prova extractor JSON
    stream_url, stream_headers = resolve_with_easyproxy(url)

    # Fallback: proxy manifest diretto
    if not stream_url:
        print(f"[RESOLVER] Extractor fallito, provo proxy manifest", file=sys.stderr)
        stream_url = resolve_with_proxy_manifest(url)
        stream_headers = {}

    # Ultimo fallback
    if not stream_url:
        print(f"[RESOLVER] Tutti i metodi falliti, uso originale", file=sys.stderr)
        stream_url = url

    return {
        "resolved_url": stream_url,
        "headers": _build_headers(url, stream_headers)
    }


def main():
    if len(sys.argv) < 2:
        print("Uso: python3 dlhd_resolver.py [--check|--resolve input.json output.json]")
        sys.exit(1)

    if sys.argv[1] == "--check":
        print("resolver_ready: True")
        sys.exit(0)

    if sys.argv[1] == "--resolve" and len(sys.argv) >= 4:
        input_file = sys.argv[2]
        output_file = sys.argv[3]
        try:
            with open(input_file, 'r') as f:
                input_data = json.load(f)

            url = input_data.get('url', '')
            headers = input_data.get('headers', {})
            channel_name = input_data.get('channel_name', 'unknown')

            result = resolve_link(url, headers, channel_name)

            with open(output_file, 'w') as f:
                json.dump(result, f, indent=2)

            print(f"[RESOLVER] Risultato salvato in: {output_file}", file=sys.stderr)
            sys.exit(0)

        except Exception as e:
            print(f"[RESOLVER] Errore: {e}", file=sys.stderr)
            sys.exit(1)

    print("Comando non valido")
    sys.exit(1)


if __name__ == "__main__":
    main()
