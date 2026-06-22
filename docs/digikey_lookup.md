# Digi-Key 部品情報取得ツール

`tools/digikey_lookup.py` は、部品型番から Digi-Key の価格、在庫、主要スペック、データシート URL を取得して JSON で返す Python CLI です。

Web 商品ページを直接スクレイピングせず、公式の Digi-Key Product Information V4 API を使います。価格と在庫は変動するため、BOM や部品選定に使う場合は取得日時とキャッシュ状態も出力に含めます。

## 事前準備

Digi-Key Developer Portal でアプリケーションを作成し、Product Information V4 を利用できる状態にします。

このプロジェクトでは、リポジトリルートの `.env` を `tools/digikey_lookup.py` が起動時に自動読み込みします。

`.env` の例:

```sh
DIGIKEY_CLIENT_ID="..."
DIGIKEY_CLIENT_SECRET="..."
DIGIKEY_ACCOUNT_ID="..."   # 2-legged OAuth で必要になる場合がある
DIGIKEY_ENV="production"   # production または sandbox
```

既存の `.env` が以下の短いキー名になっている場合も、そのまま読み込めます。

```sh
CLIENT_ID="..."
CLIENT_SECRET="..."
ACCOUNT_ID="..."
```

同じキーがすでにシェルの環境変数として設定されている場合は、シェル側の値を優先し、`.env` の値では上書きしません。

一時的にターミナルで設定する場合は、従来通り `export` も使えます。

```sh
export DIGIKEY_CLIENT_ID="..."
export DIGIKEY_CLIENT_SECRET="..."
export DIGIKEY_ACCOUNT_ID="..."   # 2-legged OAuth で必要になる場合がある
```

日本向けの価格確認を前提に、デフォルトは `site=JP`、`language=ja`、`currency=JPY` です。

必要に応じて以下も指定できます。

`.env` に書く場合:

```sh
DIGIKEY_SITE="JP"
DIGIKEY_LANGUAGE="ja"
DIGIKEY_CURRENCY="JPY"
DIGIKEY_CACHE_DIR=".cache/digikey"
```

ターミナルで一時指定する場合:

```sh
export DIGIKEY_ENV="production"    # production または sandbox
export DIGIKEY_SITE="JP"
export DIGIKEY_LANGUAGE="ja"
export DIGIKEY_CURRENCY="JPY"
export DIGIKEY_CACHE_DIR=".cache/digikey"
```

## 単体の型番を取得

```sh
python tools/digikey_lookup.py part TPS40210DGQR --quantity 5 --pretty
```

Digi-Key 品番で指定する方が曖昧さが少ないです。

```sh
python tools/digikey_lookup.py part 296-26969-1-ND --pretty
```

メーカー型番が複数メーカーで衝突する場合は、Digi-Key の manufacturer ID を補助指定します。

```sh
python tools/digikey_lookup.py part CR2032 --manufacturer-id 299 --pretty
```

## BOM CSV をまとめて取得

既存の Digi-Key BOM 形式の列名を自動検出します。

```sh
python tools/digikey_lookup.py bom bom/nixie_clock_integrated_digikey_bom.csv \
  --output build/digikey_lookup.json \
  --pretty
```

検出対象の主な列名:

- `Digi-Key Part Number`
- `Manufacturer Part Number`
- `Quantity`
- `Reference Designator` または `Customer Reference`

## 出力の読み方

単体取得では以下のような構造になります。

```json
{
  "ok": true,
  "fetched_at": "2026-06-22T12:34:56Z",
  "cache": {
    "hit": false,
    "ttl_seconds": 86400
  },
  "source": {
    "provider": "Digi-Key",
    "api": "Product Information V4",
    "environment": "production",
    "site": "JP",
    "language": "ja",
    "currency": "JPY"
  },
  "product": {
    "manufacturer_part_number": "TPS40210DGQR",
    "datasheet_url": "https://...",
    "quantity_available": 123,
    "status": "Active",
    "parameter_map": {
      "Voltage - Supply": "4.5V ~ 52V"
    },
    "variations": [],
    "best_offer": {
      "digikey_product_number": "296-26969-1-ND",
      "package_type": "Cut Tape",
      "requested_quantity": 5,
      "purchase_quantity": 5,
      "unit_price": 123.0,
      "estimated_total_price": 615.0
    }
  },
  "warnings": []
}
```

AI エージェントが優先して使う想定のフィールド:

- `product.datasheet_url`: データシート URL
- `product.parameter_map`: 仕様名から値を引ける辞書
- `product.status` と `product.status_flags`: Active/EOL/Discontinued などの判断材料
- `product.variations[].standard_pricing`: パッケージごとの価格表
- `product.best_offer`: 指定数量に対して最も扱いやすい見積もり
- `warnings`: 部品採用前に確認すべき注意点

## キャッシュと再取得

デフォルトでは API レスポンスを 24 時間キャッシュします。価格と在庫を必ず取り直す場合は `--refresh` を付けます。

```sh
python tools/digikey_lookup.py part SN74HC595DR --refresh --pretty
```

キャッシュを無効化する場合:

```sh
python tools/digikey_lookup.py part SN74HC595DR --cache-ttl-seconds 0 --pretty
```

## エラー出力

認証情報不足、API の 401/404/429、ネットワークエラーも JSON で返します。

```json
{
  "ok": false,
  "error": {
    "type": "DigikeyConfigError",
    "message": "DIGIKEY_CLIENT_ID and DIGIKEY_CLIENT_SECRET are required."
  },
  "hints": []
}
```

`429 Too Many Requests` の場合は `Retry-After` ヘッダーを見て自動リトライします。

## 参照

- Digi-Key API Developer Portal: https://developer.digikey.com/
- Product Information V4: https://developer.digikey.com/products/product-information-v4
- ProductDetails endpoint: https://developer.digikey.com/products/product-information-v4/productsearch/productdetails
- OAuth 2.0 2-legged flow: https://developer.digikey.com/tutorials-and-resources/oauth-20-2-legged-flow
