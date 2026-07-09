"""
标签页模块 —— EncodingViewerTab（编码查看器）和 EncodingConverterTab（编码转换器）。
包含文件选择、编码检测、转换设置、结果展示等完整交互逻辑。
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
# 共享检测管线 —— 供两个标签页共用
# ---------------------------------------------------------------------------
def _detect_file_info(file_path):
    """读取文件一次，返回原始字节、检测结果对象及 charset-normalizer 辅助信息。

    返回 (raw_data, DetectionResult, csn_part)，其中 csn_part 为可读的检测标签字符串。
    """
    raw_data = Path(file_path).read_bytes()
    raw_data, result, csn_part = _detect_from_raw(raw_data, file_path)
    return raw_data, result, csn_part


def _detect_from_raw(raw_data, file_path):
    """对已载入的字节数据进行编码检测 —— 避免重复读取磁盘。

    同时调用 diagnose_from_raw（内部多引擎）和 charset-normalizer，
    将后者结果格式化为 "charset-normalizer: encoding (confidence%)" 的可读片段。
    """
    result = diagnose_from_raw(raw_data, file_path)
    csn_r = charset_detect(raw_data)
    csn_part = f"charset-normalizer: {csn_r['encoding'] or 'N/A'}"
    if csn_r['confidence'] > 0:
        csn_part += f" ({csn_r['confidence']:.0%})"
    return raw_data, result, csn_part


# ---------------------------------------------------------------------------
# EncodingConverterTab —— 编码转换器标签页
# ---------------------------------------------------------------------------
class EncodingConverterTab(tk.Frame):
    """编码转换器标签页。提供文件选择、源/目标编码选择、兼容性预览及实际转换功能。"""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.selected_file = None     # 当前选中的源文件路径（Path 对象）
        self.conv_tokens = []         # 转换后生成的 CharacterToken 列表
        self._last_dir = ""           # 上次打开文件的目录，用于对话框初始路径
        self._setup_ui()

    def _setup_ui(self):
        """构建转换器标签页的完整 UI 布局。

        自上而下分为四区：文件选择 → 转换设置（源/目标编码 + 错误策略）
        → 操作按钮 & 信息栏 → 转换结果表格。
        """
        # -- 文件选择区域 --
        frm_file = ttk.LabelFrame(self, text="文件选择", padding=(8, 6))
        frm_file.pack(fill="x", padx=8, pady=(8, 3))

        row_f = tk.Frame(frm_file)
        row_f.pack(fill="x")
        tk.Button(row_f, text="选择文件", command=self._sel_file,
                  font=("Microsoft YaHei", 9), bg="#4A90D9", fg="white",
                  padx=8, relief="flat", cursor="hand2").pack(side="left", padx=3)
        self.file_lbl = tk.Label(row_f, text="未选择文件", font=("Microsoft YaHei", 9), fg="#888")
        self.file_lbl.pack(side="left", padx=10)

        # -- 转换设置区域（源编码 → 目标编码 + 错误处理策略） --
        frm_enc = ttk.LabelFrame(self, text="转换设置", padding=(8, 6))
        frm_enc.pack(fill="x", padx=8, pady=3)
        row_e = tk.Frame(frm_enc)
        row_e.pack(fill="x")

        enc_names = list(supported_encodings.keys())
        tk.Label(row_e, text="源编码：", font=("Microsoft YaHei", 9)).pack(side="left", padx=3)
        self.src_cb = ttk.Combobox(row_e, values=enc_names, state="readonly", width=18)
        self.src_cb.pack(side="left", padx=3)
        self.src_cb.current(0)         # 默认选中第一个编码

        tk.Label(row_e, text="→", font=("Microsoft YaHei", 14)).pack(side="left", padx=8)

        tk.Label(row_e, text="目标编码：", font=("Microsoft YaHei", 9)).pack(side="left", padx=3)
        self.tgt_cb = ttk.Combobox(row_e, values=enc_names, state="readonly", width=18)
        self.tgt_cb.pack(side="left", padx=3)
        self.tgt_cb.current(4 if len(enc_names) > 4 else 0)

        tk.Label(row_e, text="错误处理：", font=("Microsoft YaHei", 9)).pack(side="left", padx=(12, 3))
        err_names = list(error_strategies.keys())
        self.err_cb = ttk.Combobox(row_e, values=err_names, state="readonly", width=18)
        self.err_cb.pack(side="left", padx=3)
        self.err_cb.current(0)         # 默认 strict 模式

        # -- 操作按钮（执行转换 / 打开输出目录 / 清空结果） --
        frm_btn = tk.Frame(self)
        frm_btn.pack(fill="x", padx=8, pady=4)
        tk.Button(frm_btn, text="执行转换", command=self._do_convert,
                  font=("Microsoft YaHei", 10), bg="#5BC0DE", fg="white").pack(side="left", padx=3)
        tk.Button(frm_btn, text="打开输出目录", command=self._open_output,
                  font=("Microsoft YaHei", 9)).pack(side="left", padx=3)
        tk.Button(frm_btn, text="清空结果", command=self._clear_results,
                  font=("Microsoft YaHei", 9)).pack(side="left", padx=3)

        # -- 文件信息状态栏（凹陷样式，显示编码检测信息） --
        self.file_info_lbl = tk.Label(self, text="", anchor="w", font=("Microsoft YaHei", 9),
                                       fg="#555", bg="#F2F2F2", relief="sunken")
        self.file_info_lbl.pack(fill="x", padx=8)

        # -- 转换结果表格 --
        frm_result = ttk.LabelFrame(self, text="转换结果", padding=8)
        frm_result.pack(fill="both", expand=True, padx=8, pady=(3, 2))
        frm_result.grid_rowconfigure(1, weight=1)
        frm_result.grid_columnconfigure(0, weight=1)
        self.result_table = ConversionResultTable(frm_result)
        self.result_table.grid(row=1, column=0, sticky="nsew")

    def _set_file_status(self, parts):
        """用  |  拼接信息片段，更新文件信息状态栏。"""
        self.file_info_lbl.configure(text="  |  ".join(parts))

    def _sel_file(self, file_path=None):
        """弹出文件选择对话框（或接收外部传入路径），加载文件并自动检测编码。

        检测成功后自动将源编码下拉框切换为匹配项，更新状态栏显示检测结果。
        """
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

            # 自动匹配检测到的编码，设置源编码下拉框
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
                status_parts[1] += "（编码不明确）"    # 纯 ASCII 无法确定编码，标注提示
            self._set_file_status(status_parts)
            self.result_table.clear()
        except Exception as e:
            logger.warning("Failed to select file %s: %s", p, e)

    def _get_strategy(self):
        """从下拉框获取当前选中的错误处理策略函数。"""
        return converter_get_strategy(self.err_cb.get())

    def _do_convert(self):
        """执行编码转换的主入口。

        流程：
        1. 校验文件选择、源/目标编码是否一致
        2. 对 Big5 目标编码给出繁简转换提示
        3. 解码文件 → 兼容性扫描 → 若兼容性 < 100% 则弹窗警告
        4. 调用 convert_file 执行实际转换
        5. 更新状态栏 & 结果表格 & 日志
        """
        if not self.selected_file:
            messagebox.showinfo("提示", "请先选择源文件")
            return

        src_enc = self.src_cb.get()
        tgt_enc = self.tgt_cb.get()
        if src_enc == tgt_enc:
            messagebox.showinfo("提示", "源编码和目标编码相同")
            return

        strategy = self._get_strategy()

        # Big5 转换需要繁简转换，额外确认
        is_big5 = tgt_enc.upper() in ("BIG5", "BIG5-HKSCS")
        if is_big5:
            if not messagebox.askyesno(
                "Big5 转换提示",
                "转换为 Big5 编码时，简体中文会自动转换为繁体中文。\n\n是否继续？"
            ):
                return

        try:
            # 1. 解码文件获取 CharacterToken 列表
            tokens = file_to_tokens(self.selected_file)

            # 2. 转换前兼容性扫描（预估目标编码是否能无损容纳所有字符）
            report = compatibility_scan(tokens, tgt_enc, s2t_convert=is_big5)
            if report.rate < 100:
                # 组装兼容性警告信息
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
            # 3. 执行实际转换并输出到文件
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

            # 组装日志信息（英文，供给 logging 模块记录）
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

            # 转换结果弹窗
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
            # 捕获转换过程中的任何异常
            messagebox.showerror("错误", str(e))

    def _clear_results(self):
        """清空转换结果及状态栏信息。"""
        self.conv_tokens = []
        self.result_table.clear()
        self.file_info_lbl.configure(text="")

    def _open_output(self):
        """确保输出目录存在后，用系统文件管理器打开。"""
        CONVERT_DIR.mkdir(parents=True, exist_ok=True)
        os.startfile(str(CONVERT_DIR))


# ---------------------------------------------------------------------------
# EncodingViewerTab —— 编码查看器标签页
# ---------------------------------------------------------------------------
class EncodingViewerTab(tk.Frame):
    """编码查看器标签页。支持打开文件或粘贴文本，实时分析每个字符在各种编码下的表现。"""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.current_file = None         # 当前打开的文件路径
        self.detected_encoding = ""      # 检测到的文件编码
        self.current_tokens = []         # 当前字符的 CharacterToken 列表
        self.analysis_results = []       # EncodingViewer 分析结果列表
        self._last_dir = str(CHARS_DIR)  # 上次目录，用于对话框初始路径
        self._setup_ui()

    def _setup_ui(self):
        """构建查看器标签页的完整 UI 布局。

        布局从上到下：工具栏 → 左右分栏（原始文本 / 编码分析表）→ 底部操作栏 → 状态栏。
        使用 grid 实现左右等高分栏，左栏固定宽度、右栏自适应拉伸。
        """
        # ── 1. 顶部工具栏（打开 / 粘贴 / 清空 / 打开输出目录 + 编码标签） ──
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

        # ── 2. 主内容区域（左：原始文本 / 右：编码分析表） ──
        content = tk.Frame(self)
        content.grid_rowconfigure(0, weight=1)
        content.grid_columnconfigure(0, weight=0)  # 左栏：固定宽度，不随窗口拉伸
        content.grid_columnconfigure(1, weight=1)  # 右栏：占满剩余空间

        # --- 左栏：原始文本输入框（只读显示用） ---
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
                            width=35,  # 固定宽度 35 字符，使左栏不会随窗口变宽
                            bg="white", fg="#111111", relief="flat", borderwidth=0,
                            highlightthickness=0, padx=4, pady=2, insertbackground="#111111")
        txt_in_vbar = tk.Scrollbar(txt_in_frame, orient="vertical", command=self.txt_in.yview)
        self.txt_in.configure(yscrollcommand=txt_in_vbar.set)
        self.txt_in.grid(row=0, column=0, sticky="nsew")
        txt_in_vbar.grid(row=0, column=1, sticky="ns")

        # --- 右栏：Canvas 编码分析表格（按字符逐行显示各编码的可用性） ---
        right_frm = tk.Frame(content, bg="#F2F2F2", bd=1, relief="solid")
        right_frm.grid(row=0, column=1, sticky="nsew", padx=(3, 0))
        right_frm.grid_rowconfigure(1, weight=1)
        right_frm.grid_columnconfigure(0, weight=1)

        tk.Label(right_frm, text="编码分析", font=("Microsoft YaHei", 9, "bold"),
                 bg="#F2F2F2").grid(row=0, column=0, sticky="w", padx=6, pady=(4, 2))
        self.table = ColoredTable(right_frm)
        self.table.grid(row=1, column=0, sticky="nsew", padx=4, pady=(2, 4))

        # ── 3. 底部操作栏（分析编码 / 图例 / 退出） ──
        bot = tk.Frame(self, bg="#EBEBEB")
        bb = tk.Frame(bot, bg="#EBEBEB")
        bb.pack(fill="x", padx=6, pady=3)

        create_button(bb, "分析编码", self._analyze, "#5BC0DE").pack(side="left", padx=3)
        create_button(bb, "退出", self._quit, "#D9534F").pack(side="right", padx=(3, 4))

        legend_frm = tk.Frame(bb)
        legend_frm.pack(side="right", padx=(0, 16))
        ColorLegend(legend_frm).pack()

        # ── 4. 状态栏（显示文件、编码检测、字符统计信息） ──
        self.status = tk.Label(self, text=DEFAULT_STATUS, anchor="w",
                                font=("Microsoft YaHei", 9),
                                bg="#E0E0E0", fg="#666")

        # ── 5. 组装各部分到主 Frame（顺序：上→中→底） ──
        self.status.pack(fill="x", side="bottom", padx=0, pady=0)
        create_horizontal_separator(self).pack(fill="x", side="bottom")

        bot.pack(fill="x", side="bottom", padx=0, pady=0)
        create_horizontal_separator(self).pack(fill="x", side="bottom")

        top.pack(fill="x", side="top", padx=0, pady=0)
        create_horizontal_separator(self).pack(fill="x", side="top")

        content.pack(fill="both", expand=True, side="top", padx=4, pady=4)

    def _set_status(self, msg):
        """更新底部状态栏文本。"""
        self.status.configure(text=msg)

    def _open_file(self, file_path=None):
        """弹出文件选择对话框，加载文件并立即进行编码检测与 Token 分析。

        若 file_path 不为 None（如从 _open_output 回调），则跳过对话框直接打开。
        分析后自动在右侧表格中显示各字符的编码兼容性。
        """
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

            # 复用共享检测管线（避免二次读取）
            _, result, csn_part = _detect_from_raw(raw_data, p)

            self.enc_lbl.configure(text=f"检测结果：{enc_name}  |  {csn_part}")

            # 状态栏显示：编码名称（纯 ASCII 标注）、charset-normalizer 结果、各引擎诊断摘要
            pure = " (编码不明确)" if result.is_pure_ascii else ""
            diag = " | ".join(f"{n}:{r[:1]}" for n, _, r in result.trials)
            self._set_status(f"已打开：{p} | 检测结果：{enc_name}{pure} | {csn_part} | {diag}")
            self.file_lbl.configure(text=p, fg="#222")
            self._analyze_tokens(tokens)
        except Exception as e:
            messagebox.showerror("错误", f"打开文件失败：\n{e}")
            logger.exception("Failed to open file")

    def _paste_text(self):
        """从系统剪贴板获取文本，填入左侧文本框。

        清空之前的状态（文件路径、检测编码等），因为粘贴来源无文件编码信息。
        """
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
        """清空文本框、分析表格、Token 缓存及状态显示。"""
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
        """分析左侧文本框中的文本（非文件模式）。

        将文本按 UTF-8 编码构建 CharacterToken，调用 charset-normalizer 辅助检测，
        最后将结果渲染到右侧 ColoredTable 中并更新状态栏统计数据。
        """
        text = self.txt_in.get("1.0", "end").rstrip("\n")
        if not text:
            messagebox.showinfo("提示", "请先输入或打开文本")
            return

        # 将每个字符按 UTF-8 编码构建 Token
        tokens = []
        raw_bytes = text.encode("utf-8")
        for ch in text:
            try:
                src_bytes = ch.encode("utf-8")
            except UnicodeEncodeError:
                src_bytes = b""
            tokens.append(CharacterToken(char=ch, source_encoding="UTF-8", source_bytes=src_bytes))

        self.current_tokens = tokens

        # 检测文本编码（仅用于参考显示，不支持文件级别检测细粒度）
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
        """将 Token 列表传递给 EncodingViewer 进行分析并在表格中展示。

        同时计算并显示概要统计：总字符数、各编码覆盖率、文件编码。
        """
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
        """打开输出目录并弹出文件选择对话框，选中的文件回传给 _open_file 继续分析。"""
        CONVERT_DIR.mkdir(parents=True, exist_ok=True)
        p = filedialog.askopenfilename(title="选择要检测的文件", initialdir=str(CONVERT_DIR),
                                       filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")])
        if p:
            self._open_file(file_path=p)

    @staticmethod
    def _quit():
        """直接退出进程。"""
        sys.exit(0)
