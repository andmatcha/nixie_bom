# KiCad ライブラリ未確定・要レビュー部品

標準ライブラリまたは生成ライブラリで回路図への配置は済ませたが、下記はメーカー専用品、近似フットプリント、またはピン/機械寸法の確認が必要な部品である。

| Ref | MPN | Selected Symbol | Selected Footprint | Issue | Next Action |
| --- | --- | --- | --- | --- | --- |
| `L1` | `7447709102` | `Device:L` | `Inductor_SMD:L_Wuerth_WE-PD-Typ-M-Typ-S` | No exact 7447709102 footprint was found in the KiCad 10 standard libraries; selected the closest WE-PD generic footprint for placement. | Verify pad geometry against the Wurth 7447709102 datasheet before PCB layout. |
| `Q1` | `STD10N60M2` | `Transistor_FET:Q_NMOS_GDSD` | `Package_TO_SOT_SMD:TO-252-3_TabPin4` | Generic four-pin NMOS symbol and TO-252/DPAK footprint selected; tab/drain numbering must be checked against the ST package drawing. | Confirm TO-252 pin order and tab mapping before PCB layout. |
| `D2` | `ESD2CAN24DBZRQ1` | `nixie_clock_bom:ESD2CAN24DBZRQ1` | `Package_TO_SOT_SMD:SOT-23-3` | Project-local 3-pin CAN ESD placeholder symbol generated; SOT-23-3 footprint selected. | Verify pin 1/2/3 assignment against the TI ESD2CAN24DBZRQ1 datasheet before wiring. |
| `Y1` | `ECS-80-12-33-JGN-TR` | `Device:Crystal` | `Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm` | Generic crystal symbol and 3.2 x 2.5 mm 4-pad footprint selected from the BOM package dimensions. | Confirm ECS land pattern and unused pad treatment before PCB layout. |
| `JCAN1` | `OSTVN03A150` | `Connector_Generic:Conn_01x03` | `TerminalBlock:TerminalBlock_Xinya_XY308-2.54-3P_1x03_P2.54mm_Horizontal` | Generic 3-pin connector symbol and 2.54 mm horizontal terminal-block footprint selected; exact OSTVN footprint was not found locally. | Check On Shore OSTVN03A150 hole size and outline before PCB layout. |
| `JSWD1` | `FTSH-105-01-F-DV-K` | `Connector_Generic:Conn_02x05_Odd_Even` | `Connector_PinHeader_1.27mm:PinHeader_2x05_P1.27mm_Vertical_SMD` | Generic 2x05 1.27 mm connector symbol and SMD pin-header footprint selected; exact Samtec keyed header footprint was not found locally. | Verify Samtec FTSH keyed/shroud geometry before PCB layout. |
| `XIN1P1-XIN6P12` | `9353-1-15-80-18-27-10-0` | `Connector_Generic:Conn_01x01` | `nixie_clock_bom:MillMax_9353_1_15_80_18_27_10_0` | Generic one-pin connector symbol selected and a project-local placeholder footprint generated from Digi-Key dimensions. | Verify the Mill-Max receptacle land pattern, drill tolerance, and annular ring before PCB layout. |
