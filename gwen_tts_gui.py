import sys
import os
import json
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QTextEdit, QLineEdit, QPushButton, QComboBox, QTabWidget, 
                             QFileDialog, QMessageBox, QGroupBox, QCheckBox, QProgressBar)
from PyQt5.QtCore import QProcess, Qt, QThread, pyqtSignal

class ModelLoaderThread(QThread):
    finished = pyqtSignal(object)
    log = pyqtSignal(str)

    def run(self):
        self.log.emit("Đang nạp mô hình AI vào bộ nhớ... (Sẽ mất khoảng 30-60 giây ở lần mở đầu tiên)")
        import platform
        import inference
        device = "mps" if platform.system() == "Darwin" and platform.machine() == "arm64" else "cpu"
        try:
            model = inference.load_model("g-group-ai-lab/gwen-tts-0.6B", device=device)
            self.log.emit("✅ Nạp mô hình thành công! Đã sẵn sàng tạo giọng nói ngay lập tức.")
            self.finished.emit(model)
        except Exception as e:
            self.log.emit(f"❌ Lỗi nạp mô hình: {str(e)}")
            self.finished.emit(None)

class StdoutRedirector:
    def __init__(self, log_signal):
        self.log_signal = log_signal

    def write(self, text):
        text = text.strip('\r\n')
        if text:
            self.log_signal.emit(text)

    def flush(self):
        pass

class InferenceThread(QThread):
    finished = pyqtSignal(bool, str) # success, output_path or error_msg
    log = pyqtSignal(str)
    
    def __init__(self, model, args_dict):
        super().__init__()
        self.model = model
        self.args = args_dict
    
    def run(self):
        import sys
        old_stdout = sys.stdout
        sys.stdout = StdoutRedirector(self.log)
        
        try:
            import inference
            from pathlib import Path
            import soundfile as sf
            
            args = self.args
            
            theanh28_style = args.get("theanh28", False)
            chunks = inference.split_text_into_chunks(args["text"], max_chars=400)
            print(f"\n[Chunking] Văn bản dài {len(args['text'])} ký tự được chia thành {len(chunks)} phần nhỏ.")
            
            all_wavs = []
            final_sr = 24000
            
            base_dir = Path(inference.__file__).parent
            ref_info_path = base_dir / "data" / "ref_info.json"
            
            if args.get("speaker"):
                ref_info = inference.load_speaker_info(ref_info_path)
                print(f"Generating with speaker: {ref_info[args['speaker']]['name']}...")
                for i, chunk in enumerate(chunks):
                    print(f"\n--- Đang xử lý phần {i+1}/{len(chunks)} ({len(chunk)} ký tự) ---")
                    wav, sr = inference.generate_with_speaker(
                        self.model, chunk, args["language"], args["speaker"], ref_info, base_dir,
                        theanh28_style=theanh28_style,
                        pitch_shift=args.get("pitch_shift")
                    )
                    all_wavs.append(wav)
                    final_sr = sr
            else:
                print(f"Generating with custom reference audio: {args['ref_audio']}...")
                for i, chunk in enumerate(chunks):
                    print(f"\n--- Đang xử lý phần {i+1}/{len(chunks)} ({len(chunk)} ký tự) ---")
                    wav, sr = inference.generate_voice_clone(
                        self.model, chunk, args["language"], args["ref_audio"], args["ref_text"],
                        theanh28_style=theanh28_style,
                        pitch_shift=args.get("pitch_shift")
                    )
                    all_wavs.append(wav)
                    final_sr = sr

            if len(all_wavs) > 1:
                print("\n[Nối file] Đang ghép nối các phần lại thành 1 file âm thanh hoàn chỉnh...")
                final_wav = inference._concat_audio_chunks(all_wavs, final_sr, gap_seconds=0.25)
            else:
                final_wav = all_wavs[0]

            sf.write(args["output"], final_wav, final_sr)
            print(f"Saved final audio to {args['output']} (sample rate: {final_sr}Hz)")
            self.finished.emit(True, args["output"])
            
        except Exception as e:
            import traceback
            err = traceback.format_exc()
            print(f"❌ Lỗi trong quá trình xử lý: {str(e)}\n{err}")
            self.finished.emit(False, str(e))
        finally:
            sys.stdout = old_stdout
class GwenTTSGui(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gwen-TTS: Vietnamese Voice Cloning")
        self.resize(800, 600)
        self.setStyleSheet("""
            QWidget {
                font-family: Arial, sans-serif;
                font-size: 14px;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ccc;
                border-radius: 5px;
                margin-top: 1ex;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                padding: 0 3px;
            }
            QPushButton {
                background-color: #2c3e50;
                color: white;
                padding: 8px 15px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #34495e;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
            QTextEdit, QLineEdit, QComboBox {
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 5px;
            }
            QTextEdit[readOnly="true"] {
                background-color: #f8f9fa;
                font-family: Consolas, monospace;
                color: #27ae60;
                font-size: 13px;
            }
        """)

        # Main Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # -----------------------------------------------------------------
        # Input Text Section
        # -----------------------------------------------------------------
        text_group = QGroupBox("Bạn muốn tôi nói gì?")
        text_layout = QVBoxLayout()
        text_label = QLabel("Nhập nội dung bạn muốn AI đọc tại đây:")
        text_label.setStyleSheet("font-size: 14px; padding: 2px 0;")
        text_layout.addWidget(text_label)
        self.input_text = QTextEdit()
        self.input_text.setMinimumHeight(120)
        self.input_text.setPlaceholderText("Nhập nội dung tại đây...\n\nSố, ngày tháng, tiền tệ, đơn vị (km/h, °C, %) sẽ được tự động chuyển thành chữ Việt.")
        text_layout.addWidget(self.input_text)
        text_group.setLayout(text_layout)
        main_layout.addWidget(text_group)

        # -----------------------------------------------------------------
        # Voice Settings Section (Tabs)
        # -----------------------------------------------------------------
        voice_group = QGroupBox("2. Tùy chọn giọng đọc (Voice Selection)")
        voice_layout = QVBoxLayout()
        self.tab_widget = QTabWidget()
        
        # Tab 1: Built-in Speaker
        self.tab_builtin = QWidget()
        builtin_layout = QVBoxLayout(self.tab_builtin)
        builtin_layout.addWidget(QLabel("Chọn một giọng đọc gợi ý có sẵn:"))
        
        self.speaker_combo = QComboBox()
        builtin_layout.addWidget(self.speaker_combo)
        builtin_layout.addStretch()
        
        self.tab_widget.addTab(self.tab_builtin, "Giọng đọc có sẵn")
        
        # Tab 2: Custom Voice Clone
        self.tab_custom = QWidget()
        custom_layout = QVBoxLayout(self.tab_custom)
        
        audio_layout = QHBoxLayout()
        self.ref_audio_input = QLineEdit()
        self.ref_audio_input.setPlaceholderText("Chưa chọn file audio (.wav)")
        self.ref_audio_input.setReadOnly(True)
        btn_browse_audio = QPushButton("Duyệt...")
        btn_browse_audio.clicked.connect(self.browse_ref_audio)
        audio_layout.addWidget(QLabel("File audio mẫu:"))
        audio_layout.addWidget(self.ref_audio_input)
        audio_layout.addWidget(btn_browse_audio)
        custom_layout.addLayout(audio_layout)
        
        custom_layout.addWidget(QLabel("Văn bản trong file audio mẫu (Transcript):"))
        self.ref_text_input = QTextEdit()
        self.ref_text_input.setMaximumHeight(80)
        self.ref_text_input.setPlaceholderText(
            "⚠️ QUAN TRỌNG: Ghi lại CHÍNH XÁC những gì người nói trong file audio mẫu.\n"
            "→ Sai transcript = mô hình bị lạc → ra giọng Trung Quốc!\n\n"
            "✅ Đúng: 'xin chào tôi là minh hôm nay chúng ta sẽ'\n"
            "❌ Sai: 'Xin chào! Tôi là Minh. Hôm nay...' (dấu câu, hoa thường không khớp)\n\n"
            "Nên viết thường, ít dấu câu, khớp y hệt nhịp đọc trong audio."
        )
        custom_layout.addWidget(self.ref_text_input)
        
        self.tab_widget.addTab(self.tab_custom, "Sao chép giọng (Custom Clone)")
        
        voice_layout.addWidget(self.tab_widget)
        voice_group.setLayout(voice_layout)
        main_layout.addWidget(voice_group)

        # -----------------------------------------------------------------
        # Output Config Section
        # -----------------------------------------------------------------
        output_layout = QHBoxLayout()
        self.output_path_input = QLineEdit()
        self.output_path_input.setText(os.path.join(os.getcwd(), "output.wav"))
        btn_browse_output = QPushButton("Đổi vị trí...")
        btn_browse_output.clicked.connect(self.browse_output_path)
        
        output_layout.addWidget(QLabel("Lưu tệp tại:"))
        output_layout.addWidget(self.output_path_input)
        output_layout.addWidget(btn_browse_output)
        main_layout.addLayout(output_layout)

        # -----------------------------------------------------------------
        # Options Section
        # -----------------------------------------------------------------
        opt_group = QGroupBox("3. Tùy chọn phong cách")
        opt_layout = QVBoxLayout()
        self.chk_theanh28 = QCheckBox("Nâng thêm cao độ giọng (Pitch Shift — tuỳ chọn)")
        self.chk_theanh28.setToolTip("Nâng cao độ giọng bằng post-processing.\nGiọng Theanh28 đã tự động phiêu/nhấn nhá nhờ text style.\nChỉ tích khi muốn nâng tone CAO HƠN NỮA.")
        self.chk_theanh28.stateChanged.connect(self._toggle_pitch_shift)
        opt_layout.addWidget(self.chk_theanh28)
        
        # Pitch shift controls (visible when Theanh28 is checked)
        self.pitch_shift_widget = QWidget()
        pitch_layout = QHBoxLayout(self.pitch_shift_widget)
        pitch_layout.setContentsMargins(20, 0, 0, 0)
        pitch_layout.addWidget(QLabel("Nâng cao giọng (Pitch Shift):"))
        
        from PyQt5.QtWidgets import QSlider, QSpinBox
        self.pitch_slider = QSlider(Qt.Horizontal)
        self.pitch_slider.setMinimum(0)
        self.pitch_slider.setMaximum(60)  # 0.0 to 6.0 semitones (x10)
        self.pitch_slider.setValue(20)    # Default: +2.0 semitones
        self.pitch_slider.setTickInterval(10)
        self.pitch_slider.setTickPosition(QSlider.TicksBelow)
        self.pitch_slider.valueChanged.connect(self._update_pitch_label)
        pitch_layout.addWidget(self.pitch_slider)
        
        self.pitch_label = QLabel("+2.0 semitones")
        self.pitch_label.setMinimumWidth(110)
        pitch_layout.addWidget(self.pitch_label)
        
        self.pitch_shift_widget.setVisible(False)
        opt_layout.addWidget(self.pitch_shift_widget)
        
        opt_group.setLayout(opt_layout)
        main_layout.addWidget(opt_group)

        # -----------------------------------------------------------------
        # Action Button
        # -----------------------------------------------------------------
        self.btn_generate = QPushButton("▶ BẮT ĐẦU TẠO GIỌNG NÓI")
        self.btn_generate.setStyleSheet("background-color: #27ae60; font-size: 16px; padding: 12px;")
        self.btn_generate.clicked.connect(self.start_generation)
        self.btn_generate.setEnabled(False)
        self.btn_generate.setText("⏳ ĐANG NẠP MÔ HÌNH AI...")
        main_layout.addWidget(self.btn_generate)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate mode
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        # -----------------------------------------------------------------
        # Log Output Section
        # -----------------------------------------------------------------
        log_group = QGroupBox("Quá trình xử lý (Log Console)")
        log_layout = QVBoxLayout()
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        log_layout.addWidget(self.log_output)
        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group)

        # -----------------------------------------------------------------
        # Init components
        # -----------------------------------------------------------------
        self.ai_model = None
        self.process = None
        self.inference_thread = None
        self.speaker_keys = []
        self.load_speakers()

        # Bắt đầu nạp mô hình trong background
        self.loader_thread = ModelLoaderThread()
        self.loader_thread.log.connect(self.print_log)
        self.loader_thread.finished.connect(self.on_model_loaded)
        self.loader_thread.start()

    def on_model_loaded(self, model):
        if model is not None:
            self.ai_model = model
            self.btn_generate.setEnabled(True)
            self.btn_generate.setText("▶ BẮT ĐẦU TẠO GIỌNG NÓI")
        else:
            self.btn_generate.setText("❌ LỖI NẠP MÔ HÌNH")
            QMessageBox.critical(self, "Lỗi khởi tạo", "Không thể nạp mô hình AI. Vui lòng kiểm tra log.")

    def load_speakers(self):
        ref_info_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "ref_info.json")
        try:
            with open(ref_info_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                temp_speakers = []
                for key, info in data.items():
                    name = info.get("name", key)
                    temp_speakers.append((name, key))
                
                # Sort alphabetically by name
                temp_speakers.sort(key=lambda x: x[0])
                
                for name, key in temp_speakers:
                    self.speaker_combo.addItem(name)
                    self.speaker_keys.append(key)
        except Exception as e:
            self.speaker_combo.addItem(f"Lỗi tải danh sách: {str(e)}")

    def browse_ref_audio(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Chọn File Audio Mẫu", "", "Audio Files (*.wav)")
        if file_path:
            self.ref_audio_input.setText(file_path)

    def browse_output_path(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Chọn nơi lưu", "output.wav", "Audio Files (*.wav)")
        if file_path:
            self.output_path_input.setText(file_path)

    def _toggle_pitch_shift(self, state):
        """Show/hide pitch shift slider based on Theanh28 checkbox."""
        self.pitch_shift_widget.setVisible(state == Qt.Checked)

    def _update_pitch_label(self, value):
        """Update pitch shift label when slider changes."""
        semitones = value / 10.0
        self.pitch_label.setText(f"+{semitones:.1f} semitones")

    def print_log(self, text):
        self.log_output.append(text)
        # Scroll to bottom
        scrollbar = self.log_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def start_generation(self):
        text = self.input_text.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập văn bản cần chuyển (Text-to-Speech).")
            return

        if not self.ai_model:
            QMessageBox.warning(self, "Chưa sẵn sàng", "Mô hình AI chưa được nạp xong hoặc nạp lỗi. Vui lòng chờ!")
            return

        out_path = self.output_path_input.text().strip()
        if not out_path:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn nơi lưu file đầu ra.")
            return

        inference_args = {
            "text": text,
            "output": out_path,
            "language": "vietnamese",
            "theanh28": False,
            "pitch_shift": None,
            "speaker": None,
            "ref_audio": None,
            "ref_text": None
        }

        # Check which mode is active
        if self.tab_widget.currentIndex() == 0:  # Built-in
            if not self.speaker_keys:
                QMessageBox.warning(self, "Lỗi", "Danh sách giọng nói trống. Vui lòng kiểm tra lại 'data/ref_info.json'.")
                return
            current_speaker_key = self.speaker_keys[self.speaker_combo.currentIndex()]
            inference_args["speaker"] = current_speaker_key
        else:  # Custom Clone
            ref_audio = self.ref_audio_input.text().strip()
            ref_text = self.ref_text_input.toPlainText().strip()
            if not ref_audio:
                QMessageBox.warning(self, "Lỗi", "Vui lòng chọn File audio mẫu.")
                return
            if not ref_text:
                QMessageBox.warning(self, "Lỗi", "Vui lòng ghi Transcript cho audio mẫu.")
                return

            # Pre-process & Cảnh báo nếu audio mẫu quá dài
            try:
                self.print_log("Đang tối ưu hóa âm thanh mẫu (Resample 16kHz, Trim noise, Normalize)...")
                QApplication.processEvents() # Cập nhật UI
                
                import librosa
                import soundfile as sf
                
                # Load with librosa to force 16kHz mono
                y, sr = librosa.load(ref_audio, sr=16000, mono=True)
                
                # Trim silence at the beginning and end
                y_trimmed, _ = librosa.effects.trim(y, top_db=25)
                
                # Normalize audio loudness
                y_normalized = librosa.util.normalize(y_trimmed)
                
                duration = len(y_normalized) / sr
                
                if duration > 15.0:
                    reply = QMessageBox.question(
                        self, "Cảnh báo Audio Quá Dài",
                        f"Audio mẫu sau khi tối ưu vẫn dài {duration:.1f} giây. Khuyến nghị CHỈ dùng audio từ 3-10 giây để AI tập trung tốt nhất. Dùng audio quá dài sẽ khiến thời gian chạy rất lâu và AI dễ bị nhầm lẫn (treo/im lặng/giọng TQ). Bạn có chắc chắn muốn tiếp tục?",
                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                    )
                    if reply == QMessageBox.No:
                        self.print_log("Đã hủy bỏ vì audio quá dài.")
                        return
                
                # Save processed file to a temp location
                processed_ref_path = os.path.join(os.getcwd(), "temp_custom_ref.wav")
                sf.write(processed_ref_path, y_normalized, sr)
                
                self.print_log(f"Tối ưu hóa xong. Độ dài mới: {duration:.2f}s (gốc: {len(y)/16000:.2f}s).")
                ref_audio = processed_ref_path
            except Exception as e:
                self.print_log(f"Cảnh báo: Lỗi khi tối ưu hóa âm thanh (sẽ dùng file gốc): {e}")

            inference_args["ref_audio"] = ref_audio
            inference_args["ref_text"] = ref_text

        # Checkbox = Layer 2: pitch shift post-processing.
        if self.chk_theanh28.isChecked():
            inference_args["theanh28"] = True
            inference_args["pitch_shift"] = self.pitch_slider.value() / 10.0

        # Prepare process
        if self.inference_thread is not None and self.inference_thread.isRunning():
            QMessageBox.warning(self, "Cảnh báo", "Đang có một tiến trình render. Vui lòng đợi.")
            return

        self.btn_generate.setEnabled(False)
        self.btn_generate.setText("ĐANG XỬ LÝ (XEM LOG)...")
        self.progress_bar.setVisible(True)
        self.log_output.clear()
        
        self.print_log("-" * 40)
        self.print_log("Bắt đầu xử lý (Sử dụng mô hình đã nạp trong RAM)")
        self.print_log("-" * 40)

        self.inference_thread = InferenceThread(self.ai_model, inference_args)
        self.inference_thread.log.connect(self.print_log)
        self.inference_thread.finished.connect(self.process_finished)
        self.inference_thread.start()

    def process_finished(self, success, result_msg):
        self.btn_generate.setEnabled(True)
        self.btn_generate.setText("▶ BẮT ĐẦU TẠO GIỌNG NÓI")
        self.progress_bar.setVisible(False)
        self.print_log("-" * 40)
        
        if not success:
            self.print_log(f"Render lỗi.")
            QMessageBox.critical(self, "Lỗi Render", "Đã xảy ra lỗi trong quá trình tạo giọng. Hãy kiểm tra log.")
        else:
            self.print_log("HOÀN TẤT THÀNH CÔNG!")
            QMessageBox.information(self, "Hoàn tất", f"Đã kết xuất Audio thành công tại:\n{result_msg}")


if __name__ == "__main__":
    import sys
    import os
    import traceback

    # ── Global Crash Handler ────────────────────────────────────
    # Khi build --windowed (PyInstaller), mọi exception đều bị nuốt.
    # Handler này ghi lỗi ra file và hiện MessageBox cho người dùng.
    # ────────────────────────────────────────────────────────────
    def _crash_handler(exc_type, exc_value, exc_tb):
        error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
        log_path = os.path.join(os.path.expanduser("~"), "gwen_tts_crash.log")
        try:
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(f"Gwen-TTS Crash Report\n{'='*40}\n{error_msg}")
        except Exception:
            pass
        # Hiện MessageBox cho người dùng
        try:
            from PyQt5.QtWidgets import QApplication, QMessageBox
            if QApplication.instance() is None:
                _app = QApplication(sys.argv)
            QMessageBox.critical(
                None, "Gwen-TTS — Lỗi nghiêm trọng",
                f"Ứng dụng gặp lỗi:\n\n{str(exc_value)}\n\n"
                f"Chi tiết lỗi đã được lưu tại:\n{log_path}\n\n"
                f"Vui lòng gửi file này cho admin để được hỗ trợ."
            )
        except Exception:
            pass
        sys.exit(1)

    sys.excepthook = _crash_handler

    app = QApplication(sys.argv)
    
    # Improve look on macOS/Windows
    app.setStyle("Fusion")
    
    # ── License Check ───────────────────────────────────────────
    # Xác thực license key trước khi mở giao diện chính.
    # Nếu chưa có key hoặc key không hợp lệ → hiện dialog nhập key.
    # Nếu người dùng chọn "Thoát" → đóng app.
    # ────────────────────────────────────────────────────────────
    try:
        from license.login_dialog import check_license_or_exit
    except ImportError as e:
        QMessageBox.critical(
            None, "Gwen-TTS — Lỗi khởi tạo",
            f"Không thể nạp module license:\n\n{str(e)}\n\n"
            f"Vui lòng liên hệ admin."
        )
        sys.exit(1)
    
    if not check_license_or_exit(app):
        sys.exit(0)
    
    window = GwenTTSGui()
    window.show()
    sys.exit(app.exec_())

