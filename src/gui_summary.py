"""
Module for a standalone GUI to summarize YouTube videos.
"""
import os
import tkinter as tk
import webbrowser
from queue import Empty, Queue
from threading import Thread
from tkinter import filedialog, messagebox, scrolledtext, ttk

import pyperclip

from src.common.cc_parser import process_url
from src.common.util import extract_id, is_youtube_url, preprocess_string
from src.common.youtube_info import probe_url
from src.generative_ai.gemini import call_gemini_api_for_summary
from src.manager.prompt_manager import PromptManager
from src.manager.settings_manager import SettingsManager


__version__ = "1.0.0"


class AddPromptWindow(tk.Toplevel):
    """A pop-up window for adding new summary instructions."""
    
    def __init__(self, parent, prompt_manager: PromptManager, on_success: callable):
        super().__init__(parent)
        self.prompt_manager = prompt_manager
        self.on_success = on_success
        self.title("Add New Instructions")
        self.transient(parent)
        self.grab_set()
        
        frame = ttk.Frame(self, padding="10")
        frame.pack(expand=True, fill="both")
        
        # Name Entry
        name_frame = ttk.Frame(frame)
        name_frame.pack(fill="x", pady=5)
        ttk.Label(name_frame, text="Instructions Name:", width=18).pack(side="left")
        self.name_var = tk.StringVar()
        ttk.Entry(name_frame, textvariable=self.name_var, width=50).pack(side="left", fill="x", expand=True)
        
        # Required imports:
        # import tkinter as tk
        # from tkinter import ttk
        
        # 1. A label for the model selection dropdown
        model_frame = ttk.Frame(frame)
        model_frame.pack(fill="x", pady=5)
        model_label = ttk.Label(model_frame, text="Gemini Model:").pack(side="left")
        
        # 2. A Combobox to select the Gemini model
        # This StringVar will hold the selected value from the combobox
        selected_model = tk.StringVar()
        gemini_models = [
            "gemini-1.5-pro-latest",
            "gemini-1.5-flash-latest",
            "gemini-pro",
            "gemini-pro-vision"
        ]
        self.model_combobox = ttk.Combobox(
            model_frame,
            textvariable=selected_model,
            values=gemini_models,
            state="readonly"  # Prevents users from typing in the box
        )
        self.model_combobox.pack(side="left", fill="x", expand=True)
        self.model_combobox.set(gemini_models[0])  # Set a default value
        
        # Instructions Text
        text_frame = ttk.LabelFrame(frame, text="Instructions Text")
        text_frame.pack(fill="both", expand=True, pady=5)
        self.instructions_text = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, height=10)
        self.instructions_text.pack(fill="both", expand=True, side="bottom")
        
        # Buttons
        button_frame = ttk.Frame(frame, padding="5")
        button_frame.pack(fill="x", side="bottom")
        ttk.Button(button_frame, text="Add", command=self._submit).pack(side="right", padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.destroy).pack(side="right")
    
    def _submit(self):
        name = self.name_var.get().strip()
        
        text = self.instructions_text.get(1.0, tk.END).strip()
        model = self.model_combobox.get().strip()
        
        if not name:
            messagebox.showerror("Validation Error", "Instructions name cannot be empty.", parent=self)
            return
        if not text:
            messagebox.showerror("Validation Error", "Instructions text cannot be empty.", parent=self)
            return
        if name in self.prompt_manager.get_prompts():
            messagebox.showerror("Validation Error", "An instruction set with this name already exists.", parent=self)
            return
        
        self.prompt_manager.add_prompt(name, text)
        self.on_success()
        self.destroy()



class SettingsWindow(tk.Toplevel):
    """
    A pop-up window for configuring application settings.
    Can display an error message upon opening.
    """
    def __init__(self, parent, settings_manager: SettingsManager, error_message: str = None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.title("Settings")
        self.transient(parent)
        self.grab_set()

        frame = ttk.Frame(self, padding="10")
        frame.pack(expand=True, fill="both")

        # Display error message if provided
        if error_message:
            global img_warning
            error_frame = ttk.Frame(frame)
            error_frame.pack(fill="x", pady=(0, 10))
            ttk.Label(error_frame, text=error_message, foreground="red").pack(side="left")

        # API Key
        api_frame = ttk.LabelFrame(frame, text="Gemini API Key", padding="5")
        api_frame.pack(fill="x", pady=5)
        api_entry_frame = ttk.Frame(api_frame)
        api_entry_frame.pack(fill="x")
        self.api_key_var = tk.StringVar(value=self.settings_manager.get('api_key'))
        ttk.Entry(api_entry_frame, textvariable=self.api_key_var, width=40, show="*").pack(side="left", fill="x", expand=True)
        ttk.Button(api_entry_frame, text="Open API key dashboard", command=self._open_api_key_page).pack(side="left", padx=(5, 0))

        # Output Folder
        output_frame = ttk.LabelFrame(frame, text="Output Folder", padding="5")
        output_frame.pack(fill="x", pady=5)
        output_entry_frame = ttk.Frame(output_frame)
        output_entry_frame.pack(fill="x")
        self.output_folder_var = tk.StringVar(value=self.settings_manager.get('output_folder'))
        ttk.Entry(output_entry_frame, textvariable=self.output_folder_var, width=40).pack(side="left", fill="x", expand=True)
        ttk.Button(output_entry_frame, text="Browse...", command=self._browse_folder).pack(side="left", padx=(5, 0))

        # Buttons
        button_frame = ttk.Frame(frame, padding="5")
        button_frame.pack(fill="x", side="bottom")
        ttk.Button(button_frame, text="Submit", command=self._submit).pack(side="right", padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.destroy).pack(side="right")
    
    @staticmethod
    def _open_api_key_page():
        """Opens the Gemini API key management page in a web browser."""
        webbrowser.open_new_tab("https://aistudio.google.com/app/apikey")

    def _browse_folder(self):
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder: self.output_folder_var.set(folder)

    def _submit(self):
        new_settings = {'api_key': self.api_key_var.get(), 'output_folder': self.output_folder_var.get()}
        self.settings_manager.save_settings(new_settings)
        
        messagebox.showinfo("Settings Saved", "Your settings have been saved.", parent=self)
        self.destroy()


class SummaryGUI:
    """A standalone GUI for summarizing YouTube videos."""
    @property
    def cc_folder(self) -> str:
        return self.settings_manager.settings.get("cc_folder")
    
    def __init__(self, master: tk.Tk):
        self.master = master
        master.title("YouTube Video Summarizer")
        master.geometry("700x520")

        self.queue = Queue()
        self.settings_manager = SettingsManager()
        self.prompt_manager = PromptManager()
        self.current_summary_path = None

        # --- Top & Actions Frame ---
        actions_frame = ttk.LabelFrame(master, text="Input & Actions", padding="10")
        actions_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(actions_frame, text="URL or Video ID:").pack(side=tk.LEFT, padx=(5, 0), pady=5)
        self.url_var = tk.StringVar()
        url_entry = ttk.Entry(actions_frame, textvariable=self.url_var)
        url_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5, pady=5)
        url_entry.bind("<Return>", self._start_summary_thread)
        
        ttk.Button(actions_frame, text="Paste", command=self._paste_from_clipboard).pack(side=tk.LEFT, padx=(0, 5),
                                                                                         pady=5)
        self.load_button = ttk.Button(actions_frame, text="Load Summary", command=self._load_summary_from_file)
        self.load_button.pack(side=tk.LEFT, pady=5)

        # --- Prompt Selection Frame ---
        prompt_frame = ttk.LabelFrame(master, text="Instructions", padding="5")
        prompt_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(prompt_frame, text="Summary:").pack(side=tk.LEFT, padx=(5,0))
        self.prompt_var = tk.StringVar()
        self.prompt_combobox = ttk.Combobox(prompt_frame, textvariable=self.prompt_var, state="readonly")
        self.prompt_combobox.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self._refresh_prompts_combobox()
        ttk.Button(prompt_frame, text="Add", command=self._open_add_prompt_window).pack(side=tk.LEFT)
        ttk.Button(prompt_frame, text="Delete", command=self._delete_selected_prompt).pack(side=tk.LEFT, padx=(5, 0))
        
        # --- Title Frame ---
        title_frame = ttk.LabelFrame(master, text="Video Title", padding="5")
        title_frame.pack(fill=tk.X, padx=10, pady=5)
        self.video_title_var = tk.StringVar(value="...")
        ttk.Label(title_frame, textvariable=self.video_title_var, wraplength=650, justify=tk.LEFT).pack(fill=tk.X, padx=5, pady=2)

        # --- Output Frame ---
        output_frame = ttk.LabelFrame(master, text="Summary", padding="10")
        output_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.summary_text = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD, state=tk.DISABLED, height=5)
        self.summary_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- Bottom Frame for Controls ---
        bottom_frame = ttk.Frame(master, padding=(10, 5, 10, 10))
        bottom_frame.pack(fill=tk.X)

        self.summarize_button = ttk.Button(bottom_frame, text="Summarize", command=self._start_summary_thread)
        self.summarize_button.pack(side=tk.LEFT, padx=(10, 20), pady=5)
        self.copy_button = ttk.Button(bottom_frame, text="Copy Summary", command=self._copy_summary_to_clipboard)
        self.copy_button.pack(side=tk.LEFT)
        self.delete_button = ttk.Button(bottom_frame, text="Delete Summary", command=self._delete_summary)
        self.delete_button.pack(side=tk.LEFT, padx=(10, 10))
        settings_button = ttk.Button(bottom_frame, text="Settings", command=self._open_settings)
        settings_button.pack(side=tk.RIGHT)

        self.master.after(100, self._process_queue)
    
    def _paste_from_clipboard(self):
        """
        Pastes content from the clipboard into the URL entry if it is a valid YouTube URL or video ID.
        """
        try:
            clipboard_content = self.master.clipboard_get().strip()
            # A simple heuristic for video ID is checking the length.
            if is_youtube_url(clipboard_content) or len(clipboard_content) == 11:
                self.url_var.set(clipboard_content)
            else:
                messagebox.showwarning(
                    "Invalid Clipboard Content",
                    "The text in your clipboard does not appear to be a valid YouTube URL or Video ID.",
                    parent=self.master
                )
        except tk.TclError:
            messagebox.showwarning(
                "Empty Clipboard",
                "Your clipboard is empty.",
                parent=self.master
            )
        except Exception as e:
            messagebox.showerror(
                "Paste Error",
                f"Could not read from clipboard:\n{e}",
                parent=self.master
            )
    
    def _delete_selected_prompt(self):
        """Deletes the currently selected prompt from the combobox."""
        selected_prompt = self.prompt_var.get()
        
        if not selected_prompt:
            messagebox.showwarning("No Selection", "No prompt is selected to delete.", parent=self.master)
            return
        
        if selected_prompt == self.prompt_manager.DEFAULT_PROMPT_NAME:
            messagebox.showerror("Action Not Allowed", "The default prompt cannot be deleted.", parent=self.master)
            return
        
        if messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete the prompt:\n'{selected_prompt}'?",
                               parent=self.master):
            self.prompt_manager.delete_prompt(selected_prompt)
            self._refresh_prompts_combobox()
            messagebox.showinfo("Success", f"Prompt '{selected_prompt}' has been deleted.", parent=self.master)
    
    def _refresh_prompts_combobox(self):
        """Reloads prompts and updates the combobox."""
        self.prompt_manager.prompts = self.prompt_manager.load_prompts()
        prompt_names = list(self.prompt_manager.get_prompts().keys())
        self.prompt_combobox['values'] = prompt_names
        if prompt_names:
            self.prompt_combobox.set(prompt_names[0])
    
    def _open_add_prompt_window(self):
        """Opens the pop-up to add new instructions."""
        AddPromptWindow(self.master, self.prompt_manager, on_success=self._refresh_prompts_combobox)
    
    def _copy_summary_to_clipboard(self):
        summary_content = self.summary_text.get(1.0, tk.END).strip()
        if not summary_content or summary_content.startswith(("...", "Validating input")):
            messagebox.showwarning("No Summary", "There is no summary text to copy.", parent=self.master)
            return
        try:
            pyperclip.copy(summary_content)
            messagebox.showinfo("Copied", "Summary has been copied to the clipboard.", parent=self.master)
        except Exception as e:
            messagebox.showerror("Copy Error", f"Could not copy text to clipboard:\n{e}", parent=self.master)

    def _delete_summary(self):
        if not self.current_summary_path:
            messagebox.showwarning("No Summary Loaded", "No summary file is currently loaded to be deleted.", parent=self.master)
            return
        
        if messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete this summary file?\n\n{self.current_summary_path}", parent=self.master):
            try:
                os.remove(self.current_summary_path)
                messagebox.showinfo("Success", "Summary file has been deleted.", parent=self.master)
                self._set_summary_text("")
                self.video_title_var.set("...")
                self.current_summary_path = None
            except Exception as e:
                messagebox.showerror("Delete Error", f"Failed to delete the file:\n{e}", parent=self.master)

    def _load_summary_from_file(self):
        initial_dir = self.settings_manager.get('output_folder') or os.path.expanduser("~")
        filepath = filedialog.askopenfilename(
            title="Select a Summary File", initialdir=initial_dir, filetypes=(("Text files", "*.txt"), ("All files", "*.*"))
        )
        if not filepath: return
        try:
            with open(filepath, 'r', encoding='utf-8') as f: summary_content = f.read()
            self._set_summary_text(summary_content)
            self.video_title_var.set(os.path.basename(filepath))
            self.current_summary_path = filepath
        except Exception as e:
            messagebox.showerror("Error Loading File", f"Failed to read the summary file:\n{e}", parent=self.master)

    def _open_settings(self, error_message=None):
        SettingsWindow(self.master, self.settings_manager, error_message)

    def _start_summary_thread(self, event=None):
        input_text = self.url_var.get().strip()
        if not input_text:
            messagebox.showwarning("Input Required", "Please enter a YouTube URL or Video ID.", parent=self.master)
            return
        self.summarize_button.config(state=tk.DISABLED); self.load_button.config(state=tk.DISABLED); self.delete_button.config(state=tk.DISABLED)
        self.video_title_var.set("..."); self.current_summary_path = None
        self._set_summary_text("Validating input and fetching video title...")
        thread = Thread(target=self._summarize_video, args=(input_text,)); thread.daemon = True; thread.start()

    def _summarize_video(self, input_text: str):
        try:
            api_key = self.settings_manager.get('api_key')
            output_folder = self.settings_manager.get('output_folder')
            if not api_key: self.queue.put(('SHOW_SETTINGS', 'API Key is not set. Please provide one in Settings.')); return
            if not output_folder: self.queue.put(('SHOW_SETTINGS', 'Output folder is not set. Please provide one in Settings.')); return

            if is_youtube_url(input_text): video_id = extract_id(input_text)
            elif len(input_text) == 11: video_id = input_text
            else: raise ValueError("Invalid input. Please provide a valid YouTube URL or 11-character video ID.")
            
            url = f"https://www.youtube.com/watch?v={video_id}"
            self.queue.put(('SET_TITLE', 'Fetching title and CC...'))
            metadata_file = probe_url(url)
            import json
            metadata = json.load(open(metadata_file))
            title = metadata['title']
            
            cc_path = self.get_cc_file(video_id)
            with open(cc_path, 'r', encoding='utf-8') as f:
                cc_text = f.read()
            
            self.queue.put(('SET_TITLE', title))
            self.queue.put(f"Calling API for Video ID: {video_id}...")
            
            # Get selected prompt template and format it
            prompt_name = self.prompt_var.get()
            prompt_template = self.prompt_manager.get_prompt(prompt_name)
            final_prompt = prompt_template['text'] + f"\n\nThe Closed Captions are:\n{cc_text}"
            
            filename = f"[{video_id}] - {preprocess_string(prompt_name)} - {preprocess_string(metadata['uploader'])} - {preprocess_string(title)}"
            json_file = filename + ".json"
            output_file = os.path.join(output_folder, json_file)
            api_response = call_gemini_api_for_summary(
                video_id,
                prompt_text=final_prompt,
                api_key_override=api_key,
                output_file=output_file
            )
            if "error" in api_response: raise RuntimeError(f"API Error: {api_response['error']}\n{api_response.get('response_content', '')}")

            summary_text = str(api_response.get("candidates")[0].get("content").get("parts")[0].get("text"))
            
            # Save the text summary with the new filename format
            filepath = os.path.join(output_folder, filename+".txt")
            with open(filepath, 'w', encoding='utf-8') as f: f.write(summary_text)

            self.queue.put(('SET_SUMMARY_PATH', filepath))
            self.queue.put(summary_text)

        except Exception as e:
            self.queue.put(('SET_TITLE', '...')); self.queue.put(f"An error occurred:\n{str(e)}")
        finally:
            self.queue.put("ENABLE_BUTTONS")
    
    def _process_queue(self):
        try:
            while True:
                msg = self.queue.get_nowait()
                if isinstance(msg, tuple):
                    if msg[0] == 'SET_TITLE': self.video_title_var.set(msg[1])
                    elif msg[0] == 'SHOW_SETTINGS': self._open_settings(error_message=msg[1])
                    elif msg[0] == 'SET_SUMMARY_PATH': self.current_summary_path = msg[1]
                elif msg == "ENABLE_BUTTONS":
                    self.summarize_button.config(state=tk.NORMAL); self.load_button.config(state=tk.NORMAL); self.delete_button.config(state=tk.NORMAL)
                else:
                    self._set_summary_text(msg)
        except Empty: pass
        finally: self.master.after(100, self._process_queue)

    def _set_summary_text(self, text: str):
        self.summary_text.config(state=tk.NORMAL); self.summary_text.delete(1.0, tk.END); self.summary_text.insert(tk.END, text); self.summary_text.config(state=tk.DISABLED)
    
    def get_cc_file(self, video_id: str, allow_download: bool = True) -> str:
        """Returns the path to the CC file for a given video ID, if it exists."""
        candidates = [os.path.join(self.cc_folder, f) for f in os.listdir(self.cc_folder) if f.__contains__(video_id)]
        
        if len(candidates) == 0:
            if allow_download:
                print("No potential CC files found for video ID: " + video_id + ". Attempting to download file.")
                process_url(url=f"https://www.youtube.com/watch?v={video_id}", output_folder=self.cc_folder)
                return self.get_cc_file(video_id=video_id, allow_download=False)
            else:
                raise FileNotFoundError(f"No potential CC files found for video ID: {video_id}.")
        elif len(candidates) > 0:
            output = candidates[0]
            return output
        raise RuntimeError(f"Unable to fetch CC file for video_id={video_id}")
    
    # def get_out_file(self, video_id: str, response_id: str) -> str:
    #     """Returns the path to the output file for a given video and response ID. Create model root if need be."""
    #     # if not os.path.exists(os.path.join(self.output_folder, model)):
    #     #     os.makedirs(os.path.join(self.output_folder, model))
    #     return os.path.join(self.output_folder, f"{video_id}_{response_id}.json")

    @staticmethod
    def run():
        root = tk.Tk(); app = SummaryGUI(root); root.mainloop()
