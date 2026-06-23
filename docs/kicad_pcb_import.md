# KiCad PCBへの部品読み込み手順

このプロジェクトでは、`kicad/nixie_clock/nixie_clock.kicad_sch` に配置済みの部品へフットプリントを割り当てているため、PCBエディタへ読み込める。

## 自動実行

KiCad同梱Pythonの `pcbnew` APIを使って、回路図上の全配置部品をPCBファイルへ配置する。

```bash
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 \
  tools/import_kicad_schematic_to_pcb.py --replace
```

生成先:

- `kicad/nixie_clock/nixie_clock.kicad_pcb`

配置内容:

- 回路図上の全227部品をPCBへ配置
- `Reference`、`Value`、`Digi-Key Part Number`、`Manufacturer Part Number`、`LineId` をPCB側にも保持
- 既存PCBに部品がある場合は、`--replace` 指定時だけ再生成

## 手動実行

KiCad GUIで行う場合は、次の手順で読み込む。

1. `kicad/nixie_clock/nixie_clock.kicad_pro` を開く。
2. 回路図エディタで `Tools` -> `Update PCB from Schematic...` を開く。
3. 変更一覧に部品追加が表示されることを確認する。
4. `Update PCB` を押してPCBへ反映する。
5. PCBエディタに切り替え、読み込まれたフットプリントを任意の場所へ配置する。
6. `kicad/nixie_clock/nixie_clock.kicad_pcb` を保存する。

KiCadの日本語UIでは、概ね `ツール` -> `回路図から基板を更新...` に相当する。
