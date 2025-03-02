import os
import json
import tkinter as tk
from tkinter import ttk, messagebox
from WhisperLive import WhisperLiveTranscriber

########################################################################
# WhisperLiveGUI クラス
########################################################################
class WhisperLiveGUI:
    """
    WhisperLiveのGUIアプリケーションクラス
    
    このクラスはWhisperを使用したリアルタイム音声文字起こしのGUIインターフェースを提供します。
    
    Attributes:
        root (tk.Tk): メインウィンドウ
        transcriber (WhisperLiveTranscriber): 音声文字起こしエンジン
        is_recording (bool): 録音状態のフラグ
        api_key (str): OpenAI APIキー
    """

    ########################################################################
    # コンストラクタ
    ########################################################################
    def __init__(self):
        """
        WhisperLiveGUIのインスタンスを初期化します。
        メインウィンドウの作成、スタイルの設定、APIキーの読み込みを行います。
        """
        self.root = tk.Tk()
        self.root.title("WhisperLive")
        self.root.geometry("1000x700")
        self.transcriber = None
        self.is_recording = False
        
        # スタイルの設定
        self.setup_styles()
        
        # API Key の設定
        self.api_key = self.load_api_key()
        
        self.create_widgets()
    
    ########################################################################
    # スタイル設定
    ########################################################################
    def setup_styles(self):
        """
        GUIのスタイル設定を行います。
        
        以下のスタイルを設定します：
        - フレーム
        - ラベル
        - ボタン
        - スケール
        - エントリー
        - チェックボタン
        - ラジオボタン
        """
        style = ttk.Style()
        style.theme_use('clam')
        
        # カラーパレット
        PRIMARY_COLOR = "#2196F3"  # メインカラー（青）
        SECONDARY_COLOR = "#757575"  # セカンダリーカラー（グレー）
        BG_COLOR = "#FAFAFA"  # 背景色（明るいグレー）
        ACCENT_COLOR = "#1976D2"  # アクセントカラー（濃い青）
        
        # フレームのスタイル
        style.configure('Main.TFrame', background=BG_COLOR)
        style.configure('Controls.TFrame', background=BG_COLOR)
        
        # ラベルのスタイル
        style.configure('Title.TLabel', 
                       font=('Segoe UI', 24, 'bold'),
                       padding=15,
                       background=BG_COLOR,
                       foreground=PRIMARY_COLOR)
        style.configure('Header.TLabel',
                       font=('Segoe UI', 11),
                       padding=5,
                       background=BG_COLOR,
                       foreground=SECONDARY_COLOR)
        
        # ボタンのスタイル
        style.configure('Record.TButton',
                       font=('Segoe UI', 11, 'bold'),
                       padding=(20, 10),
                       background=PRIMARY_COLOR)
        style.map('Record.TButton',
                  background=[('active', ACCENT_COLOR)],
                  foreground=[('active', 'white')])
        
        style.configure('Save.TButton',
                       font=('Segoe UI', 11),
                       padding=(20, 10),
                       background=SECONDARY_COLOR)
        style.map('Save.TButton',
                  background=[('active', '#616161')])
        
        # スケールのスタイル
        style.configure('Custom.Horizontal.TScale',
                       background=BG_COLOR,
                       troughcolor=PRIMARY_COLOR,
                       sliderlength=15)
        
        # ラベルフレームのスタイル
        style.configure('Settings.TLabelframe',
                       background=BG_COLOR,
                       padding=10)
        style.configure('Settings.TLabelframe.Label',
                       font=('Segoe UI', 11, 'bold'),
                       background=BG_COLOR,
                       foreground=PRIMARY_COLOR)
        
        # エントリーとスピンボックスのスタイル
        style.configure('TEntry',
                       fieldbackground='white',
                       padding=5)
        style.configure('TSpinbox',
                       fieldbackground='white',
                       padding=5)
        
        # チェックボタンのスタイル
        style.configure('TCheckbutton',
                       background=BG_COLOR,
                       font=('Segoe UI', 10))
        style.map('TCheckbutton',
                  foreground=[('active', PRIMARY_COLOR)])
        
        # ラジオボタンのスタイル
        style.configure('TRadiobutton',
                       background=BG_COLOR,
                       font=('Segoe UI', 10))
        style.map('TRadiobutton',
                  foreground=[('active', PRIMARY_COLOR)])

    ########################################################################
    # API Keyの読み込み
    ########################################################################
    def load_api_key(self):
        """
        環境変数からOpenAI APIキーを読み込みます。
        
        Returns:
            str: APIキー。環境変数が未設定の場合は空文字列
        """
        return os.environ.get('OPENAI_API_KEY', '')
    
    ########################################################################
    # API Keyの保存
    ########################################################################
    def save_api_key(self, api_key):
        """
        APIキーを環境変数に保存します。
        
        Args:
            api_key (str): 保存するAPIキー
            
        Notes:
            Windowsの場合はsetxコマンドを使用して永続的に保存します。
        """
        os.environ['OPENAI_API_KEY'] = api_key
        try:
            # Windowsの場合
            os.system(f'setx OPENAI_API_KEY "{api_key}"')
        except Exception as e:
            print(f"Failed to save API key to environment variable: {e}")

    ########################################################################
    # GUIウィジェットの作成
    ########################################################################
    def create_widgets(self):
        """
        GUIウィジェットを作成し配置します。
        
        以下のウィジェットを作成します：
        - メインフレーム
        - APIキー入力欄
        - 詳細設定パネル（言語選択、閾値設定等）
        - 録音コントロールボタン
        - テキスト表示エリア
        - ステータスバー
        """
        # メインウィンドウの背景色を設定
        self.root.configure(background='#FAFAFA')
        
        # メインフレーム
        main_frame = ttk.Frame(self.root, style='Main.TFrame', padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # タイトル
        title_label = ttk.Label(main_frame, 
                               text="WhisperLive - リアルタイム音声文字起こし",
                               style='Title.TLabel')
        title_label.grid(row=0, column=0, columnspan=4, sticky=(tk.W, tk.E))
        
        # 左側のコントロールパネル
        control_panel = ttk.Frame(main_frame, style='Controls.TFrame')
        control_panel.grid(row=1, column=0, sticky=(tk.N, tk.W), padx=10, pady=5)
        
        # API Key 入力
        api_frame = ttk.LabelFrame(control_panel, text="API設定", style='Settings.TLabelframe')
        api_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=10)
        
        ttk.Label(api_frame, text="OpenAI API Key:", style='Header.TLabel').grid(row=0, column=0, sticky=tk.W, padx=5)
        self.api_key_var = tk.StringVar(value=self.api_key)
        api_key_entry = ttk.Entry(api_frame, textvariable=self.api_key_var, width=40)
        api_key_entry.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # 設定フレーム
        settings_frame = ttk.LabelFrame(control_panel, text="詳細設定", style='Settings.TLabelframe')
        settings_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=10)
        
        # 言語選択
        lang_frame = ttk.Frame(settings_frame)
        lang_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)
        ttk.Label(lang_frame, text="言語:", style='Header.TLabel').pack(side=tk.LEFT, padx=5)
        self.language_var = tk.StringVar(value="ja")
        languages = [("日本語", "ja"), ("English", "en")]
        for label, code in languages:
            ttk.Radiobutton(lang_frame, text=label, variable=self.language_var, value=code).pack(side=tk.LEFT, padx=5)
        
        # エネルギー閾値
        energy_frame = ttk.Frame(settings_frame)
        energy_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        ttk.Label(energy_frame, text="無音判定閾値:", style='Header.TLabel').grid(row=0, column=0, sticky=tk.W, padx=5)
        self.energy_threshold_var = tk.IntVar(value=70)
        energy_scale = ttk.Scale(energy_frame, from_=0, to=1000, 
                               variable=self.energy_threshold_var,
                               orient=tk.HORIZONTAL,
                               style='Custom.Horizontal.TScale')
        energy_scale.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        energy_spinbox = ttk.Spinbox(energy_frame, from_=0, to=1000,
                                   textvariable=self.energy_threshold_var,
                                   width=5)
        energy_spinbox.grid(row=0, column=2, sticky=tk.W, padx=5)
        
        # 確信度閾値
        confidence_frame = ttk.Frame(settings_frame)
        confidence_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=5)
        ttk.Label(confidence_frame, text="確信度閾値:", style='Header.TLabel').grid(row=0, column=0, sticky=tk.W, padx=5)
        self.confidence_threshold_var = tk.DoubleVar(value=0.5)
        confidence_scale = ttk.Scale(confidence_frame, from_=0.0, to=1.0,
                                   variable=self.confidence_threshold_var,
                                   orient=tk.HORIZONTAL,
                                   style='Custom.Horizontal.TScale')
        confidence_scale.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        confidence_spinbox = ttk.Spinbox(confidence_frame, from_=0.0, to=1.0,
                                       increment=0.1,
                                       textvariable=self.confidence_threshold_var,
                                       width=5)
        confidence_spinbox.grid(row=0, column=2, sticky=tk.W, padx=5)
        
        # セグメント長
        segment_frame = ttk.Frame(settings_frame)
        segment_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=5)
        ttk.Label(segment_frame, text="セグメント長(秒):", style='Header.TLabel').grid(row=0, column=0, sticky=tk.W, padx=5)
        self.segment_length_var = tk.IntVar(value=10)
        segment_spinbox = ttk.Spinbox(segment_frame, from_=1, to=30,
                                    textvariable=self.segment_length_var,
                                    width=5)
        segment_spinbox.grid(row=0, column=1, sticky=tk.W, padx=5)
        
        # チェックボックス
        checks_frame = ttk.Frame(settings_frame)
        checks_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=5)
        self.skip_silence_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(checks_frame, text="無音区間をスキップ",
                       variable=self.skip_silence_var).grid(row=0, column=0, sticky=tk.W, padx=5)
        
        self.debug_mode_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(checks_frame, text="デバッグモード",
                       variable=self.debug_mode_var).grid(row=1, column=0, sticky=tk.W, padx=5)
        
        # コントロールボタン
        control_buttons = ttk.Frame(control_panel)
        control_buttons.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=10)
        
        self.record_button = ttk.Button(control_buttons, text="録音開始",
                                      command=self.toggle_recording,
                                      style='Record.TButton')
        self.record_button.pack(side=tk.LEFT, padx=5)
        
        self.save_button = ttk.Button(control_buttons, text="テキストを保存",
                                    command=self.save_text,
                                    style='Save.TButton')
        self.save_button.pack(side=tk.LEFT, padx=5)
        
        # 転写テキスト表示エリア（右側）
        text_frame = ttk.LabelFrame(main_frame, text="転写テキスト", style='Settings.TLabelframe')
        text_frame.grid(row=1, column=1, sticky=(tk.N, tk.S, tk.E, tk.W), padx=10)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # テキストエリアのスタイルを更新
        self.text_area = tk.Text(text_frame, 
                                wrap=tk.WORD, 
                                font=('Segoe UI', 11),
                                bg='white',
                                relief=tk.FLAT,
                                padx=10,
                                pady=10)
        self.text_area.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W), padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.text_area.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.text_area.configure(yscrollcommand=scrollbar.set)
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        
        # ステータスバーのスタイルを更新
        self.status_var = tk.StringVar(value="準備完了")
        status_bar = ttk.Label(main_frame, 
                              textvariable=self.status_var,
                              relief=tk.FLAT, 
                              padding=10,
                              background='#E0E0E0',
                              font=('Segoe UI', 10))
        status_bar.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))

    ########################################################################
    # 録音の開始/停止の切り替え
    ########################################################################
    def toggle_recording(self):
        """
        録音の開始/停止を切り替えます。
        
        録音開始時：
        - APIキーの検証
        - WhisperLiveTranscriberの初期化
        - コールバックの設定
        - 録音の開始
        
        録音停止時：
        - 録音の停止
        - 最終結果の表示
        - GUIの状態更新
        
        Raises:
            Exception: 録音の開始に失敗した場合
        """
        if not self.is_recording:
            # 録音開始
            api_key = self.api_key_var.get().strip()
            if not api_key:
                messagebox.showerror("エラー", 
                    "API Keyが設定されていません。\n"
                    "環境変数 'OPENAI_API_KEY' を設定するか、\n"
                    "入力フィールドに直接API Keyを入力してください。")
                return
                
            self.save_api_key(api_key)
            
            try:
                self.transcriber = WhisperLiveTranscriber(
                    api_key=api_key,
                    language=self.language_var.get(),
                    segment_length=self.segment_length_var.get(),
                    energy_threshold=self.energy_threshold_var.get(),
                    confidence_threshold=self.confidence_threshold_var.get(),  # 追加
                    skip_silence=self.skip_silence_var.get(),
                    debug_mode=self.debug_mode_var.get()
                )
                
                self.transcriber.transcriptions = []  # 転写結果をクリア
                self.text_area.delete(1.0, tk.END)  # テキストエリアをクリア
                
                # GUIに転写結果を表示するためのコールバックを設定
                def on_transcription(text):
                    self.text_area.insert(tk.END, f"> {text}\n")
                    self.text_area.see(tk.END)
                
                # WhisperLiveTranscriberのtranscriptionsリストに要素が追加されたときに
                # コールバックを呼び出すように_transcribe_segmentメソッドを修正
                original_transcribe_segment = self.transcriber._transcribe_segment
                def wrapped_transcribe_segment(*args, **kwargs):
                    result = original_transcribe_segment(*args, **kwargs)
                    if self.transcriber.transcriptions:
                        latest = self.transcriber.transcriptions[-1]
                        self.root.after(0, lambda: on_transcription(latest))
                    return result
                self.transcriber._transcribe_segment = wrapped_transcribe_segment
                
                self.transcriber.start_recording()
                self.is_recording = True
                self.record_button.configure(text="録音停止")
                self.status_var.set("録音中...")
                
            except Exception as e:
                messagebox.showerror("エラー", f"録音の開始に失敗しました: {e}")
                self.is_recording = False
                
        else:
            # 録音停止
            if self.transcriber:
                final_text = self.transcriber.stop_recording()
                self.text_area.insert(tk.END, "\n\n=== 最終転写結果 ===\n")
                self.text_area.insert(tk.END, final_text)
                self.text_area.see(tk.END)
            self.is_recording = False
            self.record_button.configure(text="録音開始")
            self.status_var.set("録音停止")
    
    ########################################################################
    # テキストの保存
    ########################################################################
    def save_text(self):
        """
        転写テキストをファイルに保存します。
        
        ファイル保存ダイアログを表示し、選択された場所にテキストを保存します。
        
        Raises:
            Exception: ファイルの保存に失敗した場合
        """
        try:
            from tkinter import filedialog
            file_path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
            )
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.text_area.get(1.0, tk.END))
                messagebox.showinfo("保存完了", "テキストを保存しました")
        except Exception as e:
            messagebox.showerror("エラー", f"保存中にエラーが発生しました: {e}")
    
    ########################################################################
    # GUIアプリケーションの実行
    ########################################################################
    def run(self):
        """
        GUIアプリケーションを実行します。
        
        メインループを開始し、ユーザーの入力を待ち受けます。
        """
        self.root.mainloop()
        
    ########################################################################
    # アプリケーション終了時の処理
    ########################################################################
    def on_closing(self):
        """
        アプリケーション終了時の処理を行います。
        
        - 録音中の場合は録音を停止
        - メインウィンドウを破棄
        """
        if self.is_recording:
            self.toggle_recording()
        self.root.destroy()

########################################################################
# メイン関数
########################################################################
def main():
    """
    GUIアプリケーションのエントリーポイント
    
    アプリケーションのインスタンスを作成し、
    ウィンドウクローズ時のハンドラを設定して実行します。
    """
    app = WhisperLiveGUI()
    app.root.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.run()

if __name__ == "__main__":
    main()
