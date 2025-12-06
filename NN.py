from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Key, Controller as KeyboardController
import math
import random
import time  # اضافه شده

class WhatsAppBot:
    def __init__(self):
        self.mouse = MouseController()
        self.keyboard = KeyboardController()
    
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
w =WhatsAppBot()

w.smooth_move(800,200)

w.human_like_click(800,200)
w.send_message(989169640564,"/downloads")



