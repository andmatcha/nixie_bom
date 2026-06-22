# 制御・表示駆動系部品選定

## 1. 目的

IN-12 ニキシー管時計の制御・通信・表示駆動系について、初回基板に実装する部品を選定する。

電源系と同じルールとして、コンデンサは Murata、抵抗は Panasonic から選定する。主要部品はデータシートを確認し、DigiKey で部品状況がアクティブで、日本から購入できることを確認したものを採用候補とする。

IN-12 および INS-1 本体は既存前提の表示デバイスであり、本書の DigiKey 選定対象からは外す。

## 2. 設計条件

| 項目 | 値 |
| --- | --- |
| 入力電源 | DC 12 V |
| 制御電源 | 3.3 V |
| MCU | STM32 系、CAN/FDCAN、SPI、タイマ、SWD を持つこと |
| CAN | CAN 2.0B、1 Mbps、標準 ID を基本条件 |
| 表示方式 | IN-12 6 桁ダイナミック点灯 |
| カソード | 数字 0 から 9 の 10 系統を共通化 |
| アノード | 6 桁を個別に高側スイッチング |
| コロン | INS-1 を 4 個使用 |
| 高電圧 | 170 V nominal、設計上 160 V から 180 V を考慮 |
| シフトレジスタ出力数 | 24 出力を初期構成とする |

シフトレジスタ出力は、IN-12 カソード 10 本、IN-12 アノード制御 6 本、INS-1 制御 4 本、予備 4 本に割り当てる。SN74HC595DR を 3 個カスケード接続し、OE は MCU から直接制御してブランキングに使う。

## 3. データシートから必要になる部品

制御・表示駆動系として、少なくとも以下の部品が必要になる。

- STM32 MCU
- MCU 用 HSE 水晶振動子と負荷容量
- MCU、ロジック、CAN 用 3.3 V 降圧電源
- 3.3 V 降圧電源のインダクタ、入力コンデンサ、出力コンデンサ、ブートストラップコンデンサ
- CAN トランシーバ
- CAN バス ESD 保護素子
- CAN 終端抵抗と終端有効化用のはんだジャンパ
- CAN コネクタ
- SWD デバッグコネクタ
- SN74HC595 シフトレジスタ
- SN75468 カソードシンクドライバ
- IN-12 アノード用高耐圧 PNP トランジスタ
- 高耐圧 PNP を駆動する高耐圧 NPN トランジスタ
- IN-12 アノード電流制限抵抗
- IN-12 カソードプリバイアス回路
- INS-1 低側スイッチ用高耐圧 NPN トランジスタ
- INS-1 電流制限抵抗
- 各 IC のデカップリングコンデンサ
- リセット、BOOT、OE、SRCLR、CAN モード、トランジスタ入力のプルアップ/プルダウン抵抗

## 4. 採用構成

### 4.1 MCU

MCU は STM32G0B1CBT6 を採用候補とする。

48-LQFP で手実装や試作確認がしやすく、CANbus、SPI、タイマ、44 I/O を持つため、CAN 受信、SN74HC595 更新、表示ブランキング、HV_ENABLE 制御、SWD デバッグを 1 チップで扱える。

CAN のビットタイミング余裕を確保するため、HSE として 8 MHz 水晶振動子を実装する。内部発振だけでの CAN 運用は初回基板の標準構成にはしない。

### 4.2 3.3 V 制御電源

3.3 V 電源は AP63203QWU-7 を採用候補とする。

AP63203QWU-7 は 3.8 V から 32 V 入力、3.3 V 固定出力、2 A の同期整流降圧コンバータであり、12 V 入力から MCU、CAN、SN74HC595、SN75468 入力をまとめて供給できる。

通常版 AP63203WU-7 は確認時点で DigiKey 在庫が 0 のため採用しない。AP63203QWU-7 はアクティブかつ在庫があるため、初回基板の採用候補とする。

### 4.3 CAN

CAN トランシーバは TCAN334GDR を採用候補とする。

当初候補の TCAN332GDR は確認時点で DigiKey 在庫が 0 のため採用しない。TCAN334GDR は 3.3 V 単電源、5 Mbps 対応、SOIC-8、STB/SHDN 付きであり、1 Mbps の CAN 2.0B には十分余裕がある。

STB と SHDN は外付け 100 kOhm で GND にプルダウンし、MCU リセット中のデフォルトを通常動作側に寄せる。必要に応じて MCU GPIO でスタンバイまたはシャットダウンを制御する。

CANH/CANL には ESD2CAN24DBZRQ1 を配置する。終端抵抗は 120 Ohm を実装し、はんだジャンパで有効/無効を切り替える。

### 4.4 シフトレジスタ

SN74HC595DR を 3 個使用する。

SN74HC595 は 2 V から 6 V で動作し、3.3 V ロジックで使用できる。OE が High のとき出力がハイインピーダンスになるため、MCU のブランキング信号で桁切り替え中の誤点灯を抑える。OE は 100 kOhm で 3.3 V にプルアップし、MCU リセット中は表示を無効化する。

### 4.5 カソードシンク

SN75468DR を 2 個使用し、10 本の IN-12 カソードラインを駆動する。

SN75468 は 7ch の NPN Darlington シンクドライバで、各出力は 100 V、500 mA 定格である。IN-12 のカソードシンク電流はピーク 12 mA から 15 mA 程度を初期目標とするため、電流定格には十分余裕がある。

SN75468 の COM 端子は誘導性負荷用クランプダイオードの共通端子である。ニキシー管カソード駆動では誘導性負荷を扱わないため、初期設計では COM を 170 V 系へ接続せず未接続とする。

### 4.6 カソードプリバイアス

SN75468 の出力耐圧 100 V に対して余裕を持たせるため、消灯中のカソードラインは約 90 V にプリバイアスする。

初期値は以下とする。

- RPREH1 = 150 kOhm
- RPREL1 = 180 kOhm
- CVPRE1 = 0.1 uF / 250 V
- RKP1-RKP10 = 1.00 MOhm

170 V 入力時の無負荷 VPRE は約 92.7 V となる。点灯中の選択カソードラインは 1 MOhm 経由で VPRE を負荷するため、実動作時の VPRE と SN75468 出力端子電圧は必ず実測する。

### 4.7 IN-12 アノードドライバ

IN-12 の各桁アノードは、MMBTA92-7-F と MMBTA42-7-F のディスクリート高側スイッチで駆動する。

1 桁あたり以下の構成とする。

- QAHx: MMBTA92-7-F PNP、エミッタを 170 V 系へ接続
- QALx: MMBTA42-7-F NPN、PNP ベース電流をシンク
- RAHOFFx: 1.00 MOhm、PNP ベース-エミッタ間プルアップ
- RAHDRVxA/RAHDRVxB: 220 kOhm x 2 直列、PNP ベース駆動電流制限
- RALBx: 10 kOhm、SN74HC595 出力から NPN ベースへの直列抵抗
- RALPDx: 100 kOhm、NPN ベースプルダウン
- RAx: 2.2 kOhm、IN-12 アノード電流制限

RAHDRV を 220 kOhm x 2 直列にすることで、170 V 印加時の抵抗電圧と消費電力を分散する。概算の PNP ベース電流は約 0.38 mA で、ピーク管電流 12 mA から 15 mA 程度の初期設計に対して確認しやすい値とする。

RA は 2.2 kOhm を初期値とする。IN-12 の実際の放電電圧、管個体差、デューティ比、輝度目標に依存するため、最終値は実機で平均管電流 2 mA から 2.5 mA 程度になるよう調整する。

### 4.8 INS-1 コロン駆動

INS-1 は 4 個それぞれに MMBTA42-7-F を低側スイッチとして使用する。

1 個あたり以下の構成とする。

- QCOLx: MMBTA42-7-F NPN、INS-1 低側シンク
- RINSx: 180 kOhm、INS-1 電流制限
- RCOLBx: 10 kOhm、SN74HC595 出力から NPN ベースへの直列抵抗
- RCOLPDx: 100 kOhm、NPN ベースプルダウン

INS-1 の電流は明るさと寿命を見ながら調整する。180 kOhm は初期値であり、暗い場合は抵抗値を下げる候補を残す。

## 5. 選定部品表

在庫・ステータスは 2026-06-22 時点で DigiKey の商品ページを確認した。

| Designator | 数量 | 用途 | メーカー | 型番 | 主な仕様 | DigiKey確認 |
| --- | ---: | --- | --- | --- | --- | --- |
| U2 | 1 | MCU | STMicroelectronics | [STM32G0B1CBT6](https://www.digikey.jp/ja/products/detail/stmicroelectronics/STM32G0B1CBT6/18086231) | Arm Cortex-M0+, 64 MHz, 128 KB Flash, 48-LQFP, CANbus | アクティブ、在庫あり |
| U3 | 1 | 12 V から 3.3 V 降圧 | Diodes Incorporated | [AP63203QWU-7](https://www.digikey.jp/ja/products/detail/diodes-incorporated/AP63203QWU-7/16548045) | 3.8 V to 32 V input, 3.3 V fixed, 2 A, TSOT-23-6 | アクティブ、在庫あり |
| L2 | 1 | 3.3 V 降圧用インダクタ | Würth Elektronik | [74439346068](https://www.digikey.jp/ja/products/detail/w%C3%BCrth-elektronik/74439346068/6236304) | 6.8 uH, 6.5 A, shielded, DCR 17.6 mOhm | アクティブ、在庫あり |
| U4 | 1 | CAN トランシーバ | Texas Instruments | [TCAN334GDR](https://www.digikey.jp/ja/products/detail/texas-instruments/TCAN334GDR/5957539) | 3.3 V CAN FD transceiver, 5 Mbps, SOIC-8 | アクティブ、在庫あり |
| U5-U7 | 3 | 表示制御シフトレジスタ | Texas Instruments | [SN74HC595DR](https://www.digikey.jp/ja/products/detail/texas-instruments/SN74HC595DR/562919) | 8bit serial-in parallel-out, 2 V to 6 V, SOIC-16 | アクティブ、在庫あり |
| U8, U9 | 2 | IN-12 カソードシンク | Texas Instruments | [SN75468DR](https://www.digikey.jp/ja/products/detail/texas-instruments/SN75468DR/1593427) | 7ch NPN Darlington, 100 V, 500 mA, SOIC-16 | アクティブ、在庫あり |
| QAH1-QAH6 | 6 | IN-12 アノード高側 PNP | Diodes Incorporated | [MMBTA92-7-F](https://www.digikey.jp/ja/products/detail/diodes-incorporated/MMBTA92-7-F/717771) | PNP, 300 V, 500 mA, SOT-23 | アクティブ、在庫あり |
| QAL1-QAL6, QCOL1-QCOL4 | 10 | アノード/INS-1 駆動用 NPN | Diodes Incorporated | [MMBTA42-7-F](https://www.digikey.jp/ja/products/detail/diodes-incorporated/MMBTA42-7-F/814500) | NPN, 300 V, 500 mA, SOT-23 | アクティブ、在庫あり |
| D2 | 1 | CAN ESD 保護 | Texas Instruments | [ESD2CAN24DBZRQ1](https://www.digikey.jp/ja/products/detail/texas-instruments/ESD2CAN24DBZRQ1/16982061) | CAN 用 2ch bidirectional ESD, 24 V, SOT-23 | アクティブ、在庫あり |
| Y1 | 1 | MCU HSE | ECS Inc. | [ECS-80-12-33-JGN-TR](https://www.digikey.jp/ja/products/detail/ecs-inc/ECS-80-12-33-JGN-TR/10478754) | 8 MHz, 12 pF, ±20 ppm, 3.2 x 2.5 mm | アクティブ、在庫あり |
| JCAN1 | 1 | CANH/CANL/GND 接続 | On Shore Technology | [OSTVN03A150](https://www.digikey.jp/ja/products/detail/on-shore-technology-inc/OSTVN03A150/1588863) | 3 position terminal block, 2.54 mm | アクティブ、在庫あり |
| JSWD1 | 1 | SWD デバッグ | Samtec | [FTSH-105-01-F-DV-K](https://www.digikey.jp/ja/products/detail/samtec-inc/FTSH-105-01-F-DV-K/2649974) | 10 position, 1.27 mm, SMD header | アクティブ、在庫あり |
| C3V3IN1, C3V3IN2 | 2 | 3.3 V 降圧入力 | Murata | GRJ31CR71H475KE11K | 4.7 uF, 50 V, X7R, 1206 | アクティブ、在庫あり。Digi-Key 品番 490-GRJ31CR71H475KE11KCT-ND |
| C3V3OUT1, C3V3OUT2 | 2 | 3.3 V 降圧出力 | Murata | GRM31CC81E226KE11L | 22 uF, 25 V, X6S, 1206 | アクティブ、在庫あり。Digi-Key 品番 490-14468-1-ND |
| CBOOT1, C3V3HF1, CDEC1-CDEC8 | 10 | ブートストラップ、入力 HF、IC デカップリング | Murata | [GRM188R72A104KA35D](https://www.digikey.jp/ja/products/detail/murata-electronics/GRM188R72A104KA35D/702549) | 0.1 uF, 100 V, X7R, 0603 | アクティブ、在庫あり |
| CY1, CY2 | 2 | HSE 負荷容量 | Murata | GCM1885C1H180FA16D | 18 pF, 50 V, C0G/NP0, 0603, ±1 % | アクティブ、在庫あり。Digi-Key 品番 490-GCM1885C1H180FA16DCT-ND |
| CVPRE1 | 1 | カソードプリバイアス平滑 | Murata | [GRM31CR72E104KW03L](https://www.digikey.jp/ja/products/detail/murata-electronics/GRM31CR72E104KW03L/789390) | 0.1 uF, 250 V, X7R, 1206 | アクティブ、在庫あり |
| RALB1-RALB6, RCOLB1-RCOLB4, RNRST1, RSRCLR1 | 12 | ベース抵抗、リセット/クリアプルアップ | Panasonic | [ERJ-3EKF1002V](https://www.digikey.jp/ja/products/detail/panasonic-industry/ERJ-3EKF1002V/196066) | 10 kOhm, 1 %, 0603 | アクティブ、在庫あり |
| ROE1, RBOOT1, RCANSTB1, RCANSHDN1, RALPD1-RALPD6, RCOLPD1-RCOLPD4, R3V3EN1 | 15 | プルアップ/プルダウン | Panasonic | [ERJ-3EKF1003V](https://www.digikey.jp/ja/products/detail/panasonic-industry/ERJ-3EKF1003V/196075) | 100 kOhm, 1 %, 0603 | アクティブ、在庫あり |
| RAHDRV1A-RAHDRV6B | 12 | アノード PNP ベース電流制限 | Panasonic | [ERJ-6ENF2203V](https://www.digikey.jp/ja/products/detail/panasonic-industry/ERJ-6ENF2203V/1746544) | 220 kOhm, 1 %, 0805 | アクティブ、在庫あり |
| RAHOFF1-RAHOFF6, RKP1-RKP10 | 16 | アノード PNP オフ保持、カソードプリバイアス | Panasonic | [ERJ-6ENF1004V](https://www.digikey.jp/ja/products/detail/panasonic-industry/ERJ-6ENF1004V/112223) | 1.00 MOhm, 1 %, 0805 | アクティブ、在庫あり |
| RA1-RA6 | 6 | IN-12 アノード電流制限 | Panasonic | [ERJ-P08F2201V](https://www.digikey.jp/ja/products/detail/panasonic-industry/ERJ-P08F2201V/9812790) | 2.2 kOhm, 1 %, 0.667 W, 1206, pulse withstanding | アクティブ、在庫あり |
| RINS1-RINS4 | 4 | INS-1 電流制限 | Panasonic | [ERJ-P08F1803V](https://www.digikey.jp/ja/products/detail/panasonic-industry/ERJ-P08F1803V/9812747) | 180 kOhm, 1 %, 0.667 W, 1206, pulse withstanding | アクティブ、在庫あり |
| RPREH1 | 1 | VPRE 上側分圧 | Panasonic | [ERJ-6ENF1503V](https://www.digikey.jp/ja/products/detail/panasonic-industry/ERJ-6ENF1503V/111899) | 150 kOhm, 1 %, 0805 | アクティブ、在庫あり |
| RPREL1 | 1 | VPRE 下側分圧 | Panasonic | [ERJ-6ENF1803V](https://www.digikey.jp/ja/products/detail/panasonic-industry/ERJ-6ENF1803V/1746469) | 180 kOhm, 1 %, 0805 | アクティブ、在庫あり |
| RT1 | 1 | CAN 終端抵抗 | Panasonic | [ERJ-3EKF1200V](https://www.digikey.jp/ja/products/detail/panasonic-industry/ERJ-3EKF1200V/1746300) | 120 Ohm, 1 %, 0603 | アクティブ、在庫あり |

## 6. 採用しない候補

以下は検索中に見つかったが、今回の選定から外す。

| 型番 | 理由 |
| --- | --- |
| AP63203WU-7 | DigiKey 上でアクティブだが確認時点で在庫 0 のため、AP63203QWU-7 を採用する |
| TCAN332GDR | DigiKey 上でアクティブだが確認時点で在庫 0 のため、TCAN334GDR を採用する |
| SN74HC595DT | DigiKey 上で Obsolete 扱いのため、SN74HC595DR を採用する |
| PESD1CAN,215 | DigiKey 上で Not For New Designs 扱いのため、ESD2CAN24DBZRQ1 を採用する |
| PESD2CANFD24V-TR | DigiKey 上で在庫 0 のため、ESD2CAN24DBZRQ1 を採用する |
| GRM31CR71H475KA12L | DigiKey 上で在庫 0 のため、3.3 V 入力には GRJ31CR71H475KE11K を採用する |
| GRT31CR61E226ME01L | DigiKey 上で新規設計向けに不適合なため、3.3 V 出力には GRM31CC81E226KE11L を採用する |
| GRM31CR61E226KE15L | DigiKey 上で生産中止・在庫 0 のため、3.3 V 出力には GRM31CC81E226KE11L を採用する |
| GRM188R71H104KA93D | DigiKey 上で Obsolete 扱いのため、0.1 uF デカップリングには GRM188R72A104KA35D を採用する |
| GRM1885C1H180JA01D | DigiKey 上で新規設計向けに不適合なため、HSE 負荷容量には GCM1885C1H180FA16D を採用する |

## 7. 実装・検証時の注意

- STM32G0B1CBT6 の VDD 近傍に CDEC1-CDEC4 を分散配置し、3.3 V レールの入口に 4.7 uF から 22 uF 程度のバルク容量を置く。
- AP63203QWU-7 の VIN、SW、L2、C3V3OUT1/C3V3OUT2 の電流ループを短くし、SW ノードは必要以上に広げない。
- AP63203QWU-7 の FB は固定 3.3 V品のため VOUT に接続する。FB 配線は SW ノードから離す。
- TCAN334GDR の CANH/CANL と D2 は JCAN1 近傍に配置し、ESD 電流の戻りを短くする。
- RT1 ははんだジャンパを介して CANH-CANL 間に接続し、基板がバス終端になる場合だけ有効化する。
- SN74HC595DR の OE はプルアップによりリセット中に無効化し、ファームウェア初期化後に Low へ下げる。
- SN74HC595DR の SRCLR は 10 kOhm で 3.3 V へプルアップする。未使用入力は VCC または GND に固定する。
- SN75468DR の COM は初期設計では未接続とし、170 V 系へ直接接続しない。
- SN75468DR の出力端子電圧は、消灯時、点灯時、桁切り替え時に 100 V を超えないことを実測する。
- RAHDRV1A-RAHDRV6B は 170 V 系に関わるため、直列 2 本の配置間隔と沿面距離を確保する。
- RA1-RA6 と RINS1-RINS4 は発熱と輝度を実測し、必要に応じて値を変更する。
- VPRE は 170 V 出力の変動に追従するため、170 V が 180 V 側に上がった条件でも SN75468 出力定格に入ることを確認する。
- 表示切り替えでは、先に OE でブランキングし、シフトレジスタ更新、ラッチ更新、アノード切り替え、カソード選択の順序を守る。

## 8. 次に確認する項目

- STM32G0B1CBT6 の具体的なピン割り当て
- 3 個の SN74HC595DR のビット割り当て
- IN-12 実機での RA1-RA6 最終値
- INS-1 実機での RINS1-RINS4 最終値
- VPRE 実測値と SN75468DR 出力端子の最大過渡電圧
- AP63203QWU-7 の 3.3 V リップルと CAN 通信中の電圧変動
