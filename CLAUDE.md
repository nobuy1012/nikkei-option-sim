# CLAUDE.md — nikkei-option-sim

## プロジェクト概要

日経225オプションのポジション管理・損益シミュレーターのWebアプリ。
Google Spreadsheetで運用していた「OP損益早見表」をApp化したもの。
個人利用目的。GitHub Pages（nobuy1012.github.io/nikkei-option-sim）で無料公開。

## 技術スタック

- 純粋なHTML/CSS/JS（フレームワークなし）
- Chart.js 4.4.1（CDN）
- Google Fonts: IBM Plex Mono + Noto Sans JP
- デプロイ: GitHub Pages（mainブランチ / root）

## ファイル構成

```
nikkei-option-sim/
├── index.html   # アプリ本体（1ファイル完結）
├── CLAUDE.md    # このファイル
├── app.py       # 旧Pythonスクリプト（参考用）
└── requirements.txt
```

## スプレッドシートの構造（App化の元ネタ）

元スプレッドシート: OP損益早見表（Google Sheets）
シート名:「【雛形】損益計算表」

### 上部（行1〜34）
- 損益早見表マトリクス（横軸: 日経225価格 50円刻み、縦軸: 価格帯）
- 全ポジション合計の損益を表示
- 損切り・利益幅フィールドあり

### 下部（行36以降）: オプション計算表

第1〜8組の構成（各組が独立したポジション）：

| 項目 | 内容 |
|------|------|
| 組番号 | 第1〜8組 |
| タイプ | コール or プット（切り替え可） |
| 有効/無効 | チェックボックスで組全体をON/OFF |
| 売り | 行使価格・プレミアム・枚数 × 2行 |
| 買い | 行使価格・プレミアム・枚数 × 2行 |
| 最大損失 | 組ごとに自動計算・表示 |

第1〜4組: コール（デフォルト）
第5〜8組: プット（デフォルト）

## 損益計算ロジック

- 1枚 = 1,000倍（MULT = 1000）
- 満期損益ベース（Black-Scholesなし、シンプルな満期ペイオフ）
- コール: max(S - K, 0)
- プット: max(K - S, 0)
- 売り: -(満期価値 - プレミアム) × 枚数 × MULT
- 買い: +(満期価値 - プレミアム) × 枚数 × MULT

## UIデザイン

- ダークテーマ（#0f1117ベース）
- サマリーバー: NET PREMIUM / MAX PROFIT / MAX LOSS / BREAKEVEN
- メインチャート: 満期損益バーチャート（緑=利益、赤=損失）
- 第1〜8組のカードグリッド（2列）
- 各カード: SELL（赤系）/ BUY（緑系）のレグブロック

## 今後やりたいこと（TODO）

- [ ] ポジションの保存・読み込み（localStorage）
- [ ] 現在価値曲線の追加（Black-Scholes、残存日数スライダー）
- [ ] 損益早見表マトリクスの表示（スプレッドシートの上部部分）
- [ ] スマホ対応の改善
- [ ] タイトル（限月名）の入力フィールド

## GitHub Pages

URL: https://nobuy1012.github.io/nikkei-option-sim/
設定: Settings → Pages → Branch: main / root
