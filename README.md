# WhisperLive

リアルタイム音声をOpenAI Whisper APIを使って文字起こしするシンプルなPythonツールです。

## 特徴

- マイクからのリアルタイム音声入力
- 自動的な音声セグメント検出（最大長さまたは無音検出による分割）
- 無音区間の自動スキップ機能
- 低確信度の転写結果をフィルタリング
- 言語指定対応
- 結果のテキストファイル保存機能
- デバッグモード

## 必要環境

- Python 3.6+
- OpenAI API Key

## インストール

```bash
# リポジトリをクローン
git clone https://github.com/monyuonyu/WhisperLive.git
cd WhisperLive

# 依存パッケージをインストール
pip install -r requirements.txt
```

または、必要なパッケージを個別にインストール：

```bash
pip install pyaudio numpy requests pydub
```

## 使い方

### 基本的な使い方

```bash
python whisper_live.py --api_key YOUR_OPENAI_API_KEY
```

APIキーは環境変数 `OPENAI_API_KEY` からも読み込みます。指定がない場合は実行時に入力を求められます。

### コマンドラインオプション

```
usage: whisper_live.py [-h] [--api_key API_KEY] [--language LANGUAGE]
                        [--segment_length SEGMENT_LENGTH]
                        [--energy_threshold ENERGY_THRESHOLD]
                        [--silence_duration SILENCE_DURATION]
                        [--confidence_threshold CONFIDENCE_THRESHOLD]
                        [--no_skip_silence] [--debug] [--output OUTPUT]

シンプルなWhisper API ストリーミング転写

optional arguments:
  -h, --help            ヘルプメッセージを表示して終了します
  --api_key API_KEY     OpenAI API Key
  --language LANGUAGE   言語コード (デフォルト: ja)
  --segment_length SEGMENT_LENGTH
                        1セグメントの最大長さ（秒, デフォルト: 10）
  --energy_threshold ENERGY_THRESHOLD
                        無音判定の閾値 0-1000 (低いほど敏感, デフォルト: 70)
  --silence_duration SILENCE_DURATION
                        無音とみなす最小の長さ（秒, デフォルト: 1.0）
  --confidence_threshold CONFIDENCE_THRESHOLD
                        転写結果の確信度閾値 (0-1, デフォルト: 0.3)
  --no_skip_silence     無音区間スキップを無効化 (すべてのセグメントをAPIに送信)
  --debug               デバッグモードを有効化 (詳細なログを表示)
  --output OUTPUT       転写結果をテキストファイルに保存（ファイルパスを指定）
```

### 使用例

英語の音声を文字起こしする場合：
```bash
python whisper_live.py --language en
```

より短いセグメントで文字起こしする場合：
```bash
python whisper_live.py --segment_length 5
```

無音検出の感度を上げる場合：
```bash
python whisper_live.py --energy_threshold 50 --silence_duration 0.7
```

デバッグモードを有効にして結果をファイルに保存する場合：
```bash
python whisper_live.py --debug --output transcript.txt
```

## 動作方法

1. マイクからの音声を取得し、短いフレーム（20ms）ごとに処理します
2. 音声セグメントを自動的に検出します：
   - 最大セグメント長（デフォルト10秒）に達した場合
   - 一定時間以上の無音が検出された場合
3. 検出したセグメントが無音でなければ、Whisper APIに送信します
4. APIからの応答を受け取り、確信度を評価して表示します
5. すべての転写結果を結合して最終結果とします

## ライセンス

MITライセンス

## トラブルシューティング

### 文字起こしの結果が表示されない場合

- **確信度閾値を下げる**: 転写結果が表示されない場合は、確信度閾値を下げてみてください。
  ```bash
  python whisper_live.py --confidence_threshold 0.1
  ```

- **無音検出の閾値を調整**: 環境によっては無音判定が敏感すぎる場合があります。
  ```bash
  python whisper_live.py --energy_threshold 40
  ```

- **デバッグモードを有効に**: 詳細なログを確認してみてください。
  ```bash
  python whisper_live.py --debug
  ```

### 短い発話が無視される場合

- **無音判定の時間を短くする**:
  ```bash
  python whisper_live.py --silence_duration 0.5
  ```

### APIエラーが発生する場合

- APIキーが正しいことを確認してください
- インターネット接続を確認してください
- OpenAI APIの利用制限に達していないか確認してください

## 注意事項

- このツールを使用するにはOpenAI APIのアカウントとAPIキーが必要です
- APIの使用には料金が発生します
- 最適なパラメータは、使用環境やマイクの特性によって異なります
