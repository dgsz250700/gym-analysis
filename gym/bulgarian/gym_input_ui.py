import os
import subprocess
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import cv2
from PIL import Image, ImageTk

from gym_input import INTEREST_FIELDS, run_analysis

WINDOW_TITLE = "Gym Input UI"
VIDEO_CANVAS_SIZE = (760, 540)


class GymInputUI:
    def __init__(self, root):
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.geometry("1280x760")

        self.analysis_thread = None
        self.current_result = None
        self.video_capture = None
        self.video_after_id = None
        self.video_photo = None
        self.is_paused = False
        self.playback_token = 0

        self._build_layout()

    def _build_layout(self):
        self.root.columnconfigure(0, weight=3)
        self.root.columnconfigure(1, weight=2)
        self.root.rowconfigure(1, weight=1)

        controls_frame = ttk.Frame(self.root, padding=12)
        controls_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
        controls_frame.columnconfigure(2, weight=1)

        self.process_button = ttk.Button(
            controls_frame,
            text="Seleccionar video y procesar",
            command=self.select_and_process_video,
        )
        self.process_button.grid(row=0, column=0, padx=(0, 8), pady=4, sticky="w")

        self.open_comparison_button = ttk.Button(
            controls_frame,
            text="Abrir comparacion en Excel",
            command=self.open_comparison_csv,
            state="disabled",
        )
        self.open_comparison_button.grid(row=0, column=1, padx=(0, 8), pady=4, sticky="w")

        self.pause_button = ttk.Button(
            controls_frame,
            text="Pausar video",
            command=self.toggle_pause,
            state="disabled",
        )
        self.pause_button.grid(row=0, column=2, padx=(0, 8), pady=4, sticky="w")

        self.status_var = tk.StringVar(value="Selecciona un video para comenzar.")
        self.status_label = ttk.Label(controls_frame, textvariable=self.status_var)
        self.status_label.grid(row=1, column=0, columnspan=3, sticky="w")

        self.progress = ttk.Progressbar(controls_frame, mode="indeterminate")
        self.progress.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(8, 0))

        video_frame = ttk.LabelFrame(self.root, text="Video con overlays", padding=12)
        video_frame.grid(row=1, column=0, sticky="nsew", padx=(12, 6), pady=12)
        video_frame.rowconfigure(0, weight=1)
        video_frame.columnconfigure(0, weight=1)

        self.video_label = ttk.Label(video_frame, anchor="center")
        self.video_label.grid(row=0, column=0, sticky="nsew")

        right_panel = ttk.Frame(self.root, padding=(6, 12, 12, 12))
        right_panel.grid(row=1, column=1, sticky="nsew")
        right_panel.rowconfigure(1, weight=1)
        right_panel.columnconfigure(0, weight=1)

        comparison_frame = ttk.LabelFrame(right_panel, text="Comparacion", padding=12)
        comparison_frame.grid(row=0, column=0, sticky="ew")
        comparison_frame.columnconfigure(0, weight=1)

        self.comparison_path_var = tk.StringVar(value="CSV de comparacion: aun no generado")
        self.comparison_path_label = ttk.Label(
            comparison_frame,
            textvariable=self.comparison_path_var,
            wraplength=420,
            justify="left",
        )
        self.comparison_path_label.grid(row=0, column=0, sticky="w")

        summary_frame = ttk.LabelFrame(right_panel, text="Resumen", padding=12)
        summary_frame.grid(row=1, column=0, sticky="nsew", pady=(12, 0))
        summary_frame.rowconfigure(0, weight=1)
        summary_frame.columnconfigure(0, weight=1)

        self.summary_text = tk.Text(summary_frame, wrap="word", state="disabled")
        self.summary_text.grid(row=0, column=0, sticky="nsew")

        summary_scrollbar = ttk.Scrollbar(
            summary_frame,
            orient="vertical",
            command=self.summary_text.yview,
        )
        summary_scrollbar.grid(row=0, column=1, sticky="ns")
        self.summary_text.configure(yscrollcommand=summary_scrollbar.set)

    def select_and_process_video(self):
        if self.analysis_thread is not None and self.analysis_thread.is_alive():
            return

        selected_video = filedialog.askopenfilename(
            title="Selecciona el video a analizar",
            filetypes=[
                ("Videos", "*.mp4 *.mov *.avi *.mkv *.m4v"),
                ("Todos los archivos", "*.*"),
            ],
        )
        if not selected_video:
            return

        self._stop_video_playback()
        self._set_summary_text("")
        self.comparison_path_var.set("CSV de comparacion: procesando...")
        self.status_var.set("Procesando video, esto puede tardar unos segundos...")
        self.process_button.configure(state="disabled")
        self.open_comparison_button.configure(state="disabled")
        self.pause_button.configure(state="disabled")
        self.progress.start(10)

        self.analysis_thread = threading.Thread(
            target=self._run_analysis_worker,
            args=(selected_video,),
            daemon=True,
        )
        self.analysis_thread.start()

    def _run_analysis_worker(self, selected_video):
        try:
            selected_path = Path(selected_video)
            run_folder_name = f"{selected_path.stem}_ui_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            output_dir = selected_path.parent / "ui_runs" / run_folder_name
            result = run_analysis(
                video_path=selected_video,
                output_dir=output_dir,
            )
            self.root.after(0, lambda: self._handle_analysis_success(result))
        except Exception as exc:
            self.root.after(0, lambda: self._handle_analysis_error(exc))

    def _handle_analysis_success(self, result):
        self.analysis_thread = None
        self.current_result = result
        self.progress.stop()
        self.process_button.configure(state="normal")
        self.open_comparison_button.configure(state="normal")
        self.pause_button.configure(state="normal")
        self.status_var.set("Procesamiento finalizado.")
        self.comparison_path_var.set(f"CSV de comparacion: {result['output_paths']['comparison']}")
        self._set_summary_text(self._build_summary(result))
        self._load_overlay_video(result["output_paths"]["overlay_video"])

    def _handle_analysis_error(self, exc):
        self.analysis_thread = None
        self.progress.stop()
        self.process_button.configure(state="normal")
        self.open_comparison_button.configure(state="disabled")
        self.pause_button.configure(state="disabled")
        self.status_var.set("Ocurrio un error durante el procesamiento.")
        messagebox.showerror("Error", str(exc))

    def _build_summary(self, result):
        lines = [
            f"Video: {result['video_path'].name}",
            f"Overlay: {result['output_paths']['overlay_video'].name}",
            f"Comparacion: {result['output_paths']['comparison'].name}",
            "",
            f"Frames guardados: {len(result['rows'])}",
            f"Cambios detectados: {len(result['changes_rows'])}",
            f"Comparaciones: {len(result['comparison_rows'])}",
            "",
        ]

        if not result["comparison_rows"]:
            lines.append("No se encontraron segmentos comparables.")
            return "\n".join(lines)

        for row in result["comparison_rows"]:
            lines.append(f"Segmento {row['segment_id']} - {row['segment_type']}")
            lines.append(f"Evaluacion general: {row.get('segment_assessment') or 'sin evaluacion'}")

            for field_name in INTEREST_FIELDS:
                signed_diff = row.get(f"mean_signed_pct_diff_{field_name}")
                abs_diff = row.get(f"mean_abs_pct_diff_{field_name}")
                assessment = row.get(f"assessment_{field_name}")

                if signed_diff is None:
                    lines.append(f"{field_name}: sin puntos comparables")
                    continue

                lines.append(
                    f"{field_name}: {signed_diff:+.2f}% "
                    f"(abs {abs_diff:.2f}%) - {assessment}"
                )

            lines.append("")

        return "\n".join(lines).strip()

    def _set_summary_text(self, text):
        self.summary_text.configure(state="normal")
        self.summary_text.delete("1.0", tk.END)
        self.summary_text.insert("1.0", text)
        self.summary_text.configure(state="disabled")

    def _load_overlay_video(self, video_path):
        self._stop_video_playback()
        self.video_capture = cv2.VideoCapture(str(video_path))
        self.playback_token += 1
        self.is_paused = False
        self.pause_button.configure(text="Pausar video", state="normal")
        self._show_next_frame(self.playback_token)

    def _show_next_frame(self, playback_token):
        if playback_token != self.playback_token:
            return

        self.video_after_id = None
        if self.video_capture is None or self.is_paused:
            return

        ret, frame = self.video_capture.read()
        if not ret:
            self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.video_capture.read()
            if not ret:
                return

        display_frame = self._prepare_frame_for_display(frame)
        self.video_photo = ImageTk.PhotoImage(display_frame)
        self.video_label.configure(image=self.video_photo)

        fps = self.video_capture.get(cv2.CAP_PROP_FPS)
        delay = 33 if fps <= 0 else max(15, int(1000 / fps))
        self.video_after_id = self.root.after(delay, lambda: self._show_next_frame(playback_token))

    def _prepare_frame_for_display(self, frame):
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(frame_rgb)
        image.thumbnail(VIDEO_CANVAS_SIZE, Image.Resampling.LANCZOS)
        return image

    def toggle_pause(self):
        if self.video_capture is None:
            return

        self.is_paused = not self.is_paused
        self.pause_button.configure(text="Reanudar video" if self.is_paused else "Pausar video")

        if not self.is_paused:
            self._show_next_frame(self.playback_token)

    def _stop_video_playback(self):
        if self.video_after_id is not None:
            try:
                self.root.after_cancel(self.video_after_id)
            except tk.TclError:
                pass
            self.video_after_id = None

        self.playback_token += 1

        if self.video_capture is not None:
            self.video_capture.release()
            self.video_capture = None

        self.video_label.configure(image="")
        self.video_photo = None
        self.is_paused = False

    def open_comparison_csv(self):
        if not self.current_result:
            return

        comparison_path = Path(self.current_result["output_paths"]["comparison"])
        if not comparison_path.exists():
            messagebox.showerror("Error", f"No se encontro el archivo: {comparison_path}")
            return

        try:
            os.startfile(str(comparison_path))
        except AttributeError:
            subprocess.Popen(["open" if os.name == "posix" else "xdg-open", str(comparison_path)])
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudo abrir el archivo:\n{exc}")

    def on_close(self):
        self._stop_video_playback()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = GymInputUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
