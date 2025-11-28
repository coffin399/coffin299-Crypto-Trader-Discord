# Coffin299 Crypto Trader ⚰️📈

Google GenAI (Gemini) と **機械学習 (Random Forest)** を融合させた、自律型暗号資産トレーディングボットです。
「バンバン買ってバンバン売る」アグレッシブな戦略（Coffin299 Strategy）を実行し、2025年の強気相場をターゲットにしています。

## ✨ 主な機能

- **🧠 AI & 機械学習のハイブリッド戦略**:
  - **Gemini 2.5 Pro**: 市場全体を分析し、最適な**取引ペア（通貨）を選定**します。
  - **Random Forest (scikit-learn)**: 選定されたペアの**過去1年分のデータ**を自動で取得・学習し、高精度な売買シグナル（BUY/SELL）を生成します。
  - **自動再学習**: Geminiが新しいペアを推奨すると、即座にそのペアの過去データを取得し、モデルを再学習させます。
- **⚡ Intel N100 最適化**:
  - 省電力CPU（Intel N100等）でも快適に動作するように、学習プロセスをマルチコア並列化＆非同期スレッド化。
  - ボットのメインループを止めることなく、バックグラウンドで学習を行います。
- **🔄 APIキーローテーション**: 複数のGemini APIキーを登録し、リクエストごとに自動で切り替えることでレート制限を回避します。
- **💻 モダンWebUI**: 
  - スタイリッシュなダークテーマのダッシュボード（ポート8088）
  - **MetaMask連携**: WebUIからMetaMaskを接続し、ウォレットアドレスを表示可能
  - 資産状況やAIの判断をリアルタイムに可視化
- **📢 Discord Bot連携**:
  - **Trade Alerts**: 売買実行時にDiscordに通知
  - **Wallet Updates**: 1時間ごとの資産状況（JPY換算）をDiscordに通知
  - チャンネルを個別に設定可能
- **💸 資金管理**:
  - **Paper Mode**: ETHを元手としたデモトレード機能（初期設定: 0.044 ETH 約2万円）。
  - **Keyless Hyperliquid Paper Mode**: HyperliquidのPaper Modeは**APIキー（秘密鍵）なし**で動作可能。デポジット不要で戦略テストができます。
  - **Base Currency**: ETH基軸で運用し、USDC建てで取引を行います。
- **🔌 対応取引所**:
  - **Binance Japan**: 国内取引所
  - **Hyperliquid**: 高速DEX（Paper Modeはキー不要）
  - **Tread.fi**: アルゴリズム取引プラットフォーム

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
   - **active_exchange**: 使用する取引所を選択 (`hyperliquid` 推奨)

3. **起動**
   `run_bot.bat` をダブルクリックして実行してください。
   - 自動的に仮想環境（.venv）が作成され、依存ライブラリがインストールされます。
   - 初回起動時、**過去1年分のデータ取得とAI学習**が始まります（数秒〜数十秒かかります）。
   - 起動後、ブラウザで `http://localhost:8088` にアクセスするとダッシュボードが表示されます。

## ⚙️ 設定 (config.yaml)

| 項目 | 説明 |
| :--- | :--- |
| `active_exchange` | 使用する取引所 (`hyperliquid`, `binance_japan`, `tread_fi`) |
| `strategy.timeframe` | 取引の時間足（デフォルト: `15m`） |
| `strategy.paper_mode` | `true` でデモトレード、`false` で実弾トレード |
| `ai.api_keys` | Gemini APIキーのリスト（ローテーション用） |
| `discord.bot_token` | Discord Bot Token |
| `discord.channels` | `trade_alerts` (売買), `wallet_updates` (残高) のID |

## 🔑 APIキーの取得方法

### 1. Google Gemini
1. [Google AI Studio](https://aistudio.google.com/) にアクセスします。
2. **Get API key** をクリックします。
3. **Create API key** でキーを発行し、`config.yaml` の `ai.api_keys` に追加します。

### 2. Hyperliquid (Trade.xyz)
**Paper Mode (デモ) の場合、APIキーは不要です。**
実弾トレードを行う場合のみ、以下の手順が必要です：
1. [Hyperliquid](https://app.hyperliquid.xyz/) にウォレットを接続します。
2. **API** セクションで **API Wallet** を作成します。
3. **Wallet Address** と **Private Key** を `config.yaml` の `hyperliquid` セクションに設定します。

### 3. Binance Japan (binance_japan)
1. [Binance Japan](https://www.binance.com/ja) にログインします。
2. **API管理** からAPIキーを作成します。
3. **API Key** と **Secret Key** を `config.yaml` の `binance_japan` セクションに設定します。

## ⚠️ 免責事項

このソフトウェアは実験的なものであり、実際の取引に使用する場合は自己責任で行ってください。
開発者は、このボットの使用によって生じた損失について一切の責任を負いません。
まずは **Paper Mode (デモトレード)** で十分に検証することをお勧めします。
