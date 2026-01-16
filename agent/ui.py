import json
import logging
import queue
import threading
import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk

import mss

from agent.agent import AgentState, GameAgent
from agent.config import AgentConfig
from agent.ollama_client import OllamaClient


@dataclass(frozen=True)
class MonitorOption:
    index: int
    label: str


class QueueHandler(logging.Handler):
    def __init__(self, log_queue: queue.Queue[str]) -> None:
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        self.log_queue.put(msg)


class AgentUI:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("AI Game Agent")
        self.root.geometry("900x600")

        self.log_queue: queue.Queue[str] = queue.Queue()
        self.logger = logging.getLogger("agent")
        self.logger.setLevel(logging.INFO)
        handler = QueueHandler(self.log_queue)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
        self.logger.handlers.clear()
        self.logger.addHandler(handler)

        self.agent_thread: threading.Thread | None = None
        self.stop_event = threading.Event()

        self.monitor_options = self._load_monitors()
        self._build_ui()
        self._poll_logs()

    def _load_monitors(self) -> list[MonitorOption]:
        options: list[MonitorOption] = []
        with mss.mss() as sct:
            for index, monitor in enumerate(sct.monitors):
                if index == 0:
                    continue
                label = f"{index}: {monitor['width']}x{monitor['height']} @ ({monitor['left']},{monitor['top']})"
                options.append(MonitorOption(index=index, label=label))
        return options

    def _build_ui(self) -> None:
        form_frame = ttk.Frame(self.root, padding=12)
        form_frame.pack(fill=tk.X)

        ttk.Label(form_frame, text="Monitor").grid(row=0, column=0, sticky=tk.W)
        self.monitor_var = tk.StringVar()
        self.monitor_combo = ttk.Combobox(
            form_frame,
            textvariable=self.monitor_var,
            values=[opt.label for opt in self.monitor_options],
            state="readonly",
            width=50,
        )
        if self.monitor_options:
            self.monitor_combo.current(0)
        self.monitor_combo.grid(row=0, column=1, sticky=tk.W, padx=8)

        ttk.Label(form_frame, text="Model").grid(row=1, column=0, sticky=tk.W)
        self.model_entry = ttk.Entry(form_frame, width=52)
        self.model_entry.insert(0, "llava:7b")
        self.model_entry.grid(row=1, column=1, sticky=tk.W, padx=8)

        ttk.Label(form_frame, text="Task").grid(row=2, column=0, sticky=tk.W)
        self.task_entry = ttk.Entry(form_frame, width=52)
        self.task_entry.insert(0, "mine_ore")
        self.task_entry.grid(row=2, column=1, sticky=tk.W, padx=8)

        ttk.Label(form_frame, text="Context").grid(row=3, column=0, sticky=tk.W)
        self.context_entry = ttk.Entry(form_frame, width=52)
        self.context_entry.insert(0, "start in mine, pickaxe equipped")
        self.context_entry.grid(row=3, column=1, sticky=tk.W, padx=8)

        ttk.Label(form_frame, text="Rules").grid(row=4, column=0, sticky=tk.W)
        self.rules_entry = ttk.Entry(form_frame, width=52)
        self.rules_entry.insert(0, "avoid enemies, return when inventory full")
        self.rules_entry.grid(row=4, column=1, sticky=tk.W, padx=8)

        self.dry_run_var = tk.BooleanVar(value=True)
        self.dry_run_check = ttk.Checkbutton(form_frame, text="Dry run", variable=self.dry_run_var)
        self.dry_run_check.grid(row=5, column=1, sticky=tk.W, padx=8, pady=(4, 0))

        button_frame = ttk.Frame(self.root, padding=12)
        button_frame.pack(fill=tk.X)

        self.start_button = ttk.Button(button_frame, text="Start", command=self.start_agent)
        self.start_button.pack(side=tk.LEFT)
        self.stop_button = ttk.Button(button_frame, text="Stop", command=self.stop_agent, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=8)
        self.copy_button = ttk.Button(button_frame, text="Copy JSON", command=self.copy_params_json)
        self.copy_button.pack(side=tk.LEFT, padx=8)
        self.paste_button = ttk.Button(button_frame, text="Paste JSON", command=self.paste_params_json)
        self.paste_button.pack(side=tk.LEFT)

        self.log_text = tk.Text(self.root, height=20, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

    def _poll_logs(self) -> None:
        while not self.log_queue.empty():
            msg = self.log_queue.get_nowait()
            self.log_text.configure(state=tk.NORMAL)
            self.log_text.insert(tk.END, msg + "\n")
            self.log_text.configure(state=tk.DISABLED)
            self.log_text.see(tk.END)
        self.root.after(200, self._poll_logs)

    def start_agent(self) -> None:
        if self.agent_thread and self.agent_thread.is_alive():
            return
        self.stop_event.clear()
        monitor_index = self._selected_monitor_index()
        config = AgentConfig(
            model=self.model_entry.get().strip(),
            screen_monitor=monitor_index,
            dry_run=self.dry_run_var.get(),
        )
        state = AgentState(
            task=self.task_entry.get().strip(),
            context=self.context_entry.get().strip(),
            rules=self.rules_entry.get().strip(),
        )
        ollama_ok, ollama_message = OllamaClient(config.ollama_url).check_connection(config.model)
        if ollama_ok:
            self.logger.info(ollama_message)
        else:
            self.logger.warning(ollama_message)
        agent = GameAgent(config, state, stop_event=self.stop_event, logger=self.logger)
        self.agent_thread = threading.Thread(target=agent.run, daemon=True)
        self.agent_thread.start()
        self.logger.info("Agent started")
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)

    def _collect_params(self) -> dict[str, object]:
        return {
            "monitor_index": self._selected_monitor_index(),
            "monitor_label": self.monitor_var.get(),
            "model": self.model_entry.get().strip(),
            "task": self.task_entry.get().strip(),
            "context": self.context_entry.get().strip(),
            "rules": self.rules_entry.get().strip(),
            "dry_run": self.dry_run_var.get(),
        }

    def _apply_params(self, payload: dict[str, object]) -> None:
        if "model" in payload:
            self.model_entry.delete(0, tk.END)
            self.model_entry.insert(0, str(payload["model"]))
        if "task" in payload:
            self.task_entry.delete(0, tk.END)
            self.task_entry.insert(0, str(payload["task"]))
        if "context" in payload:
            self.context_entry.delete(0, tk.END)
            self.context_entry.insert(0, str(payload["context"]))
        if "rules" in payload:
            self.rules_entry.delete(0, tk.END)
            self.rules_entry.insert(0, str(payload["rules"]))
        if "dry_run" in payload:
            self.dry_run_var.set(bool(payload["dry_run"]))
        monitor_label = payload.get("monitor_label")
        monitor_index = payload.get("monitor_index")
        if monitor_label:
            self.monitor_var.set(str(monitor_label))
        elif monitor_index is not None:
            matched = next((opt.label for opt in self.monitor_options if opt.index == int(monitor_index)), None)
            if matched:
                self.monitor_var.set(matched)
            else:
                self.logger.warning("Monitor index %s not found in available monitors", monitor_index)

    def copy_params_json(self) -> None:
        payload = self._collect_params()
        encoded = json.dumps(payload, ensure_ascii=False, indent=2)
        self.root.clipboard_clear()
        self.root.clipboard_append(encoded)
        self.logger.info("Parameters copied to clipboard as JSON")

    def paste_params_json(self) -> None:
        try:
            raw = self.root.clipboard_get()
        except tk.TclError as exc:
            self.logger.warning("Clipboard is empty or unavailable: %s", exc)
            return
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            self.logger.warning("Clipboard JSON is invalid: %s", exc)
            return
        if not isinstance(payload, dict):
            self.logger.warning("Clipboard JSON must be an object")
            return
        self._apply_params(payload)
        self.logger.info("Parameters loaded from clipboard JSON")

    def stop_agent(self) -> None:
        self.stop_event.set()
        self.logger.info("Stopping agent...")
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

    def _selected_monitor_index(self) -> int:
        selected_label = self.monitor_var.get()
        for opt in self.monitor_options:
            if opt.label == selected_label:
                return opt.index
        return 1

    def run(self) -> None:
        self.root.mainloop()


def run_ui() -> None:
    AgentUI().run()
