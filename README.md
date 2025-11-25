# Coffin299 Crypto Trader ⚰️📈

Google GenAI (Gemini) を搭載した、自律型暗号資産トレーディングボットです。
「バンバン買ってバンバン売る」アグレッシブな戦略（Coffin299 Strategy）を実行し、2025年の強気相場をターゲットにしています。

## ✨ 主な機能

- **🧠 AI駆動戦略**: Google Gemini 2.5 pro を使用し、市場データを分析して売買判断（LONG/SHORT）を行います。
- **🔄 APIキーローテーション**: 複数のGemini APIキーを登録し、リクエストごとに自動で切り替えることでレート制限を回避します。
- **💻 モダンWebUI**: スタイリッシュなダークテーマのダッシュボード（ポート8088）で、資産状況やAIの判断をリアルタイムに可視化します。
- **📢 Discord Bot連携**:
  - **Trade Alerts**: 売買実行時にDiscordに通知
  - **Wallet Updates**: 1時間ごとの資産状況（JPY換算）をDiscordに通知
  - チャンネルを個別に設定可能
- **💸 資金管理**:
  - **Paper Mode**: ETHを元手としたデモトレード機能（初期設定: 0.044 ETH 約2万円）。
  - **Base Currency**: ETH基軸で運用し、USDC建てで取引を行います。

## 🚀 インストールと起動

### 必須要件
- Windows
- Python 3.11

### セットアップ手順

1. **リポジトリの準備**
   このフォルダを任意の場所に配置します。

2. **設定ファイルの編集**
   `config.default.yaml` を `config.yaml` という名前でコピーし、以下の項目を設定してください。
   - **ai.api_keys**: Gemini APIキーのリスト（複数登録推奨）
   - **discord.bot_token**: Discord Botのトークン
   - **discord.channels**: 通知先のチャンネルID

3. **起動**
   `run_bot.bat` をダブルクリックして実行してください。
   - 自動的に仮想環境（.venv）が作成され、依存ライブラリがインストールされます。
   - 起動後、ブラウザで `http://localhost:8088` にアクセスするとダッシュボードが表示されます。

## ⚙️ 設定 (config.yaml)

| 項目 | 説明 |
| :--- | :--- |
| `active_exchange` | 使用する取引所 (`trade_xyz` または `hyperliquid`) |
| `strategy.paper_mode` | `true` でデモトレード、`false` で実弾トレード |
| `ai.api_keys` | Gemini APIキーのリスト（ローテーション用） |
| `discord.bot_token` | Discord Bot Token |
| `discord.channels` | `trade_alerts` (売買), `wallet_updates` (残高) のID |

## 🔑 APIキーの取得方法

### 1. Trade.xyz (Hyperliquid API)
Trade.xyz は **Hyperliquid API** を使用します。
1. [Trade.xyz](https://trade.xyz/) または [Hyperliquid](https://app.hyperliquid.xyz/) にウォレットを接続します。
2. **API** セクションで **API Wallet** を作成します。
3. **Wallet Address** と **Private Key** を `config.yaml` の `trade_xyz` セクションに設定します。

### 2. Hyperliquid (DEX)
1. [Hyperliquid](https://app.hyperliquid.xyz/) にウォレットを接続します。
2. **API** セクションに移動し、**API Wallet** を作成します。
3. 表示される **Wallet Address** と **Private Key** を `config.yaml` に設定します。

### 3. Google Gemini
1. [Google AI Studio](https://aistudio.google.com/) にアクセスします。
2. **Get API key** をクリックします。
3. **Create API key** でキーを発行し、`config.yaml` の `ai.api_keys` に追加します。

## ⚠️ 免責事項

このソフトウェアは実験的なものであり、実際の取引に使用する場合は自己責任で行ってください。
開発者は、このボットの使用によって生じた損失について一切の責任を負いません。
まずは **Paper Mode (デモトレード)** で十分に検証することをお勧めします。
