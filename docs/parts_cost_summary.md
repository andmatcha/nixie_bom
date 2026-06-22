# 部品代集計

Digi-Key Product Information V4 API を使用し、`bom/nixie_clock_integrated_digikey_bom_active.csv` の全明細について価格を取得した。

## 集計結果

| 項目 | 値 |
| --- | ---: |
| 対象明細数 | 46 |
| 取得成功 | 46 |
| 取得失敗 | 0 |
| 合計部品代 | 9,018.50 JPY |

価格取得日時: 2026-06-22 21:01:43 JST
出力 CSV: `bom/nixie_clock_active_digikey_price_list.csv`

## 区分別小計

| 区分 | 小計 JPY |
| --- | ---: |
| Control | 5,786.80 |
| Power | 3,021.00 |
| Power/control | 210.70 |

## ステータス内訳

- アクティブ: 46 明細

## 注意事項

- 合計は Digi-Key API が返した商品単価を基にした部品代であり、送料、税、手数料は含まない。
- IN-12 ニキシー管本体および INS-1 本体は、現在の BOM に含まれていないため集計対象外である。
- `Purchase Quantity` は最小注文数量を考慮した購入数量であり、BOM 上の `Quantity` と異なる場合がある。
- `Immediate` が `no` の明細は、`dktools bom price` の `Availability Reasons` を確認する。

## 在庫・警告

| Reference Designator | Manufacturer Part Number | 警告 |
| --- | --- | --- |
| なし | なし | なし |
