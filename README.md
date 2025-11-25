# Coffin299 Crypto Trader ⚰️📈

Google GenAI (Gemini) を搭載した、自律型暗号資産トレーディングボットです。
「バンバン買ってバンバン売る」アグレッシブな戦略（Coffin299 Strategy）を実行し、2025年の強気相場をターゲットにしています。

## ✨ 主な機能

- **🧠 AI駆動戦略**: Google Gemini 2.0 Flash Exp を使用し、市場データを分析して売買判断（LONG/SHORT）を行います。
- **💻 モダンWebUI**: スタイリッシュなダークテーマのダッシュボード（ポート8088）で、資産状況やAIの判断をリアルタイムに可視化します。
- **📢 Discord連携**: 取引の実行通知や、1時間ごとの資産状況（JPY換算）をDiscordに通知します。
- **🔄 マルチエクスチェンジ**:
  - **Trade.xyz**: メイン取引所（Binance API互換として実装）
  - **Hyperliquid**: 次世代DEX（現在はPaper Modeのみ対応）
- **💸 資金管理**:
  - **Paper Mode**: 仮想資金（BTC/USDC）を使用したデモトレード機能。
  - **Backtest Mode**: 過去データに基づいた検証モード（実装予定）。

## 🚀 インストールと起動

### 必須要件
- Windows
- Python 3.11

### セットアップ手順

1. **リポジトリの準備**
   このフォルダを任意の場所に配置します。

2. **設定ファイルの編集**
   `config.default.yaml` を `config.yaml` という名前でコピーし、以下の項目を設定してください。
   - **API Keys**: 取引所およびGoogle GeminiのAPIキー
   - **Discord Webhook**: 通知用URL
   - **Strategy**: レバレッジやタイムフレーム設定

3. **起動**
   `run_bot.bat` をダブルクリックして実行してください。
   - 自動的に仮想環境（.venv）が作成され、依存ライブラリがインストールされます。
   - 起動後、ブラウザで `http://localhost:8088` にアクセスするとダッシュボードが表示されます。

## ⚙️ 設定 (config.yaml)

| 項目 | 説明 |
| :--- | :--- |
| `active_exchange` | 使用する取引所 (`trade_xyz` または `hyperliquid`) |
| `strategy.paper_mode` | `true` でデモトレード、`false` で実弾トレード |
| `ai.polling_interval_minutes` | AIが市場分析を行う間隔（デフォルト: 60分） |
| `discord.enabled` | Discord通知のON/OFF |

## ⚠️ 免責事項

このソフトウェアは実験的なものであり、実際の取引に使用する場合は自己責任で行ってください。
開発者は、このボットの使用によって生じた損失について一切の責任を負いません。
まずは **Paper Mode (デモトレード)** で十分に検証することをお勧めします。
