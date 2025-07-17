#ACES = Amendable Controller for Execution of Scripts
#Author: Jaiwanth Karthi
#Last patch: 05-Mar-24

###take care of the dated job overshooting current time msg thing

import time
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler

import pickle
import os
import subprocess
import winsound

import tkinter as tk
import tkinter.filedialog as filedialog
from tkinter import ttk


class ScriptError(Exception):
	pass

class CacheFile:
	instances = []

	def __init__(self, filepath):
		self.instances.append(self)
		self.filepath = filepath
		self.cache = None

		self.load()

	def load(self):
		if os.path.isfile(self.filepath):
			with open(self.filepath, "rb") as file:
				self.cache = pickle.load(file)
		else:
			print("---Cache file non-existent---")
			self.cache = {'dated_year': 2024, 'dated_month': 3, 'dated_date': 5, 
						  'dated_hour': 16, 'dated_minute': 0, 'dated_second': 0, 
						  'interval_days': 0, 'interval_hours': 0, 
						  'interval_minutes': 0, 'interval_seconds': 1, 
						  'cron_year': '*', 'cron_month': '*', 'cron_day': '*', 
						  'cron_hour': '*', 'cron_minute': '*', 'cron_second': '*/1', 
						  'selected_filepath': None, 'cmd_var': ''}

	def save(self):
		file = open(self.filepath, "wb")
		pickle.dump(self.cache, file)
		file.close()

class CmdScript:
	def __init__(self, content, exec_job_handle=None, exec_type=None):
		self.content = content
		self.exec_job_handle = exec_job_handle
		self.exec_type = exec_type

	def execute(self):
		subprocess.call(self.content.split(" "))

	def get_name(self):
		if self.content:
			return "Cmd{" + self.content + "}"
		return "Cmd{}"

class ActionScript(CmdScript):
	def __init__(self, filepath, exec_job_handle=None, exec_type=None):
		super().__init__("", exec_job_handle, exec_type)
		self.filepath = filepath
		self.load_content()

	def load_content(self):
		try:
			with open(self.filepath, "r") as file:
				self.content = file.read()
		except:
			raise ScriptError("Script file not found!")

	###deprecated
	#def write_content(self, write_content):
	#	with open(self.filepath, "w") as file:
	#		file.write(write_content)
	#	self.content = write_content

	###deprecated
	#def subprocess_execute(self):
	#	subprocess.call(["python", filepath])

	def execute(self):
		exec(self.content) ###use cmd-subprocess implementation???

	def get_name(self):
		return "File{" + os.path.basename(self.filepath) + "}"

class Handler:
	instances = []

	def __init__(self):
		self.instances.append(self)
		self.scripts = []

		self.scheduler = BackgroundScheduler(daemon = True)

	def mainloop(self):
		self.scheduler.start()

	#run at specified time, once
	def add_dated_script(self, script_object, exec_datetime):
		self.scripts.append(script_object)

		job_handle = self.scheduler.add_job(script_object.execute, "date", run_date=exec_datetime)
		script_object.exec_job_handle = job_handle
		return job_handle

	#run multiple times with given time interval in between calls
	def add_interval_script(self, script_object, **kwargs): #kwargs to pass to scheduler
		self.scripts.append(script_object)

		#hours = 1, seconds = 3
		job_handle = self.scheduler.add_job(script_object.execute, "interval", **kwargs)
		script_object.exec_job_handle = job_handle
		return job_handle

	#cron:= "a command to an operating system or server for a job that is to be executed at a specified time"
	#a flexible schedule method, like comination of dated and interval. Relies on string criteria and syntax
	def add_cron_script(self, script_object, **kwargs): #kwargs to pass to scheduler
		self.scripts.append(script_object)

		#hour = 1, second = "*/2"
		job_handle = self.scheduler.add_job(script_object.execute, "cron", **kwargs)
		script_object.exec_job_handle = job_handle
		return job_handle

	def remove_scipt_by_id(self, given_id):
		found = False
		for script in self.scripts:
			if script.id == given_id:
				self.scripts.remove(script)
				found = True
				break

		if not found:
			raise ScriptError("Given script ID not stored by handler object")

	def remove_script(self, script_object):
		script_object.exec_job_handle.remove()
		self.scripts.remove(script_object)

	def close(self):
		self.scheduler.shutdown(wait=True) #waits for all scripts to finish

class GUI:
	ICON_FILEPATH = "ACES_icon.ico"

	instances = []
	child_window_instances = []

	def __init__(self):
		self.instances.append(self)
		self.cache_file = CacheFile("aces_memory.cache")
		self.handler = Handler()
		self.selected_filepath = None

		self.window = tk.Tk()
		self.window.title("ACES Interface")
		self.window.iconbitmap(self.ICON_FILEPATH)
		#self.window.geometry('300x100')

		self.window.protocol("WM_DELETE_WINDOW", self.destroy)
		self.window.bind('<Escape>', lambda e: self.destroy())

		self.__build_menu()

		self.parent_frame = tk.Frame(self.window)
		self.parent_frame.grid(column=0, row=0)

		self.tab_control = ttk.Notebook(self.parent_frame)
		self.tab_control.pack(expand=1, fill="both")

		self.__build_main_frame()
		self.__build_jobview_frame()

		self.load_cache()

	def __build_menu(self):
		self.menubar = tk.Menu(self.window)

		self.filemenu = tk.Menu(self.menubar, tearoff=0)
		self.filemenu.add_command(label="Show cache details", command=self.show_cache_details)
		self.filemenu.add_command(label="Exit", command=self.destroy)
		self.menubar.add_cascade(label="File", menu=self.filemenu)

		self.optionsmenu = tk.Menu(self.menubar, tearoff=0)
		self.optionsmenu.add_command(label="Hide", command=self.hide)
		self.menubar.add_cascade(label="Options", menu=self.optionsmenu)

		self.helpmenu = tk.Menu(self.menubar, tearoff=0)
		self.helpmenu.add_command(label="About", command=self.show_about)
		self.helpmenu.add_command(label="Help", command=self.show_help)
		self.menubar.add_cascade(label="Assistance", menu=self.helpmenu)

		self.window.config(menu=self.menubar)

	def __build_main_frame(self):
		self.main_frame = tk.Frame(self.tab_control)
		self.tab_control.add(self.main_frame, text='Schedule')

		self.script_frame = tk.Frame(self.main_frame)
		self.script_frame.grid(column=0, row=0)

		self.script_tab = ttk.Notebook(self.script_frame)
		self.script_tab.pack(expand=1, fill="both")


		self.script_select_frame = tk.Frame(self.script_tab)
		self.script_tab.add(self.script_select_frame, text='Select file')

		self.filepath_label = tk.Label(self.script_select_frame, text="No script selected")
		self.filepath_label.grid(column=0,row=0)
		
		self.open_button = tk.Button(self.script_select_frame, text="Open Python script from file", command=self.open_file_dialog)
		self.open_button.grid(column=0,row=1)


		self.cmd_type_frame = tk.Frame(self.script_tab)
		self.script_tab.add(self.cmd_type_frame, text='Type command')

		self.cmd_label = tk.Label(self.cmd_type_frame, text="Enter a command line argument for execution:")
		self.cmd_label.pack(anchor="center")

		self.cmd_var = tk.StringVar()
		self.cmd_entry = tk.Entry(self.cmd_type_frame, textvariable = self.cmd_var)
		self.cmd_entry.pack(anchor="center")

		#self.cmd_button = tk.Button(self.cmd_type_frame, text="Open script from file", command=self.open_file_dialog)
		#self.cmd_button.grid(column=0,row=1)


		self.tab_title_label = tk.Label(self.main_frame, text="Select the type of script schedule needed:")
		self.tab_title_label.grid(column=0,row=1,pady=20)


		self.schedule_tab_frame = tk.Frame(self.main_frame)
		self.schedule_tab_frame.grid(column=0, row=2)

		self.schedule_tab = ttk.Notebook(self.schedule_tab_frame)
		self.schedule_tab.pack(expand=1, fill="both")

		self.dated_tab = tk.Frame(self.schedule_tab)
		self.schedule_tab.add(self.dated_tab, text='Dated')
		self.interval_tab = tk.Frame(self.schedule_tab)
		self.schedule_tab.add(self.interval_tab, text='Interval')
		self.cron_tab = tk.Frame(self.schedule_tab)
		self.schedule_tab.add(self.cron_tab, text='Cron')

		self.__populate_dated_tab()
		self.__populate_interval_tab()
		self.__populate_cron_tab()

	def __populate_dated_tab(self):
		self.dated_label0 = tk.Label(self.dated_tab, text="Year")
		self.dated_label0.grid(column=0,row=0)

		self.dated_year = tk.IntVar()
		self.dated_entry0 = tk.Entry(self.dated_tab, textvariable = self.dated_year)
		self.dated_entry0.grid(column=1,row=0)

		self.dated_label1 = tk.Label(self.dated_tab, text="Month")
		self.dated_label1.grid(column=0,row=1)

		self.dated_month = tk.IntVar()
		self.dated_entry1 = tk.Entry(self.dated_tab, textvariable = self.dated_month)
		self.dated_entry1.grid(column=1,row=1)

		self.dated_label2 = tk.Label(self.dated_tab, text="Date")
		self.dated_label2.grid(column=0,row=2)

		self.dated_date = tk.IntVar()
		self.dated_entry2 = tk.Entry(self.dated_tab, textvariable = self.dated_date)
		self.dated_entry2.grid(column=1,row=2)

		self.dated_label3 = tk.Label(self.dated_tab, text="Hour")
		self.dated_label3.grid(column=0,row=3)

		self.dated_hour = tk.IntVar()
		self.dated_entry3 = tk.Entry(self.dated_tab, textvariable = self.dated_hour)
		self.dated_entry3.grid(column=1,row=3)

		self.dated_label4 = tk.Label(self.dated_tab, text="Minute")
		self.dated_label4.grid(column=0,row=4)

		self.dated_minute = tk.IntVar()
		self.dated_entry4 = tk.Entry(self.dated_tab, textvariable = self.dated_minute)
		self.dated_entry4.grid(column=1,row=4)

		self.dated_label5 = tk.Label(self.dated_tab, text="Second")
		self.dated_label5.grid(column=0,row=5)

		self.dated_second = tk.IntVar()
		self.dated_entry5 = tk.Entry(self.dated_tab, textvariable = self.dated_second)
		self.dated_entry5.grid(column=1,row=5)

		self.dated_sbutton = tk.Button(self.dated_tab, text="Schedule dated script", command=self.schedule_dated_script)
		self.dated_sbutton.grid(column=0,row=6,columnspan=2)

	def __populate_interval_tab(self):
		self.interval_label0 = tk.Label(self.interval_tab, text="Days")
		self.interval_label0.grid(column=0,row=0)

		self.interval_days = tk.IntVar()
		self.interval_entry0 = tk.Entry(self.interval_tab, textvariable = self.interval_days)
		self.interval_entry0.grid(column=1,row=0)

		self.interval_label1 = tk.Label(self.interval_tab, text="Hours")
		self.interval_label1.grid(column=0,row=1)

		self.interval_hours = tk.IntVar()
		self.interval_entry1 = tk.Entry(self.interval_tab, textvariable = self.interval_hours)
		self.interval_entry1.grid(column=1,row=1)

		self.interval_label2 = tk.Label(self.interval_tab, text="Minutes")
		self.interval_label2.grid(column=0,row=2)

		self.interval_minutes = tk.IntVar()
		self.interval_entry2 = tk.Entry(self.interval_tab, textvariable = self.interval_minutes)
		self.interval_entry2.grid(column=1,row=2)

		self.interval_label3 = tk.Label(self.interval_tab, text="Seconds")
		self.interval_label3.grid(column=0,row=3)

		self.interval_seconds = tk.IntVar()
		self.interval_entry3 = tk.Entry(self.interval_tab, textvariable = self.interval_seconds)
		self.interval_entry3.grid(column=1,row=3)

		self.interval_sbutton = tk.Button(self.interval_tab, text="Schedule interval script", command=self.schedule_interval_script)
		self.interval_sbutton.grid(column=0,row=4,columnspan=2)

	def __populate_cron_tab(self):
		self.cron_label0 = tk.Label(self.cron_tab, text="Year")
		self.cron_label0.grid(column=0,row=0)

		self.cron_year = tk.StringVar()
		self.cron_entry0 = tk.Entry(self.cron_tab, textvariable = self.cron_year)
		self.cron_entry0.grid(column=1,row=0)

		self.cron_label1 = tk.Label(self.cron_tab, text="Month")
		self.cron_label1.grid(column=0,row=1)

		self.cron_month = tk.StringVar()
		self.cron_entry1 = tk.Entry(self.cron_tab, textvariable = self.cron_month)
		self.cron_entry1.grid(column=1,row=1)

		self.cron_label2 = tk.Label(self.cron_tab, text="Date")
		self.cron_label2.grid(column=0,row=2)

		self.cron_day = tk.StringVar()
		self.cron_entry2 = tk.Entry(self.cron_tab, textvariable = self.cron_day)
		self.cron_entry2.grid(column=1,row=2)

		self.cron_label3 = tk.Label(self.cron_tab, text="Hour")
		self.cron_label3.grid(column=0,row=3)

		self.cron_hour = tk.StringVar()
		self.cron_entry3 = tk.Entry(self.cron_tab, textvariable = self.cron_hour)
		self.cron_entry3.grid(column=1,row=3)

		self.cron_label4 = tk.Label(self.cron_tab, text="Minute")
		self.cron_label4.grid(column=0,row=4)

		self.cron_minute = tk.StringVar()
		self.cron_entry4 = tk.Entry(self.cron_tab, textvariable = self.cron_minute)
		self.cron_entry4.grid(column=1,row=4)

		self.cron_label5 = tk.Label(self.cron_tab, text="Second")
		self.cron_label5.grid(column=0,row=5)

		self.cron_second = tk.StringVar()
		self.cron_entry5 = tk.Entry(self.cron_tab, textvariable = self.cron_second)
		self.cron_entry5.grid(column=1,row=5)

		self.cron_sbutton = tk.Button(self.cron_tab, text="Schedule cron script", command=self.schedule_cron_script)
		self.cron_sbutton.grid(column=0,row=6,columnspan=2)

	def __build_jobview_frame(self):
		self.jobview_frame = tk.Frame(self.tab_control)
		self.tab_control.add(self.jobview_frame, text='View Jobs')

		self.jobview_lister_frame = tk.Frame(self.jobview_frame)
		self.jobview_lister_frame.pack(anchor="center")

		self.jobview_lister = tk.Listbox(self.jobview_lister_frame, height=8, width=30)
		self.jobview_lister.pack(side="left")

		self.jobview_lister_array = []
		self.jobview_lister_count = 0

		self.__populate_jobview_lister()

		self.jobview_vscrollbar = tk.Scrollbar(self.jobview_lister_frame, orient='vertical')
		self.jobview_vscrollbar.config(command=self.jobview_lister.yview)
		self.jobview_vscrollbar.pack(fill="y", side="left")

		self.jobview_button_frame = tk.Frame(self.jobview_frame)
		self.jobview_button_frame.pack(anchor="center", pady=30)

		#load the information of the task in schedule window
		self.load_button = tk.Button(self.jobview_button_frame, text="Load", command=self.load_job)
		self.load_button.grid(column=0, row=0, padx=10)

		self.remove_button = tk.Button(self.jobview_button_frame, text="Remove", command=self.remove_job)
		self.remove_button.grid(column=1, row=0, padx=10)

	def __populate_jobview_lister(self):
		if self.jobview_lister_count > 0:
			self.jobview_lister.delete(0, self.jobview_lister_count)

		self.jobview_lister_count = len(self.handler.scripts)
		self.jobview_lister_array = list(self.handler.scripts)
		for i in range(self.jobview_lister_count):
			script_object = self.handler.scripts[i]
			string = f"ID {i}: {script_object.get_name()} [{script_object.exec_type}]"
			self.jobview_lister.insert(i, string)

	def open_file_dialog(self):
		###what about execution of other language scripts like java from cmd
		self.selected_filepath = filedialog.askopenfilename(title="Select a script", filetypes=[("Python files", "*.py"), ("All files", "*.*")])
		self.update_filepath_label()

	def schedule_dated_script(self):
		year = self.dated_year.get()
		month = self.dated_month.get()
		date = self.dated_date.get()
		hour = self.dated_hour.get()
		minute = self.dated_minute.get()
		second = self.dated_second.get()
		datetime_obj = datetime(year, month, date, hour, minute, second)

		index = self.script_tab.index('current')
		if index == 0:
			script_object = ActionScript(self.selected_filepath, exec_type=f"dated:{str(datetime_obj)}")
		else:
			script_object = CmdScript(self.cmd_var.get(), exec_type=f"dated:{str(datetime_obj)}")
		
		self.handler.add_dated_script(script_object, exec_datetime=datetime_obj)
		print(f"Scheduled dated script at {datetime_obj}!")
		self.update()		

	def schedule_interval_script(self):
		days = self.interval_days.get()
		hours = self.interval_hours.get()
		minutes = self.interval_minutes.get()
		seconds = self.interval_seconds.get()

		index = self.script_tab.index('current')
		if index == 0:
			script_object = ActionScript(self.selected_filepath, exec_type="interval")
		else:
			script_object = CmdScript(self.cmd_var.get(), exec_type="interval")
		
		self.handler.add_interval_script(script_object, days=days, hours=hours, minutes=minutes, seconds=seconds)
		print("Scheduled interval script!")
		self.update()

	def schedule_cron_script(self):
		year = self.cron_year.get()
		month = self.cron_month.get()
		day = self.cron_day.get()
		hour = self.cron_hour.get()
		minute = self.cron_minute.get()
		second = self.cron_second.get()

		index = self.script_tab.index('current')
		if index == 0:
			script_object = ActionScript(self.selected_filepath, exec_type="cron")
		else:
			script_object = CmdScript(self.cmd_var.get(), exec_type="cron")
		
		self.handler.add_cron_script(script_object, year=year, month=month, day=day,
													hour=hour, minute=minute, second=second)
		print("Scheduled cron script!")
		self.update()

	###expand code
	def load_job(self):
		return_tuple = self.jobview_lister.curselection()
		if len(return_tuple) > 0:
			self.tab_control.select(self.main_frame)

			selected_index = return_tuple[0] #listbox only allows 1 selection, so tuple only has 1 index
			script_object = self.jobview_lister_array[selected_index]

			if type(script_object) is ActionScript:
				self.script_tab.select(self.script_select_frame)
			else:
				self.script_tab.select(self.cmd_type_frame)
			
			if "dated" in script_object.exec_type:
				self.schedule_tab.select(self.dated_tab)



			elif "interval" in script_object.exec_type:
				self.schedule_tab.select(self.interval_tab)

				print(script_object.exec_job_handle.kwargs)

			else: #script_object.exec_type has "cron"
				self.schedule_tab.select(self.cron_tab)



			print("Loaded job!")
		else:
			self.show_error("Please select a job to load!")

	def remove_job(self):
		return_tuple = self.jobview_lister.curselection()
		if len(return_tuple) > 0:
			selected_index = return_tuple[0]
			selected_job = self.jobview_lister_array[selected_index]
			self.handler.remove_script(selected_job)
			self.__populate_jobview_lister()
			print("Removed job!")
		else:
			self.show_error("Please select a job to remove!")

	def update_filepath_label(self):
		if self.selected_filepath:
			self.filepath_label.config(text=f"Selected File: {self.selected_filepath}")
		else:
			self.filepath_label.config(text="No script selected")

	def update(self):
		self.update_cache()
		self.__populate_jobview_lister()
		#self.update_filepath_label()
		self.window.update()

	def tk_mainloop(self):
		self.handler.mainloop()
		self.window.mainloop()

	#duration in milliseconds and frequency in Hz
	def beep(self, duration=300, frequency=450):
		winsound.Beep(frequency, duration)

	def update_cache(self):
		self.cache_file.cache["dated_year"] = self.dated_year.get()
		self.cache_file.cache["dated_month"] = self.dated_month.get()
		self.cache_file.cache["dated_date"] = self.dated_date.get()
		self.cache_file.cache["dated_hour"] = self.dated_hour.get()
		self.cache_file.cache["dated_minute"] = self.dated_minute.get()
		self.cache_file.cache["dated_second"] = self.dated_second.get()

		self.cache_file.cache["interval_days"] = self.interval_days.get()
		self.cache_file.cache["interval_hours"] = self.interval_hours.get()
		self.cache_file.cache["interval_minutes"] = self.interval_minutes.get()
		self.cache_file.cache["interval_seconds"] = self.interval_seconds.get()

		self.cache_file.cache["cron_year"] = self.cron_year.get()
		self.cache_file.cache["cron_month"] = self.cron_month.get()
		self.cache_file.cache["cron_day"] = self.cron_day.get()
		self.cache_file.cache["cron_hour"] = self.cron_hour.get()
		self.cache_file.cache["cron_minute"] = self.cron_minute.get()
		self.cache_file.cache["cron_second"] = self.cron_second.get()

		self.cache_file.cache["selected_filepath"] = self.selected_filepath
		self.cache_file.cache["cmd_var"] = self.cmd_var.get()

	def load_cache(self):
		self.dated_year.set(self.cache_file.cache["dated_year"])
		self.dated_month.set(self.cache_file.cache["dated_month"])
		self.dated_date.set(self.cache_file.cache["dated_date"])
		self.dated_hour.set(self.cache_file.cache["dated_hour"])
		self.dated_minute.set(self.cache_file.cache["dated_minute"])
		self.dated_second.set(self.cache_file.cache["dated_second"])

		self.interval_days.set(self.cache_file.cache["interval_days"])
		self.interval_hours.set(self.cache_file.cache["interval_hours"])
		self.interval_minutes.set(self.cache_file.cache["interval_minutes"])
		self.interval_seconds.set(self.cache_file.cache["interval_seconds"])

		self.cron_year.set(self.cache_file.cache["cron_year"])
		self.cron_month.set(self.cache_file.cache["cron_month"])
		self.cron_day.set(self.cache_file.cache["cron_day"])
		self.cron_hour.set(self.cache_file.cache["cron_hour"])
		self.cron_minute.set(self.cache_file.cache["cron_minute"])
		self.cron_second.set(self.cache_file.cache["cron_second"])

		self.selected_filepath = self.cache_file.cache["selected_filepath"]
		self.update_filepath_label()

		self.cmd_var.set(self.cache_file.cache["cmd_var"])

	def show_cache_details(self):
		cache_window = tk.Toplevel(self.window)
		cache_window.wm_title("Cache details")
		cache_window.iconbitmap(self.ICON_FILEPATH)
		cache_window.protocol("WM_DELETE_WINDOW", lambda: self.destroy_child_window(cache_window))
		self.child_window_instances.append(cache_window)

		tk.Label(cache_window, text="Cache file path:").grid(column=0, row=0)

		cache_fp_var = tk.StringVar()
		tk.Entry(cache_window, textvariable = cache_fp_var).grid(column=0, row=1, pady=20)
		cache_fp_var.set(self.cache_file.filepath)

		tk.Button(cache_window, text="Update cache filepath", command=lambda: cache_filepath_update(cache_fp_var)).grid(column=0, row=2)
		tk.Button(cache_window, text="Load cache", command=self.load_cache).grid(column=0, row=3)
		tk.Button(cache_window, text="Save cache", command=self.cache_file.save).grid(column=0, row=4)
		
	def cache_filepath_update(self, cache_fp_var):
		self.cache_file.filepath = cache_fp_var.get()

	def show_about(self):
		about_window = tk.Toplevel(self.window)
		about_window.wm_title("About")
		about_window.iconbitmap(self.ICON_FILEPATH)
		about_window.protocol("WM_DELETE_WINDOW", lambda: self.destroy_child_window(about_window))
		self.child_window_instances.append(about_window)

		tk.Label(about_window, text="The Amendable Controller for Execution of Scripts, ACES").pack(anchor="center")
		tk.Label(about_window, text="Developed by Jaiwanth Karthi").pack(anchor="center")
		tk.Label(about_window, text="All rights reserved - 2024 ©").pack(anchor="center")

	def show_help(self):
		help_window = tk.Toplevel(self.window)
		help_window.wm_title("Help")
		help_window.iconbitmap(self.ICON_FILEPATH)
		help_window.protocol("WM_DELETE_WINDOW", lambda: self.destroy_child_window(help_window))
		self.child_window_instances.append(help_window)

		tk.Label(help_window, text="This program is intended to allow the user to execute code scripts, \nspecifically of Python, at a scheduled time.").pack(anchor="center")
		tk.Label(help_window, text="Provide the filepath and schedule settings under the 'Schedule' panel to create the job.").pack(anchor="center")
		tk.Label(help_window, text="View and remove jobs in the 'View Jobs' panel. \nUse the 'Load' button to view the selected job's settings in the 'Schedule' panel.").pack(anchor="center")

	def show_error(self, msg="Please try again!"):
		error_window = tk.Toplevel(self.window)
		error_window.wm_title("Error")
		error_window.iconbitmap(self.ICON_FILEPATH)
		error_window.protocol("WM_DELETE_WINDOW", lambda: self.destroy_child_window(error_window))
		self.child_window_instances.append(error_window)

		tk.Label(error_window, text="An error occurred in an ACES process:").pack(anchor="center")
		tk.Label(error_window, text=msg).pack(anchor="center")

	def destroy_child_window(self, child_window):
		self.child_window_instances.remove(child_window)
		child_window.destroy()

	def hide(self):
		for child_window in tuple(self.child_window_instances):
			self.destroy_child_window(child_window)

		self.window.withdraw()
		#self.window.iconify()

		###deiconify to reverse effects of both - expand code

		time.sleep(10)
		self.window.deiconify()
		time.sleep(1)
		self.window.iconify()

	def destroy(self):
		print("---Closing window---")
		self.update_cache()
		self.cache_file.save()
		self.handler.close()

		for child_window in tuple(self.child_window_instances):
			self.destroy_child_window(child_window)
		self.window.destroy()


def main():
	window_handle = GUI()
	window_handle.tk_mainloop()

if __name__ == "__main__":
	main()
