# Playwright MCP テスト

このプロジェクトは、Model Context Protocol (MCP) を使用してPlaywrightによるブラウザ自動操作をAIモデルから制御するテスト環境です。Google GeminiまたはOpenAIのモデルを使用して、Playwrightツールを通じてWebブラウザを操作できます。

## 機能

- PlaywrightによるWebブラウザの自動操作
- Google GeminiまたはOpenAIのLLMモデルを選択可能
- 操作中のスクリーンショットの自動保存
- LangChainとLangGraphによるツール呼び出しフロー制御

## 必要条件

- Python 3.8以上
- Playwrightがインストールされたブラウザ
- Google GeminiまたはOpenAIのAPIキー

## インストール

1. リポジトリをクローンするか、ファイルをダウンロードします。

2. 依存パッケージをインストールします：

```bash
pip install -r requirements.txt
```

3. 環境変数を設定します：

```bash
# Google Geminiを使用する場合
export GOOGLE_APIKEY=your_google_api_key

# OpenAIを使用する場合
export OPENAI_API_KEY=your_openai_api_key
```

Windowsの場合は以下のコマンドを使用します：

```cmd
# Google Geminiを使用する場合
set GOOGLE_APIKEY=your_google_api_key

# OpenAIを使用する場合
set OPENAI_API_KEY=your_openai_api_key
```

## 設定

`mcp_config.json`ファイルで、使用するモデルとMCPサーバーの設定を行います：

```json
{
  "modelConfig": {
    "provider": "google",  // "google" または "openai"
    "models": {
      "google": {
        "model": "gemini-2.0-flash",  // または別のGeminiモデル
        "temperature": 0.1
      },
      "openai": {
        "model": "gpt-4.1-mini",  // または別のOpenAIモデル
        "temperature": 0.1
      }
    }
  },
  "mcpServers": [
    {
      "url": "http://localhost:8000",  // PlaywrightのMCPサーバーURL
      "tools": ["browser_*"]  // 使用するツールパターン
    }
  ]
}
```

## 使用方法

1. スクリプトを実行します：

```bash
python playwright_mcp_langchain_tools.py
```

2. プロンプトが表示されたら、実行したいブラウザ操作を日本語で入力します。例：
   - "Googleのトップページにアクセスして検索してください"
   - "ウィキペディアで人工知能について調べてください"

3. AIがPlaywrightを使ってブラウザを操作し、スクリーンショットを保存します。

4. 終了するには、`exit`または`quit`と入力します。

## スクリーンショット

スクリーンショットは自動的に`screenshots`ディレクトリに保存されます。ファイル名は日時とカウンターに基づいて生成されます。

## 注意事項

- ブラウザ操作は実際のブラウザを使用するため、操作中はブラウザウィンドウが開きます。
- ネットワークエラーが発生した場合は、コマンドを再実行してみてください。
- 複雑な操作や長時間の操作の場合は、適切なタイムアウト設定が必要な場合があります。
- GPT-4.1-nanoの場合、正しくスクリーンショットを取得できない場合があります。
- 操作が長い場合、LLMの戻りが遅くなります。今後入力トークン数の圧縮などを行い、対策を行う予定です。

## トラブルシューティング

- APIキーが正しく設定されていることを確認してください
- MCPサーバーが正しく起動していることを確認してください
- Playwrightが正しくインストールされていることを確認してください