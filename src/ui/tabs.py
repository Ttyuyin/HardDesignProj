"""
Tab classes — EncodingViewerTab, EncodingConverterTab.
"""

import logging
import os
from pathlib import Path
import sys
import tkinter as tk
from tkinter import filedialog, font, messagebox, TclError, ttk

from character_token import CharacterToken
from encoding_viewer import EncodingViewer
from services.converter_service import (
    convert_file,
    compatibility_scan,
    error_strategies,
    get_strategy as converter_get_strategy,
    supported_encodings,
)
from services.detector_service import (
    charset_detect,
    detect_bytes,
    diagnose_from_raw,
    file_to_tokens,
)
from ui.tables import ColoredTable, ConversionResultTable
from ui.widgets import create_button, create_horizontal_separator, create_vertical_separator, ColorLegend


logger = logging.getLogger(__name__)
CHARS_DIR = Path("D:/code/HardDesignProj/chars")
CONVERT_DIR = Path(__file__).parent.parent / "output" / "converted"
DEFAULT_STATUS = f"就绪   |   {CHARS_DIR}"


# ---------------------------------------------------------------------------
# Shared detection pipeline
# ---------------------------------------------------------------------------
def _detect_file_info(file_path):
    """Read file once, return DetectionResult + csn_part."""
    raw_data = Path(file_path).read_bytes()
    raw_data, result, csn_part = _detect_from_raw(raw_data, file_path)
    return raw_data, result, csn_part


def _detect_from_raw(raw_data, file_path):
    """Detection from already-loaded bytes — avoids redundant reads."""
    result = diagnose_from_raw(raw_data, file_path)
    csn_r = charset_detect(raw_data)
    csn_part = f"charset-normalizer: {csn_r['encoding'] or 'N/A'}"
    if csn_r['confidence'] > 0:
        csn_part += f" ({csn_r['confidence']:.0%})"
    return raw_data, result, csn_part


# ---------------------------------------------------------------------------
# EncodingConverterTab
# ---------------------------------------------------------------------------
class EncodingConverterTab(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.selected_file = None
        self.conv_tokens = []
        self._last_dir = ""
        self._setup_ui()

    def _setup_ui(self):
        # -- File Selection --
        frm_file = ttk.LabelFrame(self, text="文件选择", padding=(8, 6))
        frm_file.pack(fill="x", padx=8, pady=(8, 3))

        row_f = tk.Frame(frm_file)
        row_f.pack(fill="x")
        tk.Button(row_f, text="选择文件", command=self._sel_file,
                  font=("Microsoft YaHei", 9), bg="#4A90D9", fg="white",
                  padx=8, relief="flat", cursor="hand2").pack(side="left", padx=3)
        self.file_lbl = tk.Label(row_f, text="未选择文件", font=("Microsoft YaHei", 9), fg="#888")
        self.file_lbl.pack(side="left", padx=10)

        # -- Conversion Settings --
        frm_enc = ttk.LabelFrame(self, text="转换设置", padding=(8, 6))
        frm_enc.pack(fill="x", padx=8, pady=3)
        row_e = tk.Frame(frm_enc)
        row_e.pack(fill="x")

        enc_names = list(supported_encodings.keys())
        tk.Label(row_e, text="源编码：", font=("Microsoft YaHei", 9)).pack(side="left", padx=3)
        self.src_cb = ttk.Combobox(row_e, values=enc_names, state="readonly", width=18)
        self.src_cb.pack(side="left", padx=3)
        self.src_cb.current(0)

        tk.Label(row_e, text="→", font=("Microsoft YaHei", 14)).pack(side="left", padx=8)

        tk.Label(row_e, text="目标编码：", font=("Microsoft YaHei", 9)).pack(side="left", padx=3)
        self.tgt_cb = ttk.Combobox(row_e, values=enc_names, state="readonly", width=18)
        self.tgt_cb.pack(side="left", padx=3)
        self.tgt_cb.current(4 if len(enc_names) > 4 else 0)

        tk.Label(row_e, text="错误处理：", font=("Microsoft YaHei", 9)).pack(side="left", padx=(12, 3))
        err_names = list(error_strategies.keys())
        self.err_cb = ttk.Combobox(row_e, values=err_names, state="readonly", width=18)
        self.err_cb.pack(side="left", padx=3)
        self.err_cb.current(0)

        # -- Action buttons --
        frm_btn = tk.Frame(self)
        frm_btn.pack(fill="x", padx=8, pady=4)
        tk.Button(frm_btn, text="执行转换", command=self._do_convert,
                  font=("Microsoft YaHei", 10), bg="#5BC0DE", fg="white").pack(side="left", padx=3)
        tk.Button(frm_btn, text="打开输出目录", command=self._open_output,
                  font=("Microsoft YaHei", 9)).pack(side="left", padx=3)
        tk.Button(frm_btn, text="清空结果", command=self._clear_results,
                  font=("Microsoft YaHei", 9)).pack(side="left", padx=3)

        self.file_info_lbl = tk.Label(self, text="", anchor="w", font=("Microsoft YaHei", 9),
                                       fg="#555", bg="#F2F2F2", relief="sunken")
        self.file_info_lbl.pack(fill="x", padx=8)

        # -- Conversion Results --
        frm_result = ttk.LabelFrame(self, text="转换结果", padding=8)
        frm_result.pack(fill="both", expand=True, padx=8, pady=(3, 2))
        frm_result.grid_rowconfigure(1, weight=1)
        frm_result.grid_columnconfigure(0, weight=1)
        self.result_table = ConversionResultTable(frm_result)
        self.result_table.grid(row=1, column=0, sticky="nsew")

    def _set_file_status(self, parts):
        self.file_info_lbl.configure(text="  |  ".join(parts))

    def _sel_file(self, file_path=None):
        if file_path is None:
            p = filedialog.askopenfilename(initialdir=self._last_dir or None,
                                           filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")])
            if not p:
                return
        else:
            p = file_path

        self.selected_file = Path(p)
        self._last_dir = str(self.selected_file.parent)
        self.file_lbl.configure(text=str(self.selected_file), fg="#222")

        try:
            _, result, csn_part = _detect_file_info(p)

            enc_name_lower = result.encoding.lower()
            for i, k in enumerate(supported_encodings):
                if k.lower() == enc_name_lower:
                    self.src_cb.current(i)
                    break

            status_parts = [
                f"文件：{Path(p).name}",
                f"检测结果：{result.encoding}",
                csn_part,
            ]
            if result.is_pure_ascii:
                status_parts[1] += "（编码不明确）"
            self._set_file_status(status_parts)
            self.result_table.clear()
        except Exception as e:
            logger.warning("Failed to select file %s: %s", p, e)

    def _get_strategy(self):
        return converter_get_strategy(self.err_cb.get())

    def _do_convert(self):
        if not self.selected_file:
            messagebox.showinfo("提示", "请先选择源文件")
            return

        src_enc = self.src_cb.get()
        tgt_enc = self.tgt_cb.get()
        if src_enc == tgt_enc:
            messagebox.showinfo("提示", "源编码和目标编码相同")
            return

        strategy = self._get_strategy()

        is_big5 = tgt_enc.upper() in ("BIG5", "BIG5-HKSCS")
        if is_big5:
            if not messagebox.askyesno(
                "Big5 转换提示",
                "转换为 Big5 编码时，简体中文会自动转换为繁体中文。\n\n是否继续？"
            ):
                return

        try:
            # 1. 解码文件获取 tokens
            tokens = file_to_tokens(self.selected_file)

            # 2. 兼容性扫描（转换前预览）
            report = compatibility_scan(tokens, tgt_enc, s2t_convert=is_big5)
            if report.rate < 100:

                msg = (
                    f"兼容性：{report.rate:.1f}% "
                    f"（{report.compatible}/{report.total}）\n\n"
                    f"其中 {report.problem_count} 个字符无法编码为 {tgt_enc}：\n"
                )
                for p in report.problems[:5]:
                    msg += f"  {p['char']} ({p['unicode']})\n"
                if report.problem_count > 5:
                    msg += f"  ……以及其余 {report.problem_count - 5} 个\n"

                if strategy == "strict":
                    msg += "\n严格模式：存在无法编码的字符，转换已中止。"
                    messagebox.showerror("严格模式已中止", msg)
                    return
                msg += "\n继续执行替换（无法编码的字符将变为'?'）？"
                if not messagebox.askyesno("兼容性警告", msg):
                    return
            # 3. 执行转换
            result = convert_file(
                self.selected_file, tokens, src_enc, tgt_enc,
                CONVERT_DIR, strategy, s2t_convert=is_big5,
            )
            out_path = result.path
            self.conv_tokens = result.tokens
            total = result.total_chars
            verified = result.verified
            reversible = result.reversible

            problem_count = report.problem_count
            parts = [
                f"文件：{self.selected_file.name}",
                f"源编码：{src_enc}",
                f"目标编码：{tgt_enc}",
                f"兼容性：{report.rate:.1f}%（{report.compatible}/{total}）",
                f"{problem_count} 个被替换" if problem_count else "全部成功",
            ]
            if verified:
                parts.append(f"验证：{'可逆' if reversible else '不可逆'}")
            self._set_file_status(parts)
            self.result_table.display_results(self.conv_tokens)

            log_parts = [f"[Success] {self.selected_file.name} -> {out_path.name} ({src_enc} -> {tgt_enc})"]
            if verified:
                log_parts.append(f"Verification: {'reversible' if reversible else 'not reversible'}")
            if problem_count:
                log_parts.append(f"Compatibility: {report.rate:.1f}% ({report.compatible}/{total})")
                for p in report.problems[:5]:
                    log_parts.append(f"  {p['char']}({p['unicode']})")
                if problem_count > 5:
                    log_parts.append(f"  ... total {problem_count}")
            if not result.all_match:
                log_parts.extend(result.mismatch_log)

            if not problem_count:
                messagebox.showinfo("成功", f"转换完成：\n{out_path}")
            else:
                mode_label = "替换" if strategy == "replace" else "严格"
                messagebox.showinfo(
                    f"转换完成（{mode_label}）",
                    f"输出文件：{out_path.name}\n"
                    f"兼容性：{report.rate:.1f}%"
                    f"（{report.compatible}/{total}）\n"
                    f"{problem_count} 个字符被替换为 '?'",
                )
        except Exception as e:

            messagebox.showerror("错误", str(e))

    def _clear_results(self):
        self.conv_tokens = []
        self.result_table.clear()
        self.file_info_lbl.configure(text="")


    def _open_output(self):
        CONVERT_DIR.mkdir(parents=True, exist_ok=True)
        os.startfile(str(CONVERT_DIR))


# ---------------------------------------------------------------------------
# EncodingViewerTab
# ---------------------------------------------------------------------------
class EncodingViewerTab(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.current_file = None
        self.detected_encoding = ""
        self.current_tokens = []
        self.analysis_results = []
        self._last_dir = str(CHARS_DIR)
        self._setup_ui()

    def _setup_ui(self):
        # ── 1. Top Toolbar ──
        top = tk.Frame(self, bg="#EBEBEB")
        tb = tk.Frame(top, bg="#EBEBEB")
        tb.pack(fill="x", padx=6, pady=3)

        create_button(tb, "打开文件", self._open_file, "#4A90D9").pack(side="left", padx=3)
        create_button(tb, "粘贴文本", self._paste_text, "#5CB85C").pack(side="left", padx=3)
        create_button(tb, "清空", self._clear_all, "#F0AD4E").pack(side="left", padx=3)
        create_button(tb, "打开输出目录", self._open_output, "#6C757D").pack(side="left", padx=3)

        self.file_lbl = tk.Label(tb, text="未选择文件", font=("Microsoft YaHei", 9), fg="#888")
        self.file_lbl.pack(side="left", padx=10)

        create_vertical_separator(tb).pack(side="left", fill="y", padx=8)

        self.enc_lbl = tk.Label(tb, text="", font=("Microsoft YaHei", 10),
                                 fg="#2E7D32", bg="#EBEBEB")
        self.enc_lbl.pack(side="right", padx=10)

        # ── 2. Main Content Area ──
        content = tk.Frame(self)
        content.grid_rowconfigure(0, weight=1)
        content.grid_columnconfigure(0, weight=0)  # 左栏固定宽度，不参与拉伸
        content.grid_columnconfigure(1, weight=1)  # 右栏占满剩余空间

        # --- Left: Original Text ---
        left_frm = tk.Frame(content, bg="#F2F2F2", bd=1, relief="solid")
        left_frm.grid(row=0, column=0, sticky="nsew", padx=(0, 3))
        left_frm.grid_rowconfigure(1, weight=1)
        left_frm.grid_columnconfigure(0, weight=1)

        tk.Label(left_frm, text="原始文本", font=("Microsoft YaHei", 9, "bold"),
                 bg="#F2F2F2").grid(row=0, column=0, sticky="w", padx=6, pady=(4, 2))

        txt_in_frame = tk.Frame(left_frm)
        txt_in_frame.grid(row=1, column=0, sticky="nsew", padx=4, pady=(2, 4))
        txt_in_frame.grid_rowconfigure(0, weight=1)
        txt_in_frame.grid_columnconfigure(0, weight=1)

        self.txt_in = tk.Text(txt_in_frame, wrap="word", font=("Consolas", 11),
                            width=35,  # 控制文本框宽度（字符数）
                            bg="white", fg="#111111", relief="flat", borderwidth=0,
                            highlightthickness=0, padx=4, pady=2, insertbackground="#111111")
        txt_in_vbar = tk.Scrollbar(txt_in_frame, orient="vertical", command=self.txt_in.yview)
        self.txt_in.configure(yscrollcommand=txt_in_vbar.set)
        self.txt_in.grid(row=0, column=0, sticky="nsew")
        txt_in_vbar.grid(row=0, column=1, sticky="ns")

        # --- Right: Encoding Analysis ---
        right_frm = tk.Frame(content, bg="#F2F2F2", bd=1, relief="solid")
        right_frm.grid(row=0, column=1, sticky="nsew", padx=(3, 0))
        right_frm.grid_rowconfigure(1, weight=1)
        right_frm.grid_columnconfigure(0, weight=1)

        tk.Label(right_frm, text="编码分析", font=("Microsoft YaHei", 9, "bold"),
                 bg="#F2F2F2").grid(row=0, column=0, sticky="w", padx=6, pady=(4, 2))
        self.table = ColoredTable(right_frm)
        self.table.grid(row=1, column=0, sticky="nsew", padx=4, pady=(2, 4))

        # ── 3. Bottom Action Bar ──
        bot = tk.Frame(self, bg="#EBEBEB")
        bb = tk.Frame(bot, bg="#EBEBEB")
        bb.pack(fill="x", padx=6, pady=3)

        create_button(bb, "分析编码", self._analyze, "#5BC0DE").pack(side="left", padx=3)
        create_button(bb, "退出", self._quit, "#D9534F").pack(side="right", padx=(3, 4))

        legend_frm = tk.Frame(bb)
        legend_frm.pack(side="right", padx=(0, 16))
        ColorLegend(legend_frm).pack()

        # ── 4. Status Bar ──
        self.status = tk.Label(self, text=DEFAULT_STATUS, anchor="w",
                                font=("Microsoft YaHei", 9),
                                bg="#E0E0E0", fg="#666")

        # ── 5. Assemble ──
        self.status.pack(fill="x", side="bottom", padx=0, pady=0)
        create_horizontal_separator(self).pack(fill="x", side="bottom")

        bot.pack(fill="x", side="bottom", padx=0, pady=0)
        create_horizontal_separator(self).pack(fill="x", side="bottom")

        top.pack(fill="x", side="top", padx=0, pady=0)
        create_horizontal_separator(self).pack(fill="x", side="top")

        content.pack(fill="both", expand=True, side="top", padx=4, pady=4)

    def _set_status(self, msg):
        self.status.configure(text=msg)

    def _open_file(self, file_path=None):
        if file_path is None:
            p = filedialog.askopenfilename(title="选择文本文件", initialdir=str(CHARS_DIR),
                                           filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")])
            if not p:
                return
        else:
            p = file_path
        try:
            raw_data = Path(p).read_bytes()
            tokens = file_to_tokens(p, raw_data=raw_data)
            enc_name = tokens[0].source_encoding if tokens else ""
            self.detected_encoding = enc_name
            self.current_tokens = tokens
            self.current_file = p

            _, result, csn_part = _detect_from_raw(raw_data, p)

            self.enc_lbl.configure(text=f"检测结果：{enc_name}  |  {csn_part}")

            pure = " (编码不明确)" if result.is_pure_ascii else ""
            diag = " | ".join(f"{n}:{r[:1]}" for n, _, r in result.trials)
            self._set_status(f"已打开：{p} | 检测结果：{enc_name}{pure} | {csn_part} | {diag}")
            self.file_lbl.configure(text=p, fg="#222")
            self._analyze_tokens(tokens)
        except Exception as e:
            messagebox.showerror("错误", f"打开文件失败：\n{e}")
            logger.exception("Failed to open file")

    def _paste_text(self):
        try:
            text = self.clipboard_get()
            self.txt_in.delete("1.0", "end")
            self.txt_in.insert("1.0", text)
            self.current_file = None
            self.detected_encoding = ""
            self.file_lbl.configure(text="未选择文件", fg="#888")
            self.enc_lbl.configure(text="")
            self._set_status("已粘贴文本")
        except TclError:
            messagebox.showinfo("提示", "剪贴板为空")

    def _clear_all(self):
        self.txt_in.delete("1.0", "end")
        self.table.clear()
        self.analysis_results = []
        self.current_tokens = []
        self.current_file = None
        self.detected_encoding = ""
        self.file_lbl.configure(text="未选择文件", fg="#888")
        self.enc_lbl.configure(text="")
        self._set_status("已清空")

    def _analyze(self):
        text = self.txt_in.get("1.0", "end").rstrip("\n")
        if not text:
            messagebox.showinfo("提示", "请先输入或打开文本")
            return

        tokens = []
        raw_bytes = text.encode("utf-8")
        for ch in text:
            try:
                src_bytes = ch.encode("utf-8")
            except UnicodeEncodeError:
                src_bytes = b""
            tokens.append(CharacterToken(char=ch, source_encoding="UTF-8", source_bytes=src_bytes))

        self.current_tokens = tokens

        csn_part = ""
        try:
            dr = detect_bytes(raw_bytes)
            self.detected_encoding = dr.encoding
            csn_r = charset_detect(raw_bytes)
            if csn_r["encoding"]:
                csn_part = f"charset-normalizer: {csn_r['encoding']}"
                if csn_r["confidence"] > 0:
                    csn_part += f" ({csn_r['confidence']:.0%})"
        except Exception:
            pass

        if self.detected_encoding:
            self.enc_lbl.configure(text=f"检测结果：{self.detected_encoding}  |  {csn_part}")
        else:
            self.enc_lbl.configure(text="")
        self._analyze_tokens(tokens)

    def _analyze_tokens(self, tokens):
        self.analysis_results = EncodingViewer.analyze_tokens(tokens, fallback_encoding="")
        self.table.display_data(self.analysis_results)
        stats = EncodingViewer.get_statistics(self.analysis_results)
        parts = [f"共 {stats['total_chars']} 个字符"]
        for enc, st in stats["encoding_stats"].items():
            parts.append(f"{enc}: {st['rate']:.0f}%")
        if self.detected_encoding:
            parts.insert(0, f"文件编码：{self.detected_encoding}")
        self._set_status(" | ".join(parts))

    def _open_output(self):
        CONVERT_DIR.mkdir(parents=True, exist_ok=True)
        p = filedialog.askopenfilename(title="选择要检测的文件", initialdir=str(CONVERT_DIR),
                                       filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")])
        if p:
            self._open_file(file_path=p)

    @staticmethod
    def _quit():
        sys.exit(0)
