import sys
import os
import json
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QTextEdit, QLineEdit, QPushButton, QComboBox, QTabWidget, 
                             QFileDialog, QMessageBox, QGroupBox, QCheckBox, QProgressBar)
from PyQt5.QtCore import QProcess, Qt

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
        self.process = None
        self.speaker_keys = []
        self.load_speakers()

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

        out_path = self.output_path_input.text().strip()
        if not out_path:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn nơi lưu file đầu ra.")
            return

        inference_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "inference.py")
        if not os.path.exists(inference_script):
            QMessageBox.critical(self, "Không tìm thấy", f"Không tìm thấy file: {inference_script}")
            return

        # Prepare arguments: Tự động dùng card đồ họa (MPS) trên Mac chip M-series để tăng tốc
        import platform
        device = "mps" if platform.system() == "Darwin" and platform.machine() == "arm64" else "cpu"
        
        if getattr(sys, 'frozen', False):
            # PyInstaller packaged mode
            args = ["inference_worker", "--text", text, "--output", out_path, "--device", device, "--language", "vietnamese"]
        else:
            # Dev mode
            args = ["-u", inference_script, "--text", text, "--output", out_path, "--device", device, "--language", "vietnamese"]

        # Check which mode is active
        if self.tab_widget.currentIndex() == 0:  # Built-in
            if not self.speaker_keys:
                QMessageBox.warning(self, "Lỗi", "Danh sách giọng nói trống. Vui lòng kiểm tra lại 'data/ref_info.json'.")
                return
            current_speaker_key = self.speaker_keys[self.speaker_combo.currentIndex()]
            args.extend(["--speaker", current_speaker_key])
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

            args.extend(["--ref_audio", ref_audio, "--ref_text", ref_text])

        # Checkbox = Layer 2: pitch shift post-processing.
        # Layer 1 (text style + tight config) is auto-applied by inference.py
        # when it detects a theanh speaker — no flag needed from GUI.
        if self.chk_theanh28.isChecked():
            args.append("--theanh28")
            pitch_value = self.pitch_slider.value() / 10.0
            args.extend(["--pitch_shift", str(pitch_value)])

        # Prepare process
        if self.process is not None and self.process.state() == QProcess.Running:
            QMessageBox.warning(self, "Cảnh báo", "Đang có một tiến trình render. Vui lòng đợi.")
            return

        self.btn_generate.setEnabled(False)
        self.btn_generate.setText("ĐANG XỬ LÝ (XEM LOG)...")
        self.progress_bar.setVisible(True)
        self.log_output.clear()
        
        # Display the command being run for debug
        # Format arguments for logging safely without backslash in f-string expression
        formatted_args = []
        for a in args:
            if ' ' in a:
                # Add quotes around paths with spaces
                formatted_args.append('"' + a + '"')
            else:
                formatted_args.append(a)
        command_str = f"Chạy lệnh: {sys.executable} {' '.join(formatted_args)}"
        self.print_log(command_str)
        self.print_log("-" * 40)

        self.process = QProcess()
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.finished.connect(self.process_finished)
        
        # Run inference using the same python executable running the GUI
        self.process.start(sys.executable, args)

    def handle_stdout(self):
        data = self.process.readAllStandardOutput()
        text = bytes(data).decode("utf8", errors="replace").strip()
        if text:
            self.print_log(text)

    def process_finished(self, exit_code, exit_status):
        self.btn_generate.setEnabled(True)
        self.btn_generate.setText("▶ BẮT ĐẦU TẠO GIỌNG NÓI")
        self.progress_bar.setVisible(False)
        self.print_log("-" * 40)
        
        if exit_status == QProcess.CrashExit:
            self.print_log("Tiến trình bị đóng băng (crash).")
            QMessageBox.critical(self, "Thất bại", "Tiến trình inference bị tắt đột ngột!")
        elif exit_code != 0:
            self.print_log(f"Render lỗi (Mã thoát: {exit_code}).")
            QMessageBox.critical(self, "Lỗi Render", "Đã xảy ra lỗi trong quá trình tạo giọng. Hãy kiểm tra log.")
        else:
            self.print_log("HOÀN TẤT THÀNH CÔNG!")
            QMessageBox.information(self, "Hoàn tất", f"Đã kết xuất Audio thành công tại:\n{self.output_path_input.text()}")


if __name__ == "__main__":
    import sys
    
    # PyInstaller multiprocessing / subprocess support
    if getattr(sys, 'frozen', False) and len(sys.argv) > 1 and sys.argv[1] == "inference_worker":
        # We are running as an inference subprocess
        sys.argv.pop(1)
        import inference
        inference.main()
        sys.exit(0)

    app = QApplication(sys.argv)
    
    # Improve look on macOS/Windows
    app.setStyle("Fusion")
    
    # ── License Check ───────────────────────────────────────────
    # Xác thực license key trước khi mở giao diện chính.
    # Nếu chưa có key hoặc key không hợp lệ → hiện dialog nhập key.
    # Nếu người dùng chọn "Thoát" → đóng app.
    # ────────────────────────────────────────────────────────────
    from license.login_dialog import check_license_or_exit
    
    if not check_license_or_exit(app):
        sys.exit(0)
    
    window = GwenTTSGui()
    window.show()
    sys.exit(app.exec_())
