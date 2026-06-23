# KiCad フットプリント監査

BOM全行について、フットプリントがKiCad標準ライブラリまたはプロジェクトローカルライブラリで解決できることを確認した記録である。
Digi-Key保存応答にEDA/footprintの直接リンクが含まれていない部品は、メーカー/データシート寸法またはDigi-Keyパラメータからローカルフットプリントを生成した。

## サマリ

- BOM行数: 47
- KiCad標準フットプリント採用: 44
- プロジェクトローカルフットプリント採用: 3
- 未解決フットプリント: 0

## ローカル生成フットプリント

| Footprint | Source | Basis |
| --- | --- | --- |
| `nixie_clock_bom:OnShore_OSTVN03A150_1x03_P2.54mm_Horizontal` | Digi-Key datasheet URL / On Shore OSTVNXXA150 drawing | 3 poles, 2.54 mm pitch, 1.30 mm drill, Dim B 5.08 mm, Dim L 8.02 mm |
| `nixie_clock_bom:Samtec_FTSH_105_01_F_DV_K_2x05_P1.27mm_Vertical_SMD` | Samtec FTSH SMT datasheet and KiCad generic 1.27 mm SMD header pads | 2x05, 1.27 mm pitch, -DV vertical SMD body, -K keying shroud noted in fab/courtyard |
| `nixie_clock_bom:MillMax_9353_1_15_80_18_27_10_0` | Digi-Key product parameters / Mill-Max catalog URL | 1.85 mm mounting drill, 2.29 mm flange diameter, 4.06 mm socket depth |

## 全BOM行

| LineId | Ref | MPN | Footprint | Source | Status | Basis |
| --- | --- | --- | --- | --- | --- | --- |
| `804222c8dc6e` | `U1` | `TPS40210DGQR` | `Package_SO:HVSSOP-10-1EP_3x3mm_P0.5mm_EP1.83x1.89mm` | KiCad standard | available/high | Project-local symbol generated from the TPS40210 pin-function table; KiCad 10 has an HVSSOP-10-EP footprint. |
| `6c3ca2657583` | `FHV1` | `0437.750KRA` | `Fuse:Fuse_1206_3216Metric` | KiCad standard | generic_ok/high | 1206 board-mount fuse; KiCad generic 1206 fuse symbol and footprint are sufficient for schematic placement. |
| `2dde437fdef7` | `L1` | `7447709102` | `Inductor_SMD:L_Wuerth_WE-PD-Typ-M-Typ-S` | KiCad standard | available/high | KiCad 10 standard Wurth WE-PD Type M/S footprint selected; the 7447709102 datasheet reports a 12.0 x 12.0 mm WE-PD 1210 body and matching recommended land pattern. |
| `e531d8fbf4bf` | `Q1` | `STD10N60M2` | `Package_TO_SOT_SMD:TO-252-3_TabPin4` | KiCad standard | available/high | Digi-Key describes the package as DPAK/TO-252; KiCad TO-252-3_TabPin4 provides pads 1/2/3 plus drain tab 4, matching the selected G-D-S-D MOSFET symbol. |
| `6f9c953a3510` | `D1` | `STTH2R06U` | `Diode_SMD:D_SMB` | KiCad standard | generic_ok/high | Fast recovery diode in SMB; KiCad generic fast diode symbol and SMB footprint selected. |
| `6144ef6c2707` | `CIN1 CIN2` | `GRM31CR71E106KA12K` | `Capacitor_SMD:C_1206_3216Metric` | KiCad standard | generic_ok/high | Generic KiCad capacitor symbol and metric SMD capacitor footprint selected. |
| `8da575eed0a6` | `CINB1 CINB2` | `GRM32ER71E226KE15L` | `Capacitor_SMD:C_1210_3225Metric` | KiCad standard | generic_ok/high | Generic KiCad capacitor symbol and metric SMD capacitor footprint selected. |
| `5ca38ab8c3ae` | `COUT1 COUT2 COUT3` | `GRM55DR72E105KW01L` | `Capacitor_SMD:C_2220_5750Metric` | KiCad standard | generic_ok/high | Generic KiCad capacitor symbol and metric SMD capacitor footprint selected. |
| `54c3ee112c3c` | `CVDD1 CBP1 CSS1` | `GCM188R71E105KA64D` | `Capacitor_SMD:C_0603_1608Metric` | KiCad standard | generic_ok/high | Generic KiCad capacitor symbol and metric SMD capacitor footprint selected. |
| `479d2386c58a` | `CRC1` | `GCM1885C1H101JA16D` | `Capacitor_SMD:C_0603_1608Metric` | KiCad standard | generic_ok/high | Generic KiCad capacitor symbol and metric SMD capacitor footprint selected. |
| `0ecc127915e1` | `CIFLT1` | `GCM1885C1H471JA16D` | `Capacitor_SMD:C_0603_1608Metric` | KiCad standard | generic_ok/high | Generic KiCad capacitor symbol and metric SMD capacitor footprint selected. |
| `968250526037` | `CCOMP1` | `GRM1885C1H222JA01D` | `Capacitor_SMD:C_0603_1608Metric` | KiCad standard | generic_ok/high | Generic KiCad capacitor symbol and metric SMD capacitor footprint selected. |
| `cae608b7ab67` | `CHF1` | `GCM1885C1H470GA16J` | `Capacitor_SMD:C_0603_1608Metric` | KiCad standard | generic_ok/high | Generic KiCad capacitor symbol and metric SMD capacitor footprint selected. |
| `84980127cf24` | `RSNS1` | `ERJ-8BSFR15V` | `Resistor_SMD:R_1206_3216Metric` | KiCad standard | generic_ok/high | Generic KiCad resistor symbol and metric SMD resistor footprint selected. |
| `0e93376b6661` | `RIFLT1 REN1` | `ERJ-3GEYJ102V` | `Resistor_SMD:R_0603_1608Metric` | KiCad standard | generic_ok/high | Generic KiCad resistor symbol and metric SMD resistor footprint selected. |
| `689d5394d706` | `RRC1 RKP1-RKP10` | `ERJ-6ENF1004V` | `Resistor_SMD:R_0805_2012Metric` | KiCad standard | generic_ok/high | Generic KiCad resistor symbol and metric SMD resistor footprint selected. |
| `0d568ec2c81e` | `RG1` | `ERJ-3EKF10R2V` | `Resistor_SMD:R_0603_1608Metric` | KiCad standard | generic_ok/high | Generic KiCad resistor symbol and metric SMD resistor footprint selected. |
| `22ea46f5ae07` | `RFB1 RFB2 RFB3 RFB4 RFB5` | `ERJ-6ENF2002V` | `Resistor_SMD:R_0805_2012Metric` | KiCad standard | generic_ok/high | Generic KiCad resistor symbol and metric SMD resistor footprint selected. |
| `f1f0eaa9cdc1` | `RFB6` | `ERJ-6ENF4120V` | `Resistor_SMD:R_0805_2012Metric` | KiCad standard | generic_ok/high | Generic KiCad resistor symbol and metric SMD resistor footprint selected. |
| `ed8491a8dfb2` | `RCOMP1` | `ERJ-6ENF6802V` | `Resistor_SMD:R_0805_2012Metric` | KiCad standard | generic_ok/high | Generic KiCad resistor symbol and metric SMD resistor footprint selected. |
| `6678d49853b5` | `RBLD1 RBLD2 RBLD3` | `ERJ-6ENF1104V` | `Resistor_SMD:R_0805_2012Metric` | KiCad standard | generic_ok/high | Generic KiCad resistor symbol and metric SMD resistor footprint selected. |
| `fdbd851e6691` | `RENPD1 ROE1 RBOOT1 RCANSTB1 RCANSHDN1 RALPD1-RALPD6 RCOLPD1-RCOLPD4 R3V3EN1` | `ERJ-3EKF1003V` | `Resistor_SMD:R_0603_1608Metric` | KiCad standard | generic_ok/high | Generic KiCad resistor symbol and metric SMD resistor footprint selected. |
| `bfcb6ffccd98` | `U2` | `STM32G0B1CBT6` | `Package_QFP:LQFP-48_7x7mm_P0.5mm` | KiCad standard | available/high | KiCad 10 STM32G0B1C_B-C-E_Tx base symbol matches the STM32G0B1CBTx LQFP-48 pinout and avoids embedded alias rendering issues. |
| `341c3c454b2b` | `U3` | `AP63203QWU-7` | `Package_TO_SOT_SMD:TSOT-23-6` | KiCad standard | available/high | KiCad 10 AP63200WU base symbol matches the AP63203QWU-7 TSOT-23-6 pinout and avoids embedded alias rendering issues. |
| `5c75613e51ae` | `L2` | `74439346068` | `Inductor_SMD:L_Wuerth_XHMI-6060` | KiCad standard | available/high | KiCad 10 standard Wurth XHMI-6060 footprint explicitly references the 74439346068 datasheet. |
| `e9d8e3b7229f` | `U4` | `TCAN334GDR` | `Package_SO:SOIC-8_3.9x4.9mm_P1.27mm` | KiCad standard | available/high | KiCad 10 TCAN334 base symbol matches the TCAN334GDR SOIC-8 pinout and avoids embedded alias rendering issues. |
| `814e2343658c` | `U5 U6 U7` | `SN74HC595DR` | `Package_SO:SOIC-16_3.9x9.9mm_P1.27mm` | KiCad standard | available/high | KiCad 10 standard 74HC595 symbol and SOIC-16 footprint selected. |
| `fd8244805ea4` | `U8 U9` | `SN75468DR` | `Package_SO:SOIC-16_3.9x9.9mm_P1.27mm` | KiCad standard | available/high | KiCad 10 standard SN75468 symbol and SOIC-16 footprint selected. |
| `11d8b4f716ea` | `QAH1 QAH2 QAH3 QAH4 QAH5 QAH6` | `MMBTA92-7-F` | `Package_TO_SOT_SMD:SOT-23` | KiCad standard | available/high | KiCad 10 Q_PNP_BEC base symbol matches the MMBTA92 BEC pin order and avoids embedded alias rendering issues. |
| `f7bcbe4c2c2e` | `QAL1 QAL2 QAL3 QAL4 QAL5 QAL6 QCOL1 QCOL2 QCOL3 QCOL4` | `MMBTA42-7-F` | `Package_TO_SOT_SMD:SOT-23` | KiCad standard | available/high | KiCad 10 Q_NPN_BEC base symbol matches the MMBTA42 BEC pin order and avoids embedded alias rendering issues. |
| `861dca0e37e0` | `D2` | `ESD2CAN24DBZRQ1` | `Package_TO_SOT_SMD:SOT-23-3` | KiCad standard | available/high | Project-local 3-pin CAN ESD symbol generated with IO1/GND/IO2 pins; Digi-Key and TI identify the package as SOT-23-3, so KiCad's standard SOT-23-3 footprint is used. |
| `1b89701fcd76` | `Y1` | `ECS-80-12-33-JGN-TR` | `Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm` | KiCad standard | available/high | Digi-Key describes this as a 4-SMD leadless crystal; KiCad's standard 3.2 x 2.5 mm 4-pad crystal footprint matches the ECS ECX-32 package family. |
| `38075d990a55` | `JCAN1` | `OSTVN03A150` | `nixie_clock_bom:OnShore_OSTVN03A150_1x03_P2.54mm_Horizontal` | project-local | available/high | Project-local footprint generated from the On Shore OSTVNXXA150 drawing obtained via Digi-Key: 3 poles, 2.54 mm pitch, 1.30 mm drill, Dim B 5.08 mm, Dim L 8.02 mm. |
| `21190abb0b9b` | `JSWD1` | `FTSH-105-01-F-DV-K` | `nixie_clock_bom:Samtec_FTSH_105_01_F_DV_K_2x05_P1.27mm_Vertical_SMD` | project-local | available/high | Project-local footprint generated for the Samtec FTSH-105-01-F-DV-K keyed 2x05 1.27 mm SMD header; pad geometry follows the KiCad 1.27 mm SMD header pattern and the fab/courtyard outline records the FTSH -DV/-K body. |
| `0855faf5235b` | `C3V3IN1 C3V3IN2` | `GRJ31CR71H475KE11K` | `Capacitor_SMD:C_1206_3216Metric` | KiCad standard | generic_ok/high | Generic KiCad capacitor symbol and metric SMD capacitor footprint selected. |
| `6f285d042801` | `C3V3OUT1 C3V3OUT2` | `GRM31CC81E226KE11L` | `Capacitor_SMD:C_1206_3216Metric` | KiCad standard | generic_ok/high | Generic KiCad capacitor symbol and metric SMD capacitor footprint selected. |
| `cbfe960294cf` | `CBOOT1 C3V3HF1 CDEC1-CDEC8` | `GRM188R72A104KA35D` | `Capacitor_SMD:C_0603_1608Metric` | KiCad standard | generic_ok/high | Generic KiCad capacitor symbol and metric SMD capacitor footprint selected. |
| `fe684ed1a737` | `CY1 CY2` | `GCM1885C1H180FA16D` | `Capacitor_SMD:C_0603_1608Metric` | KiCad standard | generic_ok/high | Generic KiCad capacitor symbol and metric SMD capacitor footprint selected. |
| `80d829cc42d3` | `CVPRE1` | `GRM31CR72E104KW03L` | `Capacitor_SMD:C_1206_3216Metric` | KiCad standard | generic_ok/high | Generic KiCad capacitor symbol and metric SMD capacitor footprint selected. |
| `b5bf7ea69801` | `RALB1-RALB6 RCOLB1-RCOLB4 RNRST1 RSRCLR1` | `ERJ-3EKF1002V` | `Resistor_SMD:R_0603_1608Metric` | KiCad standard | generic_ok/high | Generic KiCad resistor symbol and metric SMD resistor footprint selected. |
| `474097bea409` | `RAHOFF1A-RAHOFF6B` | `ERJ-6ENF4993V` | `Resistor_SMD:R_0805_2012Metric` | KiCad standard | generic_ok/high | Generic KiCad resistor symbol and metric SMD resistor footprint selected. |
| `e4aef89a3602` | `RAHDRV1A-RAHDRV6B` | `ERJ-6ENF2203V` | `Resistor_SMD:R_0805_2012Metric` | KiCad standard | generic_ok/high | Generic KiCad resistor symbol and metric SMD resistor footprint selected. |
| `7004bc31bd64` | `RA1-RA6` | `ERJ-P08F2201V` | `Resistor_SMD:R_1206_3216Metric` | KiCad standard | generic_ok/high | Generic KiCad resistor symbol and metric SMD resistor footprint selected. |
| `ad7525aead93` | `RINS1-RINS4` | `ERJ-P08F1803V` | `Resistor_SMD:R_1206_3216Metric` | KiCad standard | generic_ok/high | Generic KiCad resistor symbol and metric SMD resistor footprint selected. |
| `a4fcc43babc2` | `RPREH1 RPREL1` | `ERJ-6ENF1803V` | `Resistor_SMD:R_0805_2012Metric` | KiCad standard | generic_ok/high | Generic KiCad resistor symbol and metric SMD resistor footprint selected. |
| `bb337a1279b5` | `RT1` | `ERJ-3EKF1200V` | `Resistor_SMD:R_0603_1608Metric` | KiCad standard | generic_ok/high | Generic KiCad resistor symbol and metric SMD resistor footprint selected. |
| `493e165ce731` | `XIN1P1-XIN6P12` | `9353-1-15-80-18-27-10-0` | `nixie_clock_bom:MillMax_9353_1_15_80_18_27_10_0` | project-local | available/high | Project-local footprint generated from Digi-Key parameters for the Mill-Max 9353 receptacle: 1.85 mm mounting drill, 2.29 mm flange diameter, 4.06 mm socket depth. |
