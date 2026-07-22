import threading
import tkinter as tk
from tkinter import messagebox, ttk

from collector.collector import ReadOnlyMailboxCollector
from modules.config import load_config
from modules.logging_setup import configure_logging
from modules.safety import ReadOnlyViolation


class MainWindow(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("OutSmart Werkbon Assistent - Read-Only Collector")
        self.geometry("980x640")
        self.minsize(860, 560)
        self.config_data = load_config()
        self._build_ui()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        banner = tk.Frame(self, bg="#b91c1c", height=48)
        banner.grid(row=0, column=0, sticky="ew")
        banner.grid_propagate(False)
        tk.Label(
            banner,
            text="READ-ONLY MODE - Outlook wordt alleen gelezen; er worden geen mails gewijzigd",
            bg="#b91c1c",
            fg="white",
            font=("Segoe UI", 12, "bold"),
        ).pack(side="left", padx=18)

        top = ttk.Frame(self, padding=16)
        top.grid(row=1, column=0, sticky="ew")
        top.columnconfigure(1, weight=1)
        ttk.Label(top, text="OutSmart Werkbon Assistent", font=("Segoe UI", 18, "bold")).grid(row=0, column=0, sticky="w")
        mode = "Demo/mock" if self.config_data.demo_mode else "Real Outlook disabled unless allowed"
        ttk.Label(top, text=f"Collector: {mode} | Max mails/map: {self.config_data.max_mails_per_folder}").grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.start_button = ttk.Button(top, text="Start veilige demo-export", command=self.start_demo_export)
        self.start_button.grid(row=0, column=2, rowspan=2, sticky="e", padx=(12, 0))

        body = ttk.PanedWindow(self, orient="horizontal")
        body.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 16))

        left = ttk.Frame(body, padding=12)
        right = ttk.Frame(body, padding=12)
        body.add(left, weight=1)
        body.add(right, weight=3)

        ttk.Label(left, text="Mailboxprofielen", font=("Segoe UI", 12, "bold")).pack(anchor="w")
        self.profile_list = tk.Listbox(left, height=12)
        self.profile_list.pack(fill="both", expand=True, pady=(8, 0))
        for folder, profile in self.config_data.mailbox_profiles.items():
            self.profile_list.insert("end", f"{folder} -> {profile.get('debiteur', '')} {profile.get('naam', '')}")

        ttk.Label(right, text="Collector-log", font=("Segoe UI", 12, "bold")).pack(anchor="w")
        self.log = tk.Text(right, height=20, wrap="word")
        self.log.pack(fill="both", expand=True, pady=(8, 0))
        self._log("Klaar. Demo-modus gebruikt geen Outlook en wijzigt niets.")
        self._log("Gebruik deze versie later op de werk-pc om een portable exportpakket te maken.")

        footer = ttk.Label(self, text="Verboden acties zijn technisch geblokkeerd: markeren, verplaatsen, verwijderen, verzenden, antwoorden, categorieen wijzigen en mailboxfolders aanpassen.")
        footer.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 12))

    def _log(self, message: str) -> None:
        self.log.insert("end", message + "\n")
        self.log.see("end")
        self.update_idletasks()

    def start_demo_export(self) -> None:
        self.start_button.config(state="disabled")
        self._log("Demo-export gestart...")
        thread = threading.Thread(target=self._run_demo_export, daemon=True)
        thread.start()

    def _run_demo_export(self) -> None:
        try:
            collector = ReadOnlyMailboxCollector(self.config_data)
            result = collector.run(demo_mode=True)
            self._log(f"Export klaar: {result.export_dir}")
            self._log(f"ZIP klaar: {result.zip_path}")
            self._log(f"Manifest: {result.manifest_path}")
            self._log(f"Rapport: {result.report_path}")
            messagebox.showinfo("Export klaar", f"Demo-export aangemaakt:\n{result.zip_path}")
        except ReadOnlyViolation as exc:
            self._log(f"READ-ONLY blokkade: {exc}")
            messagebox.showerror("Read-only blokkade", str(exc))
        except Exception as exc:
            self._log(f"Fout: {exc}")
            messagebox.showerror("Fout", str(exc))
        finally:
            self.start_button.config(state="normal")


def run_app() -> None:
    configure_logging()
    app = MainWindow()
    app.mainloop()
