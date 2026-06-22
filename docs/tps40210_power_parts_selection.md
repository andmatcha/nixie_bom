# TPS40210DGQR 電源系部品選定

## 1. 目的

TPS40210DGQR を使用し、DC 12 V 入力からニキシー管用の DC 170 V / 20 mA を生成する昇圧電源の部品を選定する。

コンデンサは Murata、抵抗は Panasonic から選定する。ただし、DigiKey 上で在庫 0 または新規設計向けに不適合な部品は、回路用途上許容できる範囲で同メーカーのアクティブ品へ置き換える。DigiKey で部品状況がアクティブで、日本から購入できることを確認した部品を採用候補とする。

## 2. 設計条件

| 項目 | 値 |
| --- | --- |
| 入力電圧 | 12 V nominal |
| 設計確認用入力範囲 | 10.8 V から 13.2 V |
| 出力電圧 | 170 V |
| 出力電流 | 20 mA |
| 出力電力 | 3.4 W |
| コントローラ | TPS40210DGQR |
| 整流方式 | 非同期昇圧 |
| 想定スイッチング周波数 | 約 168 kHz |

170 V 出力ではデューティ比が高くなるため、TPS40210 の最小オフ時間を満たすようにスイッチング周波数を下げる。VIN = 10.8 V、VOUT = 170 V、ダイオード順方向電圧を 1 V とすると、最大デューティは約 93.7 %、オフ時間は約 376 ns となり、TPS40210 の最小オフ時間 200 ns に対して余裕を持つ。

## 3. データシートから必要になる部品

TPS40210 の昇圧電源として、少なくとも以下の部品が必要になる。

- TPS40210DGQR 本体
- 昇圧インダクタ
- Nch パワー MOSFET
- 整流ダイオード
- MOSFET ソース電流検出抵抗
- ISNS ノイズフィルタ用 RC
- 入力コンデンサ
- 出力コンデンサ
- VDD バイパスコンデンサ
- BP レギュレータ用 1 uF バイパスコンデンサ
- FB 分圧抵抗
- COMP-FB 間の補償部品
- RC 発振周波数設定用抵抗・コンデンサ
- SS ソフトスタートコンデンサ
- 出力放電抵抗
- DIS/EN 制御用のプルダウン/直列抵抗
- 12 V入力側のHV昇圧分岐保護ヒューズ

## 4. 主要設計値

### 4.1 発振周波数

TPS40210 の RC 発振式を用い、CRC = 100 pF、RRC = 1.00 MOhm とする。

この組み合わせでスイッチング周波数は約 168 kHz となる。100 pF はデータシートで扱いやすい範囲の値であり、RRC も推奨範囲内に収まる。

### 4.2 インダクタ電流

L = 1 mH、fSW = 約 168 kHz とした場合の概算値は以下の通り。

| 項目 | 概算値 |
| --- | --- |
| 最大デューティ | 約 93.7 % |
| インダクタリップル電流 | 約 73 mA p-p |
| インダクタ平均電流 最大 | 約 317 mA |
| インダクタピーク電流 最大 | 約 347 mA |
| インダクタ RMS 電流 最大 | 約 317 mA |

7447709102 は 1 mH、900 mA、飽和電流 1 A のため、電流定格としては十分な余裕がある。DCR が最大 1.2 Ohm と大きいため、効率と温度上昇は実測確認する。

### 4.3 電流検出抵抗

L1 は 7447709102 のまま維持し、RISNS = 0.15 Ohm とする。

VIN = 10.8 V、L = 1 mH、fSW = 約 168 kHz の条件では、TPS40210 データシート Eq.19 によるサブハーモニック安定性の上限は約 0.189 Ohm、80 % 目安は約 0.151 Ohm となる。0.15 Ohm はこの 80 % 目安内に収まり、0.1 Ohm より過電流検出ピークを下げられる。

| 項目 | 概算値 |
| --- | ---: |
| 通常動作インダクタピーク電流 | 約 0.35 A |
| VISNS = 120 mV 時のピーク検出電流 | 約 0.80 A |
| VISNS = 150 mV 時のピーク検出電流 | 約 1.00 A |
| VISNS = 180 mV 時のピーク検出電流 | 約 1.20 A |
| VIN = 10.8 V 時の出力過電流目安 | 約 49 mA / 61 mA / 74 mA |

通常動作の RSNS1 損失は約 15 mW 程度で、0.5 W 定格の ERJ-8BSFR15V なら十分余裕がある。一方、TPS40210 の過電流しきい値最大側では L1 の Isat 1 A を超え得るため、短絡・過電流保護として入力側ヒューズを追加し、実機でISNS波形とL1温度を確認する。

### 4.4 コンデンサ

入力コンデンサの最小値は概算で約 1.5 uF、出力コンデンサの最小値は 1 V リップル基準で約 0.9 uF となる。

実装では DC バイアス、実容量低下、負荷過渡、ACアダプタ配線、レイアウト寄生を見込み、入力は 10 uF x 2 に加えて 22 uF x 2 のバルク容量を追加する。出力は 1 uF / 250 V x 3 を採用候補とする。

ISNS フィルタは RIFLT = 1 kOhm、CIFLT = 470 pF とする。今回条件での目安時定数は約 0.55 us、採用値は 0.47 us で、おおむねデータシート式 `RIFLT x CIFLT = 0.1 x tON` に近い。

CSS1 は 1 uF とする。RSS(chg) のばらつきを含めたソフトスタート時間は約 32 ms から 60 ms となり、COUT nominal 3 uF を 170 V まで充電する電流に 20 mA 起動負荷を足しても、RSNS = 0.15 Ohm の最小側過電流点に対して余裕を持たせられる。

### 4.5 FB 分圧

TPS40210 の FB 基準電圧は 0.7 V。以下の構成で出力設定は約 170.6 V となる。

- 上側: 20 kOhm x 5 = 100 kOhm
- 下側: 412 Ohm

上側抵抗を 5 本直列にすることで、各抵抗にかかる電圧と消費電力を分散する。分圧電流は約 1.7 mA で、表示負荷に対して無視はできないが、データシートのフィードバック抵抗範囲を優先した初期設計値とする。

### 4.6 補償回路

補償回路は以下を初期値とする。

- RCOMP = 68 kOhm
- CCOMP = 2200 pF
- CHF = 47 pF

ゼロは約 1 kHz、ハイサイド側のポールは約 50 kHz 付近になる。これは初期実装値であり、最終値は実機の負荷ステップ、出力リップル、起動波形、可能ならループ測定で調整する。

## 5. 選定部品表

在庫・ステータスは 2026-06-22 時点で DigiKey の商品ページを確認した。

| Designator | 数量 | 用途 | メーカー | 型番 | 主な仕様 | DigiKey確認 |
| --- | ---: | --- | --- | --- | --- | --- |
| U1 | 1 | 昇圧コントローラ | Texas Instruments | [TPS40210DGQR](https://www.digikey.jp/ja/products/detail/texas-instruments/TPS40210DGQR/1907864) | 4.5 V to 52 V, Boost/SEPIC/Flyback controller | アクティブ、在庫あり、日本向けJPY表示あり |
| L1 | 1 | 昇圧インダクタ | Würth Elektronik | [7447709102](https://www.digikey.jp/ja/products/detail/w%C3%BCrth-elektronik/7447709102/1994067) | 1 mH, 900 mA, Isat 1 A, DCR 1.2 Ohm max | アクティブ、在庫あり、日本向けJPY表示あり |
| Q1 | 1 | 昇圧スイッチ MOSFET | STMicroelectronics | [STD10N60M2](https://www.digikey.jp/ja/products/detail/stmicroelectronics/STD10N60M2/4357546) | Nch, 600 V, 7.5 A, DPAK | アクティブ、在庫あり、日本から購入可能 |
| D1 | 1 | 昇圧整流ダイオード | STMicroelectronics | [STTH2R06U](https://www.digikey.jp/ja/products/detail/stmicroelectronics/STTH2R06U/691875) | 600 V, 2 A, SMB, trr 50 ns | アクティブ、在庫あり。Digi-Key 品番 497-3776-1-ND。MURS160-13-F から安全寄りに置換 |
| FHV1 | 1 | 12 V入力側ヒューズ | Littelfuse | 0437.750KRA | 750 mA, 63 VAC/VDC, fast acting, 1206 | アクティブ、在庫あり。Digi-Key 品番 18-0437.750KRACT-ND |
| CIN1, CIN2 | 2 | 12 V 入力平滑 | Murata | [GRM31CR71E106KA12K](https://www.digikey.jp/ja/products/detail/murata-electronics/GRM31CR71E106KA12K/4905618) | 10 uF, 25 V, X7R, 1206 | アクティブ、在庫あり |
| CINB1, CINB2 | 2 | 12 V 入力バルク | Murata | GRM32ER71E226KE15L | 22 uF, 25 V, X7R, 1210 | アクティブ、在庫あり。Digi-Key 品番 490-5313-1-ND |
| COUT1, COUT2, COUT3 | 3 | 170 V 出力平滑 | Murata | [GRM55DR72E105KW01L](https://www.digikey.jp/ja/products/detail/murata-electronics/GRM55DR72E105KW01L/789398) | 1 uF, 250 V, X7R, 2220 | アクティブ、在庫あり |
| CVDD1 | 1 | TPS40210 VDD バイパス | Murata | [GCM188R71E105KA64D](https://www.digikey.jp/ja/products/detail/murata-electronics/GCM188R71E105KA64D/4903956) | 1 uF, 25 V, X7R, 0603 | アクティブ、在庫あり |
| CBP1 | 1 | BP レギュレータバイパス | Murata | [GCM188R71E105KA64D](https://www.digikey.jp/ja/products/detail/murata-electronics/GCM188R71E105KA64D/4903956) | 1 uF, 25 V, X7R, 0603 | アクティブ、在庫あり |
| CSS1 | 1 | ソフトスタート | Murata | [GCM188R71E105KA64D](https://www.digikey.jp/ja/products/detail/murata-electronics/GCM188R71E105KA64D/4903956) | 1 uF, 25 V, X7R, 0603 | アクティブ、在庫あり。20 mA負荷付き起動を見込み増量 |
| CRC1 | 1 | 発振周波数設定 | Murata | GCM1885C1H101JA16D | 100 pF, 50 V, C0G/NP0, 0603 | アクティブ、在庫あり。Digi-Key 品番 490-4767-1-ND。GRM1885C1H101JA01D から置換済み |
| CIFLT1 | 1 | ISNS フィルタ | Murata | GCM1885C1H471JA16D | 470 pF, 50 V, C0G/NP0, 0603 | アクティブ、在庫あり。Digi-Key 品番 490-4965-1-ND |
| CCOMP1 | 1 | COMP-FB 補償ゼロ | Murata | [GRM1885C1H222JA01D](https://www.digikey.jp/ja/products/detail/murata-electronics/GRM1885C1H222JA01D/586951) | 2200 pF, 50 V, C0G/NP0, 0603 | アクティブ、在庫あり |
| CHF1 | 1 | COMP-FB 高周波ポール | Murata | GCM1885C1H470GA16J | 47 pF, 50 V, C0G/NP0, 0603, ±2 % | アクティブ、在庫あり。Digi-Key 品番 490-GCM1885C1H470GA16JCT-ND。GCM1885C1H470JA16D から置換済み |
| RSNS1 | 1 | MOSFET ソース電流検出 | Panasonic | ERJ-8BSFR15V | 0.15 Ohm, 1 %, 0.5 W, 1206 | アクティブ、在庫あり。Digi-Key 品番 10-ERJ-8BSFR15VCT-ND |
| RIFLT1 | 1 | ISNS フィルタ | Panasonic | ERJ-3GEYJ102V | 1 kOhm, 5 %, 0.1 W, 0603, 厚膜 | アクティブ、在庫あり。Digi-Key 品番 P1.0KGCT-ND。ERJ-3EKF1001V は在庫0のため置換 |
| RRC1 | 1 | 発振周波数設定 | Panasonic | [ERJ-6ENF1004V](https://www.digikey.jp/ja/products/detail/panasonic-industry/ERJ-6ENF1004V/112223) | 1.00 MOhm, 1 %, 0805 | アクティブ、在庫あり |
| RG1 | 1 | MOSFET ゲート抵抗 | Panasonic | [ERJ-3EKF10R2V](https://www.digikey.jp/ja/products/detail/panasonic-industry/ERJ-3EKF10R2V/196067) | 10.2 Ohm, 1 %, 0603 | アクティブ、在庫あり |
| RFB1-RFB5 | 5 | FB 上側分圧 | Panasonic | [ERJ-6ENF2002V](https://www.digikey.jp/ja/products/detail/panasonic-industry/ERJ-6ENF2002V/111532) | 20 kOhm, 1 %, 0805 | アクティブ、在庫あり |
| RFB6 | 1 | FB 下側分圧 | Panasonic | [ERJ-6ENF4120V](https://www.digikey.jp/ja/products/detail/panasonic-industry/ERJ-6ENF4120V/111207) | 412 Ohm, 1 %, 0805 | アクティブ、在庫あり |
| RCOMP1 | 1 | COMP-FB 補償抵抗 | Panasonic | [ERJ-6ENF6802V](https://www.digikey.jp/ja/products/detail/panasonic-electronic-components/ERJ-6ENF6802V/1746528) | 68 kOhm, 1 %, 0805 | アクティブ、在庫あり |
| RBLD1-RBLD3 | 3 | 出力放電抵抗 | Panasonic | [ERJ-6ENF1104V](https://www.digikey.jp/ja/products/detail/panasonic-industry/ERJ-6ENF1104V/282710) | 1.1 MOhm, 1 %, 0805 | アクティブ、在庫あり |
| REN1 | 1 | DIS/EN 直列保護 | Panasonic | ERJ-3GEYJ102V | 1 kOhm, 5 %, 0.1 W, 0603, 厚膜 | アクティブ、在庫あり。Digi-Key 品番 P1.0KGCT-ND。ERJ-3EKF1001V は在庫0のため置換 |
| RENPD1 | 1 | DIS/EN プルダウン | Panasonic | [ERJ-3EKF1003V](https://www.digikey.jp/ja/products/detail/panasonic-industry/ERJ-3EKF1003V/196075) | 100 kOhm, 1 %, 0603 | アクティブ、在庫あり |

## 6. 採用しない候補

以下は初期メモまたは検索中に見つかったが、今回の選定から外す。

| 型番 | 理由 |
| --- | --- |
| GRM188R71E105KA12D | DigiKey 上で Obsolete 扱いのため、CVDD/CBP には GCM188R71E105KA64D を採用する |
| GRM1885C1H101JA01D | DigiKey 上で新規設計向けに不適合なため、CRC には GCM1885C1H101JA16D を採用する。CIFLT は指定により470 pF品へ分離する |
| GCM1885C1H470JA16D | DigiKey 上で新規設計向けに不適合なため、CHF には GCM1885C1H470GA16J を採用する |
| ERJ-3EKF1001V | DigiKey 上で在庫 0 のため、RIFLT/REN には Panasonic の ERJ-3GEYJ102V を採用する |
| ERJ-8ENF1004V | DigiKey 上で Not For New Designs 扱いのため、RRC には ERJ-6ENF1004V を採用する |
| ERJ-8ENF2002V | DigiKey 上で Not For New Designs 扱いのため、FB 上側分圧には ERJ-6ENF2002V を採用する |
| ERJ-8ENF4120V | DigiKey 上で Not For New Designs 扱いのため、FB 下側分圧には ERJ-6ENF4120V を採用する |
| GRM188R71E224KA88D | アクティブ品だが、20 mA負荷付き起動の余裕を増やすため CSS1 には 1 uF 品を採用する |
| ERJ-8BSFR10V | L1を維持する前提では過電流検出ピークが高すぎるため、RSNS1 には 0.15 Ohm 品を採用する |
| MURS160-13-F | アクティブかつ在庫ありだが、同じ600 V/SMB/trr 50 nsで平均整流電流を2 Aへ増やせる STTH2R06U をD1に採用する |
| CRCW06031K00FKEA | アクティブかつ在庫ありだが、今回の抵抗メーカー指定に合わせて RIFLT/REN には Panasonic 品を採用する |

## 7. 実装・検証時の注意

- TPS40210 の BP ピンには CBP1 をできるだけ近くに配置する。
- CVDD1 は U1 の VDD-GND 間に近接配置する。
- RSNS1、RIFLT1、CIFLT1 は U1 の ISNS/GND 近傍に置く。
- Q1、D1、COUT1-COUT3、RSNS1 の大電流ループをできるだけ小さくする。
- SW ノードは高 dv/dt になるため、銅箔面積を必要以上に広げない。
- FB、COMP、RC、SS 周辺はスイッチングノードから離し、静かな GND に戻す。
- COUT1-COUT3 は 250 V 定格だが、DC バイアスで実効容量が低下する。170 V 実印加時の出力リップルを必ず測定する。
- RFB1-RFB5 は 170 V に接続されるため、各抵抗の電圧分担と沿面距離を意識して直列配置する。
- RBLD1-RBLD3 は合計 3.3 MOhm で、3 uF nominal の出力容量に対して時定数は約 9.9 s となる。電源断後の実放電時間を測定する。
- 補償定数は初期値であり、最終基板では起動波形、負荷ステップ、CAN 途絶時の HV 停止、IN-12 点灯時のリップルを確認して調整する。
- 通常の昇圧回路は、出力短絡時に入力からインダクタとダイオード経由で電流が流れる経路を完全には遮断できない。今回の初期試作では 12 V のHV昇圧分岐に FHV1 を入れ、持続短絡時に入力源とL1/D1を保護する。

## 8. データシート照合後の反映内容

`docs/tps40210_datasheet_summary.md` で TPS40210 データシート条件と照合し、今回指定された条件をBOMへ反映した。

| 対象 | 反映前 | 反映後 | 判定 | 理由 |
| --- | --- | --- | --- | --- |
| CIFLT1 | 100 pF, GCM1885C1H101JA16D | 470 pF, GCM1885C1H471JA16D | 反映済み | `RIFLT x CIFLT = 0.1 x tON` の目安約0.55 usに対し、1 kOhm x 470 pF = 0.47 usとなる。 |
| CSS1 | 0.22 uF, GRM188R71E224KA88D | 1 uF, GCM188R71E105KA64D | 反映済み | 20 mA負荷付き起動でも、COUT充電電流と負荷電流の合計がRSNS=0.15 Ohmの最小側過電流点を下回る見込み。 |
| L1 / RSNS1 | 7447709102 / 0.1 Ohm | 7447709102 / 0.15 Ohm | 反映済み | L1は維持し、Eq.19の80 %目安内で過電流検出ピークを下げる。 |
| D1 | MURS160-13-F, 600 V / 1 A / SMB | STTH2R06U, 600 V / 2 A / SMB / trr 50 ns | 反映済み | 同じSMB実装と600 V耐圧を維持しつつ、整流電流定格を2 Aへ増やして短絡・過渡時の温度余裕を上げる。 |
| 入力バルクコンデンサ | CIN1, CIN2 の10 uF x2 | CINB1, CINB2 として22 uF x2を追加 | 反映済み | ACアダプタ配線や起動時電流に対する入力インピーダンス低減。Murata品で追加。 |
| 短絡・過電流保護 | BOM上は未実装 | FHV1として750 mA入力ヒューズを追加 | 反映済み | 標準昇圧回路で残る入力から出力への短絡電流経路に対する簡易二次保護。 |

### 8.1 短絡・過電流保護案の比較

| 案 | 追加部品 | 長所 | 短所 | 判定 |
| --- | --- | --- | --- | --- |
| 入力側ワンタイムヒューズ | 1206ヒューズ1個 | 実装が簡単。故障時に入力源からHV昇圧分岐を切り離せる。しきい値の考え方がPTCより明確。 | 溶断後は交換が必要。起動突入と時間電流特性は実機確認が必要。 | 採用 |
| 入力側PTC | PTC 1個 | 自己復帰する。部品追加が少ない。 | 温度依存が大きく、動作が遅い。短絡時に完全遮断にならない場合がある。 | 不採用 |
| eFuse / ロードスイッチ | ICと周辺部品 | 電流制限、FAULT、EN制御を明確にできる。 | 部品点数、レイアウト、選定確認が増える。今回の簡易導入条件には重い。 | 将来検討 |
| 高電圧出力側保護 | HVヒューズ、抵抗、保護素子 | 出力側の異常に近い位置で保護できる。 | 170 Vの定格、沿面距離、遮断特性の確認が必要。初期試作では実装負担が大きい。 | 将来検討 |

採用部品は Littelfuse 0437.750KRA とする。通常の 170 V / 20 mA 出力では入力電流が概ね 0.4 A 以下に収まる想定のため、750 mA定格で通常動作の余裕を持たせつつ、持続短絡や部品故障時に入力分岐を切り離す方針とする。

## 9. 次に確定する項目

- アノードドライバ回路との接続点
- プリバイアス回路の抵抗値と消費電力
- TPS40210 の DIS/EN を MCU からどの論理で制御するか
- FHV1 の時間電流特性、突入電流、実短絡時温度の実測確認
- 出力短絡・人体接触を想定した追加保護の要否
- PCB 上の 170 V 系クリアランスとテストポイント配置
