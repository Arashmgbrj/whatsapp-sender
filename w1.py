# -*- coding: utf-8 -*-
"""
ربات ارسال پیام واتساپ با قابلیت تعویض اکانت و ارسال عکس
"""

import time
import json
import os
import threading
import random
import pandas as pd
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timedelta
import urllib.parse
import hashlib
import shutil
import subprocess
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import math
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Key, Controller as KeyboardController

# تنظیمات
SENT_MESSAGES_FILE = "sent_messages.json"
PHONE_HISTORY_FILE = "phone_history.json"
DRIVER_DIR = "drivers"
USER_DATA_DIR = "./User_Data"

class WhatsAppSenderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ربات ارسال پیام واتساپ - نسخه چند اکانته + ارسال عکس")
        self.root.geometry("900x700")
        self.root.configure(bg='#f0f0f0')
        self.mouse = MouseController()
        self.keyboard = KeyboardController()
        
        # متغیرهای کنترل
        self.driver = None
        self.is_running = False
        self.current_process = None
        self.daily_limit = 500
        self.switch_account_after = 50
        self.current_account_sent = 0
        self.image_path = None
        
        # ایجاد دایرکتوری‌های لازم
        self.setup_directories()
        
        # بارگذاری تاریخچه
        self.sent_messages = self.load_sent_messages()
        self.phone_history = self.load_phone_history()
        
        # ایجاد رابط گرافیکی با قابلیت اسکرول
        self.create_scrollable_gui()
        
        # نمایش وضعیت
        self.update_status()

    def setup_directories(self):
        """ایجاد دایرکتوری‌های لازم"""
        os.makedirs(USER_DATA_DIR, exist_ok=True)
        os.makedirs(DRIVER_DIR, exist_ok=True)

    def load_phone_history(self):
        """بارگذاری تاریخچه شماره‌ها"""
        try:
            if os.path.exists(PHONE_HISTORY_FILE):
                with open(PHONE_HISTORY_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.log(f"خطا در بارگذاری تاریخچه شماره‌ها: {e}", "error")
        return {}

    def save_phone_history(self):
        """ذخیره تاریخچه شماره‌ها"""
        try:
            with open(PHONE_HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.phone_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log(f"خطا در ذخیره تاریخچه شماره‌ها: {e}", "error")

    def load_sent_messages(self):
        """بارگذاری تاریخچه پیام‌های ارسالی"""
        try:
            if os.path.exists(SENT_MESSAGES_FILE):
                with open(SENT_MESSAGES_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except:
            pass
        return {}

    def save_sent_messages(self):
        """ذخیره تاریخچه پیام‌های ارسالی"""
        try:
            with open(SENT_MESSAGES_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.sent_messages, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log(f"خطا در ذخیره تاریخچه پیام‌ها: {e}", "error")

    def create_scrollable_gui(self):
        """ایجاد رابط گرافیکی با قابلیت اسکرول"""
        # ایجاد فریم اصلی با اسکرول بار
        main_frame = tk.Frame(self.root, bg='#f0f0f0')
        main_frame.pack(fill='both', expand=True)
        
        # ایجاد Canvas و Scrollbar
        self.canvas = tk.Canvas(main_frame, bg='#f0f0f0')
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg='#f0f0f0')
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # بسته‌بندی Canvas و Scrollbar
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # فعال‌سازی اسکرول با ماوس
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.scrollable_frame.bind("<MouseWheel>", self._on_mousewheel)
        
        # ایجاد ویجت‌ها در فریم قابل اسکرول
        self.create_widgets()

    def _on_mousewheel(self, event):
        """مدیریت اسکرول با چرخ ماوس"""
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def scroll_to_bottom(self):
        """اسکرول به پایین صفحه اصلی"""
        try:
            self.canvas.yview_moveto(1.0)
            self.root.update_idletasks()
        except Exception as e:
            print(f"خطا در اسکرول به پایین: {e}")

    def create_widgets(self):
        """ایجاد ویجت‌های رابط گرافیکی"""
        # عنوان اصلی
        title_frame = tk.Frame(self.scrollable_frame, bg='#128C7E', height=80)
        title_frame.pack(fill='x', padx=10, pady=10)
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(title_frame, text="🤖 ربات ارسال پیام واتساپ - چند اکانته + ارسال عکس", 
                              font=('Arial', 16, 'bold'), 
                              fg='white', bg='#128C7E')
        title_label.pack(expand=True)
        
        # فریم مدیریت شماره‌های تکراری
        duplicate_frame = tk.LabelFrame(self.scrollable_frame, text="🔍 مدیریت شماره‌های تکراری", 
                                      font=('Arial', 12, 'bold'),
                                      bg='#f0f0f0', padx=10, pady=10)
        duplicate_frame.pack(fill='x', pady=(0, 10))

        duplicate_btn_frame = tk.Frame(duplicate_frame, bg='#f0f0f0')
        duplicate_btn_frame.pack(fill='x', pady=5)
        
        tk.Button(duplicate_btn_frame, text="📊 مشاهده تاریخچه شماره‌ها", 
                 command=self.view_phone_history, width=20,
                 font=('Arial', 9)).pack(side='right', padx=5)
        
        tk.Button(duplicate_btn_frame, text="🧹 پاکسازی تاریخچه", 
                 command=self.clear_phone_history, width=15,
                 font=('Arial', 9), bg='#FF9500', fg='white').pack(side='right', padx=5)
        
        tk.Button(duplicate_btn_frame, text="📤 خروجی از شماره‌های ارسالی", 
                 command=self.export_sent_numbers, width=18,
                 font=('Arial', 9)).pack(side='right', padx=5)

        # برچسب آمار شماره‌ها
        self.phone_stats_label = tk.Label(duplicate_frame, 
                                        text="تعداد شماره‌های ذخیره شده: 0",
                                        font=('Arial', 9), bg='#f0f0f0')
        self.phone_stats_label.pack()

        # فریم تنظیمات پیشرفته
        advanced_frame = tk.LabelFrame(self.scrollable_frame, text="⚡ تنظیمات پیشرفته", 
                                      font=('Arial', 12, 'bold'),
                                      bg='#f0f0f0', padx=10, pady=10)
        advanced_frame.pack(fill='x', pady=(0, 10))

        # محدودیت روزانه
        limit_frame = tk.Frame(advanced_frame, bg='#f0f0f0')
        limit_frame.pack(fill='x', pady=5)
        
        tk.Label(limit_frame, text="محدودیت روزانه:", 
                font=('Arial', 10), bg='#f0f0f0').pack(side='right')
        
        self.limit_var = tk.StringVar(value=str(self.daily_limit))
        limit_entry = tk.Entry(limit_frame, textvariable=self.limit_var, 
                              width=8, font=('Arial', 10), justify='center')
        limit_entry.pack(side='right', padx=(5, 0))

        # تاخیر بین پیام‌ها
        delay_frame = tk.Frame(advanced_frame, bg='#f0f0f0')
        delay_frame.pack(fill='x', pady=5)
        
        tk.Label(delay_frame, text="تاخیر بین پیام‌ها (ثانیه):", 
                font=('Arial', 10), bg='#f0f0f0').pack(side='right')
        
        self.delay_var = tk.StringVar(value="45")
        delay_entry = tk.Entry(delay_frame, textvariable=self.delay_var, 
                              width=8, font=('Arial', 10), justify='center')
        delay_entry.pack(side='right', padx=(5, 0))

        # تعویض اکانت پس از تعداد پیام
        switch_frame = tk.Frame(advanced_frame, bg='#f0f0f0')
        switch_frame.pack(fill='x', pady=5)
        
        tk.Label(switch_frame, text="تعویض اکانت پس از (پیام):", 
                font=('Arial', 10), bg='#f0f0f0').pack(side='right')
        
        self.switch_var = tk.StringVar(value=str(self.switch_account_after))
        switch_entry = tk.Entry(switch_frame, textvariable=self.switch_var, 
                               width=8, font=('Arial', 10), justify='center')
        switch_entry.pack(side='right', padx=(5, 0))

        # فریم ورودی شماره‌ها
        numbers_frame = tk.LabelFrame(self.scrollable_frame, text="📞 لیست شماره‌ها", 
                                     font=('Arial', 12, 'bold'),
                                     bg='#f0f0f0', padx=10, pady=10)
        numbers_frame.pack(fill='x', pady=(0, 10))

        # دکمه‌های مدیریت شماره‌ها
        numbers_btn_frame = tk.Frame(numbers_frame, bg='#f0f0f0')
        numbers_btn_frame.pack(fill='x', pady=5)
        
        tk.Button(numbers_btn_frame, text="📁 بارگذاری از فایل Excel", 
                 command=self.load_numbers_from_file, width=20,
                 font=('Arial', 9)).pack(side='right', padx=5)
        
        tk.Button(numbers_btn_frame, text="📋 بارگذاری از متن", 
                 command=self.load_numbers_from_text, width=15,
                 font=('Arial', 9)).pack(side='right', padx=5)
        
        tk.Button(numbers_btn_frame, text="🔍 فیلتر تکراری‌ها", 
                 command=self.filter_duplicates, width=15,
                 font=('Arial', 9)).pack(side='right', padx=5)

        # جعبه متن برای شماره‌ها
        self.numbers_text = tk.Text(numbers_frame, height=6, font=('Arial', 10),
                                   wrap='word')
        self.numbers_text.pack(fill='both', expand=True)
        
        # برچسب راهنما
        help_label = tk.Label(numbers_frame, 
                             text="شماره‌ها را با کاما جدا کنید یا از فایل Excel بارگذاری کنید",
                             font=('Arial', 8), fg='gray', bg='#f0f0f0')
        help_label.pack()

        # فریم پیام
        message_frame = tk.LabelFrame(self.scrollable_frame, text="✉️ متن پیام", 
                                     font=('Arial', 12, 'bold'),
                                     bg='#f0f0f0', padx=10, pady=10)
        message_frame.pack(fill='x', pady=(0, 10))

        self.message_text = tk.Text(message_frame, height=5, font=('Arial', 11),
                                   wrap='word')
        self.message_text.pack(fill='both', expand=True)
        self.message_text.insert('1.0', "سلام! امیدوارم حالتون خوب باشه 😊\n")

        # فریم عکس
        image_frame = tk.LabelFrame(self.scrollable_frame, text="🖼️ تصویر پیام", 
                                   font=('Arial', 12, 'bold'),
                                   bg='#f0f0f0', padx=10, pady=10)
        image_frame.pack(fill='x', pady=(0, 10))

        image_btn_frame = tk.Frame(image_frame, bg='#f0f0f0')
        image_btn_frame.pack(fill='x', pady=5)
        
        self.select_image_btn = tk.Button(image_btn_frame, text="📷 انتخاب عکس", 
                                        command=self.select_image, width=15,
                                        font=('Arial', 9))
        self.select_image_btn.pack(side='right', padx=5)
        
        self.remove_image_btn = tk.Button(image_btn_frame, text="❌ حذف عکس", 
                                        command=self.remove_image, width=12,
                                        font=('Arial', 9))
        self.remove_image_btn.pack(side='right', padx=5)
        
        # برچسب نمایش مسیر عکس
        self.image_label = tk.Label(image_frame, text="هیچ عکسی انتخاب نشده است", 
                                   font=('Arial', 9), fg='gray', bg='#f0f0f0',
                                   wraplength=800, justify='right')
        self.image_label.pack(fill='x', pady=5)

        # فریم وضعیت
        status_frame = tk.LabelFrame(self.scrollable_frame, text="📊 وضعیت عملیات", 
                                    font=('Arial', 12, 'bold'),
                                    bg='#f0f0f0', padx=10, pady=10)
        status_frame.pack(fill='x', pady=(0, 10))

        # پیشرفت
        self.progress = ttk.Progressbar(status_frame, orient="horizontal", 
                                       length=860, mode="determinate")
        self.progress.pack(pady=5)

        # برچسب وضعیت
        self.status_label = tk.Label(status_frame, text="آماده", 
                                    font=('Arial', 10), bg='#f0f0f0')
        self.status_label.pack()

        # آمار
        stats_frame = tk.Frame(status_frame, bg='#f0f0f0')
        stats_frame.pack(fill='x', pady=5)
        
        self.sent_label = tk.Label(stats_frame, text="ارسال شده امروز: 0", 
                                  font=('Arial', 9), bg='#f0f0f0')
        self.sent_label.pack(side='right', padx=20)
        
        self.remaining_label = tk.Label(stats_frame, text="مانده: 0", 
                                       font=('Arial', 9), bg='#f0f0f0')
        self.remaining_label.pack(side='right', padx=20)
        
        self.success_label = tk.Label(stats_frame, text="موفق: 0", 
                                     font=('Arial', 9), bg='#f0f0f0')
        self.success_label.pack(side='right', padx=20)
        
        self.account_label = tk.Label(stats_frame, text="اکانت فعلی: 0", 
                                     font=('Arial', 9), bg='#f0f0f0')
        self.account_label.pack(side='right', padx=20)

        # لاگ عملیات
        log_frame = tk.LabelFrame(self.scrollable_frame, text="📝 گزارش عملیات", 
                                 font=('Arial', 12, 'bold'),
                                 bg='#f0f0f0', padx=10, pady=10)
        log_frame.pack(fill='x', pady=(0, 10))

        # جعبه متن لاگ
        self.log_text = tk.Text(log_frame, height=8, font=('Arial', 9),
                               wrap='word')
        self.log_text.pack(fill='both', expand=True)
        
        # اسکرول بار برای لاگ
        log_scrollbar = tk.Scrollbar(self.log_text)
        log_scrollbar.pack(side='right', fill='y')
        self.log_text.config(yscrollcommand=log_scrollbar.set)
        log_scrollbar.config(command=self.log_text.yview)

        # فریم دکمه‌ها
        buttons_frame = tk.Frame(self.scrollable_frame, bg='#f0f0f0')
        buttons_frame.pack(fill='x', pady=10)

        # دکمه اسکرول به پایین صفحه اصلی
        self.scroll_btn = tk.Button(buttons_frame, text="⬇️ اسکرول به پایین صفحه", 
                                   command=self.scroll_to_bottom, 
                                   width=20, font=('Arial', 10), bg='#007AFF', fg='white')
        self.scroll_btn.pack(side='right', padx=5)

        # دکمه‌های اصلی
        self.download_btn = tk.Button(buttons_frame, text="🧩 دانلود WebDriver", 
                                     command=self.download_driver, width=18,
                                     font=('Arial', 10))
        self.download_btn.pack(side='right', padx=5)

        self.kill_chrome_btn = tk.Button(buttons_frame, text="🔴 بستن کروم", 
                                       command=self.kill_chrome_processes, width=15,
                                       font=('Arial', 10), bg='#FF9500', fg='white')
        self.kill_chrome_btn.pack(side='right', padx=5)

        self.start_btn = tk.Button(buttons_frame, text="🚀 شروع ارسال", 
                                  command=self.start_sending, width=15,
                                  font=('Arial', 10), bg='#25D366', fg='white')
        self.start_btn.pack(side='right', padx=5)

        self.stop_btn = tk.Button(buttons_frame, text="⏹ توقف", 
                                 command=self.stop_sending, width=12,
                                 font=('Arial', 10), bg='#FF3B30', fg='white',
                                 state='disabled')
        self.stop_btn.pack(side='right', padx=5)

        self.clear_btn = tk.Button(buttons_frame, text="🧹 پاکسازی گزارش", 
                                  command=self.clear_log, width=15,
                                  font=('Arial', 10))
        self.clear_btn.pack(side='right', padx=5)
        
        # به روز رسانی آمار شماره‌ها
        self.update_phone_stats()

    def update_phone_stats(self):
        """به روز رسانی آمار شماره‌ها"""
        total_numbers = sum(len(numbers) for numbers in self.phone_history.values())
        self.phone_stats_label.config(text=f"تعداد شماره‌های ذخیره شده: {total_numbers}")

    def is_duplicate_phone(self, phone_number):
        """بررسی تکراری بودن شماره"""
        for date, numbers in self.phone_history.items():
            if phone_number in numbers:
                return True
        return False

    def add_phone_to_history(self, phone_number):
        """افزودن شماره به تاریخچه"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        if today not in self.phone_history:
            self.phone_history[today] = []
        
        if phone_number not in self.phone_history[today]:
            self.phone_history[today].append(phone_number)
        
        self.save_phone_history()
        self.update_phone_stats()

    def view_phone_history(self):
        """مشاهده تاریخچه شماره‌ها"""
        history_dialog = tk.Toplevel(self.root)
        history_dialog.title("تاریخچه شماره‌های ارسالی")
        history_dialog.geometry("600x500")
        history_dialog.transient(self.root)
        
        # فریم اصلی
        main_frame = tk.Frame(history_dialog)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # جعبه متن برای نمایش تاریخچه
        text_widget = tk.Text(main_frame, wrap='word', font=('Arial', 9))
        text_widget.pack(fill='both', expand=True, pady=5)
        
        # اسکرول بار
        scrollbar = tk.Scrollbar(text_widget)
        scrollbar.pack(side='right', fill='y')
        text_widget.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=text_widget.yview)
        
        # نمایش تاریخچه
        if not self.phone_history:
            text_widget.insert('end', "هیچ شماره‌ای در تاریخچه وجود ندارد.\n")
        else:
            total_numbers = 0
            for date in sorted(self.phone_history.keys(), reverse=True):
                numbers = self.phone_history[date]
                total_numbers += len(numbers)
                text_widget.insert('end', f"\n📅 تاریخ: {date}\n")
                text_widget.insert('end', f"📞 تعداد: {len(numbers)} شماره\n")
                text_widget.insert('end', "-" * 50 + "\n")
                
                for i, phone in enumerate(numbers, 1):
                    text_widget.insert('end', f"{i}. {phone}\n")
                text_widget.insert('end', "\n")
            
            text_widget.insert('1.0', f"📊 جمع کل: {total_numbers} شماره در تاریخچه\n\n")
        
        text_widget.config(state='disabled')
        
        # دکمه اسکرول به پایین برای دیالوگ تاریخچه
        scroll_btn = tk.Button(main_frame, text="⬇️ اسکرول به پایین", 
                              command=lambda: text_widget.see('end'),
                              width=15)
        scroll_btn.pack(pady=5)

    def clear_phone_history(self):
        """پاکسازی تاریخچه شماره‌ها"""
        if messagebox.askyesno("تأیید", "آیا از پاکسازی تمام تاریخچه شماره‌ها مطمئنید؟"):
            try:
                if os.path.exists(PHONE_HISTORY_FILE):
                    os.remove(PHONE_HISTORY_FILE)
                self.phone_history = {}
                self.update_phone_stats()
                self.log("✅ تاریخچه شماره‌ها پاکسازی شد", "success")
                messagebox.showinfo("موفق", "تاریخچه شماره‌ها با موفقیت پاکسازی شد.")
            except Exception as e:
                self.log(f"❌ خطا در پاکسازی تاریخچه: {e}", "error")

    def export_sent_numbers(self):
        """خروجی گرفتن از شماره‌های ارسالی"""
        try:
            if not self.phone_history:
                messagebox.showinfo("اطلاع", "هیچ شماره‌ای در تاریخچه وجود ندارد.")
                return
            
            # ایجاد DataFrame از تمام شماره‌ها
            all_numbers = []
            for date, numbers in self.phone_history.items():
                for phone in numbers:
                    all_numbers.append({'تاریخ': date, 'شماره': phone})
            
            df = pd.DataFrame(all_numbers)
            
            # ذخیره در فایل Excel
            file_path = filedialog.asksaveasfilename(
                title="ذخیره فایل Excel",
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
            )
            
            if file_path:
                df.to_excel(file_path, index=False)
                self.log(f"✅ فایل Excel با {len(all_numbers)} شماره ذخیره شد: {file_path}", "success")
                messagebox.showinfo("موفق", f"فایل Excel با {len(all_numbers)} شماره ذخیره شد.")
                
        except Exception as e:
            self.log(f"❌ خطا در خروجی گرفتن: {e}", "error")
            messagebox.showerror("خطا", f"خطا در خروجی گرفتن:\n{e}")

    def filter_duplicates(self):
        """فیلتر کردن شماره‌های تکراری از لیست ورودی"""
        numbers_text = self.numbers_text.get('1.0', 'end').strip()
        if not numbers_text:
            messagebox.showwarning("هشدار", "لطفاً ابتدا شماره‌ها را وارد کنید")
            return
        
        raw_numbers = [num.strip() for num in numbers_text.split(',') if num.strip()]
        unique_numbers = []
        duplicates_found = 0
        
        for phone in raw_numbers:
            validated_phone = self.validate_phone_number(phone)
            if validated_phone:
                if not self.is_duplicate_phone(validated_phone):
                    unique_numbers.append(validated_phone)
                else:
                    duplicates_found += 1
        
        # به روز رسانی لیست شماره‌ها
        self.numbers_text.delete('1.0', 'end')
        if unique_numbers:
            self.numbers_text.insert('1.0', ', '.join(unique_numbers))
        
        self.log(f"🔍 فیلتر تکراری‌ها: {duplicates_found} شماره تکراری حذف شد", "success")
        messagebox.showinfo("نتیجه", f"{duplicates_found} شماره تکراری حذف شد.\n{len(unique_numbers)} شماره منحصربفرد باقی ماند.")

    def select_image(self):
        """انتخاب عکس برای ارسال"""
        file_path = filedialog.askopenfilename(
            title="انتخاب عکس",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.gif *.bmp"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            self.image_path = file_path
            file_name = os.path.basename(file_path)
            self.image_label.config(text=f"عکس انتخاب شده: {file_name}", fg='green')
            self.log(f"✅ عکس انتخاب شد: {file_name}")

    def remove_image(self):
        """حذف عکس انتخاب شده"""
        self.image_path = None
        self.image_label.config(text="هیچ عکسی انتخاب نشده است", fg='gray')
        self.log("🗑️ عکس حذف شد")

    def log(self, message, message_type="info"):
        """ثبت پیام در لاگ"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert('end', f"[{timestamp}] {message}\n")
        
        # اسکرول خودکار به پایین لاگ
        self.log_text.see('end')
        
        # همچنین اسکرول کلی صفحه به پایین
        self.scroll_to_bottom()
        
        self.root.update_idletasks()

    def clear_log(self):
        """پاکسازی لاگ"""
        self.log_text.delete('1.0', 'end')

    def update_status(self, message="آماده"):
        """به‌روزرسانی وضعیت"""
        self.status_label.config(text=f"وضعیت: {message}")
        
        # به‌روزرسانی آمار
        today_count = self.get_today_sent_count()
        remaining = self.daily_limit - today_count
        
        self.sent_label.config(text=f"ارسال شده امروز: {today_count}")
        self.remaining_label.config(text=f"مانده: {remaining}")
        self.account_label.config(text=f"اکانت فعلی: {self.current_account_sent}")
        self.root.update_idletasks()

    def get_today_sent_count(self):
        """دریافت تعداد پیام‌های ارسالی امروز"""
        today = datetime.now().strftime("%Y-%m-%d")
        return len(self.sent_messages.get(today, []))

    def save_sent_message(self, phone_number):
        """ذخیره پیام ارسالی"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            
            if today not in self.sent_messages:
                self.sent_messages[today] = []
            
            if phone_number not in self.sent_messages[today]:
                self.sent_messages[today].append(phone_number)
            
            self.save_sent_messages()
            
            # همچنین شماره را به تاریخچه اضافه می‌کنیم
            self.add_phone_to_history(phone_number)
            
        except Exception as e:
            self.log(f"خطا در ذخیره تاریخچه: {e}", "error")

    def can_send_message(self, phone_number):
        """بررسی امکان ارسال پیام"""
        # بررسی محدودیت روزانه
        today_count = self.get_today_sent_count()
        if today_count >= self.daily_limit:
            return False
        
        # بررسی تکراری نبودن شماره در امروز
        today = datetime.now().strftime("%Y-%m-%d")
        if phone_number in self.sent_messages.get(today, []):
            return False
        
        # بررسی تکراری بودن در کل تاریخچه
        if self.is_duplicate_phone(phone_number):
            return False
        
        return True

    def kill_chrome_processes(self):
        """کشت کردن تمام فرآیندهای کروم"""
        try:
            if os.name == 'nt':  # Windows
                os.system('taskkill /f /im chrome.exe >nul 2>&1')
                os.system('taskkill /f /im chromedriver.exe >nul 2>&1')
            else:  # Linux/Mac
                os.system('pkill -f chrome >/dev/null 2>&1')
                os.system('pkill -f chromedriver >/dev/null 2>&1')
            time.sleep(2)
            self.log("✅ تمام فرآیندهای کروم بسته شدند", "success")
        except Exception as e:
            self.log(f"⚠️ خطا در بستن کروم: {e}", "warning")

    def ensure_driver_binary(self):
        """
        بررسی وجود chromedriver در پوشه drivers
        """
        os.makedirs(DRIVER_DIR, exist_ok=True)
        binary_name = "chromedriver.exe" if os.name == "nt" else "chromedriver"
        local_path = os.path.join(DRIVER_DIR, binary_name)

        if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
            return local_path

        try:
            self.log("⬇️ در حال دانلود WebDriver...")
            installed_path = ChromeDriverManager().install()
            shutil.copy(installed_path, local_path)
            self.log(f"✅ WebDriver دانلود و ذخیره شد: {local_path}", "success")
            return local_path
        except Exception as e:
            self.log(f"❌ خطا در دانلود WebDriver: {e}", "error")
            return None

    def download_driver(self):
        """دانلود وب‌درایور"""
        threading.Thread(target=self._download_driver, daemon=True).start()

    def _download_driver(self):
        """دانلود وب‌درایور در ترد جداگانه"""
        self.download_btn.config(state='disabled')
        self.log("🔧 در حال بررسی/دانلود WebDriver...")
        
        try:
            self.kill_chrome_processes()
            driver_path = self.ensure_driver_binary()
            if driver_path:
                self.log(f"✅ WebDriver آماده است: {driver_path}", "success")
                messagebox.showinfo("موفق", f"WebDriver آماده است:\n{driver_path}")
            else:
                self.log("❌ دانلود WebDriver ناموفق بود", "error")
                messagebox.showerror("خطا", "دانلود WebDriver ناموفق بود.")
        except Exception as e:
            self.log(f"❌ خطا در نصب WebDriver: {e}", "error")
            messagebox.showerror("خطا", f"خطا در نصب WebDriver:\n{e}")
        finally:
            self.download_btn.config(state='normal')

    def setup_stealth_driver(self):
        """تنظیم درایور با قابلیت ضد تشخیص (بدون پروکسی)"""
        driver_binary = self.ensure_driver_binary()
        if not driver_binary:
            self.log("❌ WebDriver یافت نشد. لطفاً ابتدا آن را دانلود کنید.", "error")
            return None

        options = Options()
        
        # تنظیمات پایه برای جلوگیری از crash
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--remote-debugging-port=0")
        
        # تنظیمات استیلث
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-extensions")
        options.add_argument(f"--user-data-dir={os.path.abspath(USER_DATA_DIR)}")
        options.add_argument("--profile-directory=Default")
        options.add_argument("--start-maximized")
        
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        ]
        options.add_argument(f"--user-agent={random.choice(user_agents)}")
        
        options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        options.add_experimental_option('useAutomationExtension', False)
        
        options.add_experimental_option("prefs", {
            "profile.default_content_setting_values.notifications": 2,
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
        })
        
        try:
            service = Service(executable_path=driver_binary)
            driver = webdriver.Chrome(service=service, options=options)
            
            # اسکریپت‌های ضد تشخیص
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            driver.execute_script("window.chrome = {runtime: {}};")
            
            self.log("✅ درایور با موفقیت راه‌اندازی شد", "success")
            return driver
            
        except Exception as e:
            self.log(f"❌ خطا در راه‌اندازی درایور: {e}", "error")
            return None

    def load_numbers_from_file(self):
        """بارگذاری شماره‌ها از فایل Excel"""
        try:
            file_path = filedialog.askopenfilename(
                title="انتخاب فایل Excel",
                filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
            )
            
            if file_path:
                df = pd.read_excel(file_path)
                numbers = []
                
                for col in df.columns:
                    if any(keyword in str(col).lower() for keyword in ['phone', 'mobile', 'number', 'شماره']):
                        numbers = df[col].dropna().astype(str).tolist()
                        break
                
                if numbers:
                    self.numbers_text.delete('1.0', 'end')
                    self.numbers_text.insert('1.0', ', '.join(numbers))
                    self.log(f"✅ {len(numbers)} شماره از فایل بارگذاری شد", "success")
                    
                else:
                    messagebox.showwarning("هشدار", "ستون شماره تلفن یافت نشد")
                    
        except Exception as e:
            self.log(f"❌ خطا در بارگذاری فایل: {e}", "error")
            messagebox.showerror("خطا", f"خطا در بارگذاری فایل:\n{e}")

    def load_numbers_from_text(self):
        """بارگذاری شماره‌ها از طریق دیالوگ متن"""
        text_dialog = tk.Toplevel(self.root)
        text_dialog.title("ورود شماره‌ها")
        text_dialog.geometry("500x400")
        text_dialog.transient(self.root)
        text_dialog.grab_set()
        
        tk.Label(text_dialog, text="شماره‌ها را وارد کنید (هر خط یک شماره):", 
                font=('Arial', 11)).pack(padx=10, pady=10)
        
        text_widget = tk.Text(text_dialog, height=15, font=('Arial', 10))
        text_widget.pack(fill='both', expand=True, padx=10, pady=5)
        
        def save_numbers():
            numbers_text = text_widget.get('1.0', 'end').strip()
            numbers = [num.strip() for num in numbers_text.split('\n') if num.strip()]
            
            if numbers:
                self.numbers_text.delete('1.0', 'end')
                self.numbers_text.insert('1.0', ', '.join(numbers))
                self.log(f"✅ {len(numbers)} شماره وارد شد", "success")
            
            text_dialog.destroy()
        
        btn_frame = tk.Frame(text_dialog)
        btn_frame.pack(fill='x', padx=10, pady=10)
        
        tk.Button(btn_frame, text="ذخیره", command=save_numbers, 
                 width=10, bg='#25D366', fg='white').pack(side='left')
        tk.Button(btn_frame, text="انصراف", command=text_dialog.destroy, 
                 width=10).pack(side='left', padx=5)

    def validate_phone_number(self, phone):
        """اعتبارسنجی شماره تلفن"""
        try:
            cleaned_phone = ''.join(filter(str.isdigit, str(phone)))
            
            if len(cleaned_phone) < 10:
                return None
            
            if cleaned_phone.startswith('0'):
                cleaned_phone = '98' + cleaned_phone[1:]
            elif cleaned_phone.startswith('+98'):
                cleaned_phone = cleaned_phone[1:]
            elif not cleaned_phone.startswith('98'):
                cleaned_phone = '98' + cleaned_phone
            
            return cleaned_phone
        except:
            return None

    def perform_logout(self):
        """انجام لاگ‌اوت از واتساپ"""
        try:
            self.log("🚪 در حال خروج از اکانت فعلی...")
            
            # کلیک روی منو
            menu_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//div[@title="منو"]'))
            )
            menu_button.click()
            time.sleep(2)
            
            # کلیک روی گزینه خروج
            logout_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//div[@role="button"]//div[contains(text(), "خروج")]'))
            )
            logout_button.click()
            time.sleep(2)
            
            # تأیید خروج
            confirm_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//div[@role="button"]//div[contains(text(), "تأیید")]'))
            )
            confirm_button.click()
            
            self.log("✅ خروج از اکانت با موفقیت انجام شد", "success")
            return True
            
        except Exception as e:
            self.log(f"⚠️ خطا در لاگ‌اوت: {e} - استفاده از روش جایگزین", "warning")
            return self.alternative_logout()

    def alternative_logout(self):
        """روش جایگزین برای لاگ‌اوت"""
        try:
            # پاک کردن کوکی‌ها و localStorage
            self.driver.delete_all_cookies()
            self.driver.execute_script("window.localStorage.clear();")
            self.driver.execute_script("window.sessionStorage.clear();")
            
            # بازگشت به صفحه لاگین
            self.driver.get("https://web.whatsapp.com")
            time.sleep(3)
            
            self.log("✅ پاکسازی نشست با روش جایگزین انجام شد", "success")
            return True
        except Exception as e:
            self.log(f"❌ خطا در روش جایگزین: {e}", "error")
            return False

    def wait_for_new_login(self):
        """منتظر ماندن برای لاگین با اکانت جدید"""
        self.log("🔄 منتظر اسکن QR کد با اکانت جدید...")
        
        # نمایش دیالوگ انتظار
        wait_dialog = tk.Toplevel(self.root)
        wait_dialog.title("تعویض اکانت")
        wait_dialog.geometry("400x200")
        wait_dialog.transient(self.root)
        wait_dialog.grab_set()
        
        tk.Label(wait_dialog, text="🔄 لطفاً با اکانت جدید QR کد را اسکن کنید", 
                font=('Arial', 12, 'bold')).pack(pady=20)
        
        tk.Label(wait_dialog, text="پس از اسکن، دکمه 'ادامه' را بزنید", 
                font=('Arial', 10)).pack(pady=10)
        
        continue_var = tk.BooleanVar(value=False)
        
        def continue_process():
            continue_var.set(True)
            wait_dialog.destroy()
        
        tk.Button(wait_dialog, text="ادامه", command=continue_process,
                 bg='#25D366', fg='white', font=('Arial', 12), width=15).pack(pady=20)
        
        # منتظر ماندن برای تأیید کاربر
        self.root.wait_window(wait_dialog)
        
        if continue_var.get():
            self.log("✅ کاربر آماده است - بررسی لاگین...")
            
            # بررسی لاگین موفق
            try:
                WebDriverWait(self.driver, 60).until(
                    EC.presence_of_element_located((By.XPATH, '//div[@id="side"]'))
                )
                self.log("✅ لاگین با اکانت جدید موفقیت‌آمیز بود", "success")
                self.current_account_sent = 0  # ریست کردن شمارنده اکانت فعلی
                return True
            except:
                self.log("❌ لاگین انجام نشده است", "error")
                return False
        
        return False

    def smooth_move(self, x1, y1, duration=1.4):
        """حرکت نرم و سریع ماوس بین دو نقطه با الگوریتم بهبود یافته"""
        try:
            x0, y0 = self.mouse.position
            
            # محاسبه فاصله برای تنظیم هوشمند duration
            distance = math.sqrt((x1 - x0)**2 + (y1 - y0)**2)
            
            # تنظیم هوشمند مدت زمان بر اساس فاصله
            if distance < 100:
                duration = 0.3
            elif distance < 300:
                duration = 0.6
            elif distance < 600:
                duration = 1.0
            else:
                duration = 1.4
            
            steps = max(20, int(duration * 200))  # حداقل 20 گام
            
            for i in range(steps + 1):
                t = i / steps
                
                # تابع easing برای حرکت طبیعی‌تر
                # easeOutCubic برای حرکت سریع در ابتدا و نرم در انتها
                ease = 1 - (1 - t) ** 3
                
                # اضافه کردن لرزش بسیار جزئی برای طبیعی‌تر شدن حرکت
                jitter_x = random.uniform(-0.5, 0.5) if i % 3 == 0 else 0
                jitter_y = random.uniform(-0.5, 0.5) if i % 4 == 0 else 0
                
                x = x0 + (x1 - x0) * ease + jitter_x
                y = y0 + (y1 - y0) * ease + jitter_y
                
                self.mouse.position = (int(x), int(y))
                
                # تنظیم هوشمند تأخیر بر اساس سرعت
                if t < 0.8:
                    time.sleep(0.002)  # سریع در بخش ابتدایی
                else:
                    time.sleep(0.004)  # کندتر در انتها برای دقت بیشتر
            
            # اطمینان از رسیدن به نقطه نهایی
            final_x, final_y = self.mouse.position
            if abs(final_x - x1) > 2 or abs(final_y - y1) > 2:
                self.mouse.position = (x1, y1)
                time.sleep(0.1)
                
        except Exception as e:
            print(f"خطا در حرکت ماوس: {e}")
            # حرکت مستقیم در صورت بروز خطا
            self.mouse.position = (x1, y1)
    
    def human_like_click(self, x, y, click_delay=0.1):
        """کلیک طبیعی شبیه به انسان"""
        try:
            # حرکت نرم به سمت نقطه
            self.smooth_move(x, y, duration=0.8)
            
            # تأخیر کوتاه قبل از کلیک
            time.sleep(random.uniform(0.05, 0.15))
            
            # فشار دادن دکمه
            self.mouse.press(Button.left)
            time.sleep(random.uniform(0.02, 0.05))  # زمان نگه داشتن دکمه
            
            # رها کردن دکمه
            self.mouse.release(Button.left)
            
            # تأخیر پس از کلیک
            time.sleep(click_delay)
            
        except Exception as e:
            print(f"خطا در کلیک: {e}")

    def send_message_to_number(self, phone_number, message):
        """ارسال پیام به یک شماره"""
        try:
            if not self.can_send_message(phone_number):
                self.log(f"⚠️ پیام به {phone_number} حذف شد (محدودیت)", "warning")
                return False
            
            encoded_message = urllib.parse.quote(message)
            url = f"https://web.whatsapp.com/send?phone={phone_number}&text={encoded_message}"
            
            self.driver.get(url)
            time.sleep(random.uniform(7, 12))
            
            # اینتر زدن بعد از لود صفحه
            try:
                self.driver.find_element(By.XPATH,'//*[@id="main"]/footer/div[1]/div/span/div/div[2]/div/div[4]/div/span/div/div/div[1]/div[1]/span').click()
            except:
                self.driver.find_element(By.XPATH,'//*[@id="main"]/footer/div[1]/div/span/div/div[2]/div/div[4]/div/span/div/div/div[1]/div[1]/span').send_keys(Keys.ENTER)

            
            try:
                # اگر عکس انتخاب شده باشد، ابتدا عکس را ارسال می‌کنیم
                if self.image_path:
                    if not self.send_image(phone_number):
                        self.log(f"⚠️ خطا در ارسال عکس به {phone_number}", "warning")
                        return False
                    
                    # تاخیر بین ارسال عکس و متن
                    time.sleep(random.uniform(2, 4))
                
                # ارسال متن
                wait = WebDriverWait(self.driver, 20)
                message_box = wait.until(EC.presence_of_element_located(
                    (By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]')
                ))
                
                time.sleep(random.uniform(1, 2))
                message_box.clear()
                time.sleep(random.uniform(0.5, 1))
                message_box.send_keys(message)
                time.sleep(random.uniform(1, 2))
                
                # اینتر زدن برای ارسال پیام
                message_box.send_keys(Keys.ENTER)
                time.sleep(random.uniform(2, 4))
                
                self.save_sent_message(phone_number)
                self.current_account_sent += 1
                
                if self.image_path:
                    self.log(f"✅ پیام + عکس به {phone_number} ارسال شد (اکانت: {self.current_account_sent})", "success")
                else:
                    self.log(f"✅ پیام به {phone_number} ارسال شد (اکانت: {self.current_account_sent})", "success")
                    
                return True
                
            except Exception as e:
                self.log(f"⚠️ خطا در پیدا کردن باکس پیام برای {phone_number}: {e}", "warning")
                return False
            
        except Exception as e:
            self.log(f"❌ خطا در ارسال به {phone_number}: {e}", "error")
            return False
            
    def type_text(self, text):
        """تایپ متن به صورت مستقیم"""
        self.keyboard.type(text)
        time.sleep(0.5)
    
    def type_text_with_delay(self, text, delay=0.1):
        """تایپ متن با تأخیر بین کاراکترها (طبیعی‌تر)"""
        for char in text:
            self.keyboard.type(char)
            time.sleep(random.uniform(delay * 0.5, delay * 1.5))
    
    def send_message(self, phone_number, message):
        """ارسال پیام متنی"""
        try:
            # تایپ متن
            self.type_text_with_delay(message)
            time.sleep(1)
            
            # ارسال با Enter
            self.keyboard.press(Key.enter)
            self.keyboard.release(Key.enter)
            
            self.log(f"📝 پیام به {phone_number} ارسال شد", "success")
            return True
        except Exception as e:
            self.log(f"❌ خطا در ارسال پیام: {e}", "error")
            return False
    
    def send_image(self, phone_number):
        """ارسال عکس به شماره مورد نظر"""
        try:
            # کلیک روی آیکون آپلود
            clip_button = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="main"]/footer/div[1]/div/span/div/div[2]/div/div[1]/div/span/div/div/div[1]/div[1]/span'))
            )
            clip_button.click()
            time.sleep(1)
            
            # کلیک روی گزینه عکس و ویدئو
            image_video_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div[1]/div/span[6]/div/ul/div/div/div[2]/li'))
            )
            image_video_button.click()
            time.sleep(1)
       
            correct_path = self.image_path.replace("\\", "/")
            filename = os.path.basename(correct_path)
            directory_path = os.path.dirname(correct_path)
            # آپلود عکس
            self.smooth_move(600,50)
            self.human_like_click(600,50)
            self.send_message(phone_number,directory_path)
            self.keyboard.press(Key.enter)
            time.sleep(1)
            self.keyboard.release(Key.enter)
            self.smooth_move(500,470)
            self.human_like_click(500,470)
            self.send_message(phone_number,filename)
            self.keyboard.press(Key.enter)
            time.sleep(1)
            self.keyboard.release(Key.enter)

            time.sleep(3)
            
            # کلیک روی دکمه ارسال
            send_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div[1]/div/div[3]/div/div[3]/div[2]/div/span/div/div/div/div[2]/div/div[2]/div[2]/div/div/span'))
            )
            send_button.click()
            time.sleep(2)
            
            self.log(f"🖼️ عکس به {phone_number} ارسال شد", "success")
            return True
            
        except Exception as e:
            self.log(f"❌ خطا در ارسال عکس به {phone_number}: {e}", "error")
            return False

    def start_sending(self):
        """شروع عملیات ارسال"""
        if self.is_running:
            return
        
        # کشتن کروم قبل از شروع
        self.kill_chrome_processes()
        time.sleep(2)
        
        # دریافت و اعتبارسنجی ورودی‌ها
        numbers_text = self.numbers_text.get('1.0', 'end').strip()
        if not numbers_text:
            messagebox.showwarning("هشدار", "لطفاً شماره‌ها را وارد کنید")
            return
        
        message = self.message_text.get('1.0', 'end').strip()
        if not message and not self.image_path:
            messagebox.showwarning("هشدار", "لطفاً متن پیام یا عکس را وارد کنید")
            return
        
        try:
            self.daily_limit = int(self.limit_var.get())
            base_delay = int(self.delay_var.get())
            self.switch_account_after = int(self.switch_var.get())
        except ValueError:
            messagebox.showwarning("هشدار", "لطفاً مقادیر عددی معتبر وارد کنید")
            return
        
        # پردازش شماره‌ها
        raw_numbers = [num.strip() for num in numbers_text.split(',') if num.strip()]
        validated_numbers = []
        
        for phone in raw_numbers:
            validated_phone = self.validate_phone_number(phone)
            if validated_phone:
                validated_numbers.append(validated_phone)
            else:
                self.log(f"⚠️ شماره {phone} نامعتبر است", "warning")
        
        if not validated_numbers:
            messagebox.showwarning("هشدار", "هیچ شماره معتبری یافت شد")
            return
        
        # فیلتر شماره‌های قابل ارسال
        filtered_numbers = []
        for phone in validated_numbers:
            if self.can_send_message(phone):
                filtered_numbers.append(phone)
            else:
                self.log(f"⏸️ شماره {phone} حذف شد (محدودیت)", "warning")
        
        if not filtered_numbers:
            messagebox.showwarning("هشدار", "هیچ شماره‌ای برای ارسال موجود نیست")
            return
        
        self.log(f"🚀 شروع ارسال {len(filtered_numbers)} پیام از {len(validated_numbers)} شماره...")
        if self.image_path:
            self.log(f"🖼️ ارسال همراه با عکس: {os.path.basename(self.image_path)}")
        self.log(f"🔄 تعویض اکانت پس از هر {self.switch_account_after} پیام")
        
        # شروع عملیات در ترد جداگانه
        self.is_running = True
        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.kill_chrome_btn.config(state='disabled')
        self.current_account_sent = 0
        
        threading.Thread(target=self._sending_process, 
                        args=(filtered_numbers, message, base_delay), 
                        daemon=True).start()

    def _sending_process(self, numbers, message, base_delay):
        """پردازش ارسال پیام در ترد جداگانه"""
        successful_sends = 0
        account_switches = 0
        
        try:
            self.log("🔧 در حال راه‌اندازی مرورگر...")
            self.update_status("در حال راه‌اندازی مرورگر")
            
            self.driver = self.setup_stealth_driver()
            if not self.driver:
                self.stop_sending()
                return
            
            self.log("📱 در حال باز کردن واتساپ...")
            self.driver.get("https://web.whatsapp.com")
            
            # منتظر ماندن برای اسکن QR (لاگین اولیه)
            self.update_status("منتظر اسکن QR کد")
            self.log("⏳ لطفاً QR کد را با اکانت اول اسکن کنید...")
            
            try:
                WebDriverWait(self.driver, 60).until(
                    EC.presence_of_element_located((By.XPATH, '//div[@id="side"]'))
                )
                self.log("✅ لاگین اولیه موفقیت‌آمیز بود", "success")
            except:
                self.log("⚠️ ممکن است QR کد اسکن نشده باشد", "warning")
                if not messagebox.askyesno("هشدار", "آیا لاگین انجام شده است؟ ادامه دهیم؟"):
                    self.stop_sending()
                    return
            
            # تنظیم پیشرفت
            self.progress.config(maximum=len(numbers), value=0)
            
            # ارسال پیام‌ها
            for i, phone in enumerate(numbers, 1):
                if not self.is_running:
                    break
                
                # بررسی نیاز به تعویض اکانت
                if (self.current_account_sent >= self.switch_account_after and 
                    self.current_account_sent > 0 and 
                    i < len(numbers)):
                    
                    self.log(f"🔄 رسیدیم به {self.current_account_sent} پیام - تعویض اکانت...")
                    account_switches += 1
                    
                    # لاگ‌اوت از اکانت فعلی
                    if self.perform_logout():
                        # منتظر ماندن برای لاگین با اکانت جدید
                        if not self.wait_for_new_login():
                            self.log("❌ تعویض اکانت ناموفق بود - توقف عملیات", "error")
                            break
                        else:
                            self.log(f"✅ تعویض اکانت موفقیت‌آمیز (تعویض #{account_switches})", "success")
                    else:
                        self.log("❌ خطا در تعویض اکانت - توقف عملیات", "error")
                        break
                
                self.update_status(f"ارسال پیام {i} از {len(numbers)}")
                self.log(f"📞 پردازش شماره: {phone}")
                
                if self.send_message_to_number(phone, message):
                    successful_sends += 1
                
                self.progress['value'] = i
                self.update_status()
                
                # تاخیر بین پیام‌ها
                if i < len(numbers) and self.is_running:
                    delay = self.get_smart_delay(base_delay)
                    self.log(f"⏳ منتظر {delay} ثانیه...")
                    
                    for sec in range(delay, 0, -1):
                        if not self.is_running:
                            break
                        time.sleep(1)
                
                # بررسی محدودیت روزانه
                if self.get_today_sent_count() >= self.daily_limit:
                    self.log(f"🚫 محدودیت روزانه ({self.daily_limit} پیام) رسیده است")
                    break
            
            # گزارش نهایی
            final_count = self.get_today_sent_count()
            self.log(f"🎉 عملیات کامل شد!", "success")
            self.log(f"📈 امروز در مجموع {final_count} پیام ارسال شده است")
            self.log(f"✅ {successful_sends} از {len(numbers)} پیام در این اجرا موفق بودند")
            self.log(f"🔄 {account_switches} بار تعویض اکانت انجام شد")
            
        except Exception as e:
            self.log(f"❌ خطای کلی: {e}", "error")
        finally:
            self.stop_sending()

    def get_smart_delay(self, base_delay):
        """تاخیر هوشمند بر اساس تعداد پیام‌های ارسالی"""
        today_count = self.get_today_sent_count()
        
        if today_count > 400:
            return base_delay + random.randint(60, 120)
        elif today_count > 300:
            return base_delay + random.randint(40, 80)
        elif today_count > 200:
            return base_delay + random.randint(20, 40)
        elif today_count > 100:
            return base_delay + random.randint(10, 20)
        else:
            return base_delay + random.randint(-5, 10)

    def stop_sending(self):
        """توقف عملیات ارسال"""
        self.is_running = False
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.kill_chrome_btn.config(state='normal')
        self.update_status("متوقف شده")
        
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
        
        self.log("⏹ عملیات متوقف شد", "warning")

    def on_closing(self):
        """مدیریت بسته شدن پنجره"""
        self.stop_sending()
        self.kill_chrome_processes()
        self.root.destroy()

# ---------------------- اجرای برنامه ----------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = WhatsAppSenderGUI(root)
    
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    root.mainloop()