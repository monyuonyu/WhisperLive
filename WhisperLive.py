import os
import time
import wave
import pyaudio
import requests
import threading
import tempfile
import argparse
import numpy as np
import collections
from pydub import AudioSegment

class WhisperLiveTranscriber:
    """
    WhisperLive: リアルタイム音声転写クラス
    
    マイクから音声を取得し、音声セグメントを自動検出して
    OpenAI Whisper APIに送信してリアルタイムで文字起こしを行います。
    """
    
    def __init__(self, api_key, language='ja', sample_rate=16000, 
                 segment_length=10, energy_threshold=70, 
                 silence_duration=1.0, confidence_threshold=0.3,
                 skip_silence=True, debug_mode=False):
        """
        WhisperLive転写クラスを初期化します
        
        引数:
            api_key (str): OpenAI API Key
            language (str): 言語コード (デフォルト: 'ja')
            sample_rate (int): サンプルレート (デフォルト: 16000Hz)
            segment_length (int): 1セグメントの最大長さ（秒）
            energy_threshold (int): 無音判定の閾値 (0-1000)
            silence_duration (float): 無音とみなす最小の長さ（秒）
            confidence_threshold (float): 転写結果の確信度閾値 (0-1)
            skip_silence (bool): 無音区間をスキップするかどうか
            debug_mode (bool): デバッグログを表示するかどうか
        """
        self.api_key = api_key
        self.language = language
        self.sample_rate = sample_rate
        self.channels = 1
        self.format = pyaudio.paInt16
        self.is_recording = False
        self.transcriptions = []
        self.debug_mode = debug_mode
        
        # 音声セグメントの設定
        self.segment_length = segment_length  # 秒
        self.energy_threshold = energy_threshold  # 無音判定の閾値
        self.silence_duration = silence_duration  # 無音とみなす最小の長さ（秒）
        self.confidence_threshold = confidence_threshold  # 転写結果の確信度閾値
        self.skip_silence = skip_silence  # 無音区間をスキップするかどうか
        
        # フレーム設定
        self.frame_duration_ms = 20  # 1フレームの長さ（ミリ秒）
        self.frames_per_buffer = int(sample_rate * self.frame_duration_ms / 1000)
        self.samples_per_second = sample_rate
        
        # ストリーム処理用変数
        self.buffer = []
        
        # APIエンドポイント
        self.api_url = "https://api.openai.com/v1/audio/transcriptions"
        
        self._debug("WhisperLiveTranscriberを初期化しました")
        self._debug(f"設定: セグメント長={segment_length}秒, 無音閾値={energy_threshold}/1000, 無音判定={silence_duration}秒")
        if self.skip_silence:
            self._debug("無音区間検出: 有効 (無音セグメントはAPIに送信されません)")
        
        # 常に表示する重要な情報
        print("Whisper API 文字起こしツール")
        print("------------------------------")
        print(f"言語: {language}, 確信度閾値: {confidence_threshold}")
        print("録音を開始します。Ctrl+Cで終了してください。")
        print("------------------------------")
    
    def _debug(self, message):
        """デバッグモードが有効な場合のみメッセージを表示します"""
        if self.debug_mode:
            print(f"[DEBUG] {message}")
    
    def start_recording(self):
        """録音を開始し、処理スレッドを開始します"""
        if self.is_recording:
            self._debug("既に録音中です")
            return
        
        self.is_recording = True
        self.transcriptions = []
        
        # PyAudioインスタンスを作成
        self.audio = pyaudio.PyAudio()
        
        # オーディオストリームを開く
        try:
            self.stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.frames_per_buffer
            )
        except Exception as e:
            self._debug(f"オーディオストリームの初期化中にエラーが発生しました: {e}")
            self.is_recording = False
            self.audio.terminate()
            raise RuntimeError(f"マイクへのアクセスに失敗しました: {e}")
        
        # プログレスマーカーの表示
        self._show_progress_marker()
        
        # 処理用スレッド
        self.processing_thread = threading.Thread(target=self._process_audio)
        self.processing_thread.daemon = True
        self.processing_thread.start()
    
    def _show_progress_marker(self):
        """録音中であることを示すプログレスマーカーを表示します"""
        if self.is_recording:
            print(".", end='', flush=True)
            threading.Timer(1.0, self._show_progress_marker).start()
    
    def _process_audio(self):
        """
        音声ストリームを処理し、時間ベースでセグメント分割します
        
        このメソッドは内部スレッドとして実行され、以下の条件でセグメントを分割します:
        1. 最大セグメント長に達した場合
        2. 一定時間以上の無音が検出された場合
        """
        frames = []
        frames_since_start = 0
        silence_frames = 0
        max_frames = int(self.segment_length * 1000 / self.frame_duration_ms)  # セグメント最大フレーム数
        silence_threshold_frames = int(self.silence_duration * 1000 / self.frame_duration_ms)  # 無音判定フレーム数
        
        while self.is_recording:
            try:
                # 音声データを読み取り
                data = self.stream.read(self.frames_per_buffer, exception_on_overflow=False)
                frames.append(data)
                frames_since_start += 1
                
                # 現在のフレームのエネルギーを計算
                audio_np = np.frombuffer(data, dtype=np.int16)
                energy = np.sqrt(np.mean(audio_np.astype(np.float32)**2))
                normalized_energy = min(1000, energy / 32.767)
                
                # 無音判定
                if normalized_energy < self.energy_threshold:
                    silence_frames += 1
                else:
                    silence_frames = 0
                
                # セグメント分割条件判定
                should_process = False
                
                # 1. 最大セグメント長に達した
                if frames_since_start >= max_frames:
                    should_process = True
                    reason = "最大セグメント長に達しました"
                
                # 2. 無音が一定時間続いた
                elif silence_frames >= silence_threshold_frames and frames_since_start > silence_threshold_frames * 2:
                    should_process = True
                    reason = f"{self.silence_duration}秒の無音を検出しました"
                
                # セグメント処理
                if should_process and frames:
                    self._debug(f"音声セグメント分割: {reason} (長さ: {frames_since_start * self.frame_duration_ms / 1000:.1f}秒)")
                    
                    # 無音で区切った場合は、無音部分を少し含める
                    if "無音" in reason:
                        processing_frames = frames[:-silence_frames] + frames[-silence_frames:][:int(silence_threshold_frames/3)]
                    else:
                        processing_frames = frames
                    
                    # 検出したセグメントを処理
                    self._process_segment(processing_frames)
                    
                    # フレームをリセット
                    frames = []
                    frames_since_start = 0
                    silence_frames = 0
            
            except Exception as e:
                self._debug(f"音声処理中にエラーが発生しました: {e}")
                time.sleep(0.1)  # エラー時に少し待機
    
    def _process_segment(self, frames):
        """
        検出された音声セグメントを処理します
        
        無音セグメントの場合はスキップし、有音セグメントの場合は
        別スレッドで転写処理を実行します。
        
        引数:
            frames (list): 処理する音声フレームのリスト
        """
        if not frames:
            return
            
        # 音声セグメントが無音かどうかをチェック
        is_silent = self._is_silent_segment(frames)
        
        if is_silent and self.skip_silence:
            self._debug("無音セグメントを検出したため、転写処理をスキップします")
            return
        
        # 別スレッドで処理
        processing_thread = threading.Thread(
            target=self._transcribe_segment,
            args=(frames.copy(),)
        )
        processing_thread.daemon = True
        processing_thread.start()
        
    def _is_silent_segment(self, frames):
        """
        音声セグメントが無音かどうかを判定します
        
        引数:
            frames (list): 判定する音声フレームのリスト
            
        返値:
            bool: 無音セグメントの場合はTrue、それ以外はFalse
        """
        # フレームをnumpy配列に変換して連結
        audio_data = []
        for frame in frames:
            audio_np = np.frombuffer(frame, dtype=np.int16)
            audio_data.append(audio_np)
        
        if not audio_data:
            return True
            
        audio_np = np.concatenate(audio_data)
        
        # セグメント全体のRMSエネルギーを計算
        energy = np.sqrt(np.mean(audio_np.astype(np.float32)**2))
        normalized_energy = min(1000, energy / 32.767)
        
        # 活発な音声を含むフレームの割合を計算
        active_frames = 0
        total_frames = len(frames)
        
        for frame in frames:
            frame_np = np.frombuffer(frame, dtype=np.int16)
            frame_energy = np.sqrt(np.mean(frame_np.astype(np.float32)**2))
            frame_normalized = min(1000, frame_energy / 32.767)
            
            if frame_normalized > self.energy_threshold:
                active_frames += 1
        
        active_ratio = active_frames / total_frames if total_frames > 0 else 0
        
        # 無音判定：
        # 1. 全体のエネルギーが閾値の50%より低い、かつ
        # 2. 活発なフレームの割合が5%未満
        is_silent = normalized_energy < self.energy_threshold * 0.5 and active_ratio < 0.05
        
        if is_silent:
            self._debug(f"無音セグメント検出: 全体エネルギー={normalized_energy:.1f}/{self.energy_threshold}, 活発フレーム比率={active_ratio:.2f}")
        
        return is_silent
    
    def _get_transcript_confidence(self, text):
        """
        転写テキストから信頼度を推定します（ヒューリスティック）
        
        引数:
            text (str): 転写されたテキスト
            
        返値:
            float: 推定された信頼度 (0.0-1.0)
        """
        if not text or len(text.strip()) == 0:
            return 0.0
        
        # 定型句リスト
        common_phrases = [
            "ご視聴ありがとうございました。", 
            "thank you", "thanks", 
            "はい", "いいえ",
            "こんにちは", "さようなら"
        ]
        
        text_lower = text.lower().strip()
        
        for phrase in common_phrases:
            if phrase.lower() in text_lower:
                if len(text_lower) < len(phrase) * 1.5:
                    return 0.3
        
        # 文字数が多いほど確信度が高い（最大0.9）
        char_confidence = min(0.9, len(text.strip()) / 50)
        
        # 単語数（空白で区切った数）
        words = text.strip().split()
        word_confidence = min(0.9, len(words) / 10)
        
        # 合成確信度（文字数と単語数の大きい方を採用）
        confidence = max(char_confidence, word_confidence)
        
        return confidence
    
    def _transcribe_segment(self, frames):
        """
        音声セグメントをWhisper APIに送信して転写します
        
        引数:
            frames (list): 転写する音声フレームのリスト
        """
        try:
            # 一時ファイルを作成
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_filename = temp_file.name
            
            self._debug(f"一時ファイルを作成: {temp_filename}")
            
            # WAVファイルとして保存
            with wave.open(temp_filename, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.audio.get_sample_size(self.format))
                wf.setframerate(self.sample_rate)
                wf.writeframes(b''.join(frames))
            
            # WAVファイルをMP3に変換
            audio = AudioSegment.from_wav(temp_filename)
            mp3_filename = temp_filename.replace('.wav', '.mp3')
            audio.export(mp3_filename, format="mp3")
            
            self._debug(f"APIリクエスト送信中...")
            
            # APIリクエスト
            transcription = self._transcribe_audio(mp3_filename)
            
            # 一時ファイルの削除
            try:
                os.remove(temp_filename)
                os.remove(mp3_filename)
            except Exception as e:
                self._debug(f"一時ファイル削除エラー: {e}")
            
            # 転写結果の信頼性を評価
            if transcription and transcription.strip():
                confidence = self._get_transcript_confidence(transcription)
                
                if confidence >= self.confidence_threshold:
                    self.transcriptions.append(transcription)
                    # エネルギーや信頼度などの詳細情報はデバッグモードでのみ表示
                    self._debug(f"転写結果 (確信度: {confidence:.2f}): {transcription}")
                    # 通常モードでは転写結果のみ表示
                    if not self.debug_mode:
                        print(f"\n> {transcription}")
                else:
                    self._debug(f"低確信度の転写結果を無視 ({confidence:.2f}): {transcription}")
            else:
                self._debug("転写結果が空でした")
        
        except Exception as e:
            import traceback
            self._debug(f"転写中にエラーが発生しました: {e}")
            if self.debug_mode:
                traceback.print_exc()
    
    def _transcribe_audio(self, audio_file):
        """
        Whisper APIを使用して音声ファイルを転写します
        
        引数:
            audio_file (str): 転写する音声ファイルのパス
            
        返値:
            str: 転写されたテキスト、エラー時は空文字列
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        
        with open(audio_file, 'rb') as f:
            files = {
                'file': (os.path.basename(audio_file), f, 'audio/mpeg'),
                'model': (None, 'whisper-1'),
                'language': (None, self.language)
            }
            
            try:
                response = requests.post(
                    self.api_url,
                    headers=headers,
                    files=files
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get('text', '')
                else:
                    self._debug(f"APIエラー: {response.status_code}, {response.text}")
                    return ""
            
            except Exception as e:
                self._debug(f"API通信中にエラーが発生しました: {e}")
                return ""
    
    def stop_recording(self):
        """
        録音を停止し、最終結果を返します
        
        返値:
            str: 全セグメントの転写結果を結合したテキスト
        """
        if not self.is_recording:
            self._debug("録音していません")
            return ""
        
        self.is_recording = False
        
        # ストリームとPyAudioを閉じる
        if hasattr(self, 'stream') and self.stream:
            self.stream.stop_stream()
            self.stream.close()
        
        if hasattr(self, 'audio') and self.audio:
            self.audio.terminate()
        
        # 処理スレッドが終了するのを待つ
        if hasattr(self, 'processing_thread') and self.processing_thread:
            self.processing_thread.join(timeout=2.0)
        
        # 最終結果を結合
        final_transcription = ' '.join(self.transcriptions)
        print("\n\n最終転写結果:")
        print("------------------------------")
        print(final_transcription)
        print("------------------------------")
        return final_transcription


def main():
    """メイン関数：コマンドライン引数を解析し、転写処理を実行します"""
    parser = argparse.ArgumentParser(description='WhisperLive - リアルタイム音声転写ツール')
    parser.add_argument('--api_key', type=str, help='OpenAI API Key')
    parser.add_argument('--language', type=str, default='ja', help='言語コード (デフォルト: ja)')
    parser.add_argument('--segment_length', type=int, default=10, 
                        help='1セグメントの最大長さ（秒, デフォルト: 10）')
    parser.add_argument('--energy_threshold', type=int, default=70, 
                        help='無音判定の閾値 0-1000 (低いほど敏感, デフォルト: 70)')
    parser.add_argument('--silence_duration', type=float, default=1.0, 
                        help='無音とみなす最小の長さ（秒, デフォルト: 1.0）')
    parser.add_argument('--confidence_threshold', type=float, default=0.3,
                        help='転写結果の確信度閾値 (0-1, デフォルト: 0.3)')
    parser.add_argument('--no_skip_silence', action='store_true',
                        help='無音区間スキップを無効化 (すべてのセグメントをAPIに送信)')
    parser.add_argument('--debug', action='store_true',
                        help='デバッグモードを有効化 (詳細なログを表示)')
    parser.add_argument('--output', type=str, 
                        help='転写結果をテキストファイルに保存（ファイルパスを指定）')
    
    args = parser.parse_args()
    
    api_key = args.api_key
    
    # APIキーがコマンドラインで指定されていない場合、環境変数またはユーザー入力を使用
    if not api_key:
        api_key = os.environ.get('OPENAI_API_KEY')
        
    if not api_key:
        api_key = input("OpenAI API Keyを入力してください: ")
    
    # 転写器を初期化
    try:
        transcriber = WhisperLiveTranscriber(
            api_key=api_key,
            language=args.language,
            segment_length=args.segment_length,
            energy_threshold=args.energy_threshold,
            silence_duration=args.silence_duration,
            confidence_threshold=args.confidence_threshold,
            skip_silence=not args.no_skip_silence,
            debug_mode=args.debug
        )
        
        # 録音開始
        transcriber.start_recording()
        
        # ユーザーがCtrl+Cを押すまで待機
        while True:
            time.sleep(0.1)
    
    except KeyboardInterrupt:
        print("\n\n録音を停止します...")
        # 録音停止
        if 'transcriber' in locals() and transcriber.is_recording:
            final_text = transcriber.stop_recording()
            
            # 結果をファイルに保存（指定されている場合）
            if args.output:
                try:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        f.write(final_text)
                    print(f"\n転写結果を {args.output} に保存しました。")
                except Exception as e:
                    print(f"\nファイル保存中にエラーが発生しました: {e}")
    
    except Exception as e:
        import traceback
        print(f"エラーが発生しました: {e}")
        if args.debug:
            traceback.print_exc()
        if 'transcriber' in locals() and hasattr(transcriber, 'is_recording') and transcriber.is_recording:
            transcriber.stop_recording()


if __name__ == "__main__":
    main()
