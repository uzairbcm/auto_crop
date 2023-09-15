""" Credit to Olivia Walch for some code used here from https://github.com/Arcascope/screen-scrape"""
import cv2
import os
from glob import iglob
import tkinter as tk
from tkinter import *
from tkinter import filedialog
from tkinter import ttk
from tkinter import messagebox
from ttkthemes import ThemedTk
import pytesseract
from pytesseract import Output
import threading
import numpy as np
from PIL import ImageFont, ImageDraw, Image  

#from thefuzz import *
#from thefuzz import process, fuzz
#from scipy import stats
#import re

# def resource_path(relative_path):
#     """ Get absolute path to resource, works for dev and for PyInstaller """
#     try:
#         # PyInstaller creates a temp folder and stores path in _MEIPASS
#         base_path = sys._MEIPASS
#     except Exception:
#         base_path = os.path.abspath(".")

#     return os.path.join(base_path, relative_path)

# pytesseract.pytesseract.tesseract_cmd = resource_path("tesseract/tesseract.exe")

pytesseract.pytesseract.tesseract_cmd = r"C:/Users/*/AppData/Local/Programs/Tesseract-OCR/tesseract.exe"

patch_image_path = r"C:\Users\*\patch_image.png"

def patch_image(image_path, min_height=2160):

    current_image = cv2.imread(image_path)
    curr_height, curr_width, _ = current_image.shape

    if curr_height < min_height:

        patching_image = cv2.imread(patch_image_path)
        new_width = curr_width
        adjusted_patch_height = min_height - curr_height
        adjusted_patching_image = patching_image[:adjusted_patch_height, :new_width]
        new_image = np.zeros((min_height, new_width, 3), dtype=np.uint8)
        new_image[:adjusted_patch_height, :] = adjusted_patching_image
        new_image[adjusted_patch_height:, :] = current_image

        return new_image

    return current_image
    
def get_directory():
    if home_dir := selected_directory.get():
        return home_dir
    messagebox.showwarning("Warning", "Please select a directory first.")
    return None
    
def filter_folders(folders):
    ignore_folders = ["Cropped Images", "Do Not Use", "Battery Activity", "Parental Controls"]
    return [
        f.replace("\\", "/")
        for f in folders
        if os.path.isdir(f) and all(ignored not in f for ignored in ignore_folders)
    ]

def process_and_save_image(image_path, save_path):
    cropped_image, rightmost_white_pixel = preprocess_image(image_path)
    name, title = extract_text(cropped_image, rightmost_white_pixel)
    phi_removed_image = remove_phi(cropped_image, rightmost_white_pixel, name, title)

    output_path = save_path + image_path.rsplit("/")[-3] + "/" + image_path.rsplit("/")[-2] + "/" + image_path.rsplit("/")[-1]
    cv2.imwrite(output_path, phi_removed_image)

def preprocess_image(image_path):
    crop_x = 1620 - 990
    crop_y = 0
    crop_w = 1620
    crop_h = 2160

    name_x = 75
    name_y = 40
    name_w = 415
    name_h = 135

    blue_low = np.array([100, 50, 50])
    blue_high = np.array([130, 255, 255])

    current_image = patch_image(image_path)

    cropped_image = current_image[crop_y:crop_h, crop_x:crop_w]

    name_roi = cropped_image[name_y:name_h, name_x:name_w]
    name_hsv = cv2.cvtColor(name_roi, cv2.COLOR_BGR2HSV)
    name_mask = cv2.inRange(name_hsv, blue_low, blue_high)

    white_pixels = np.argwhere(name_mask > 200)
    if white_pixels.any():
        rightmost_white_pixel = list(white_pixels[np.argmax(white_pixels[:, 1])])[1] + name_x
    else:
        rightmost_white_pixel = name_w

    return cropped_image, rightmost_white_pixel

def extract_text(cropped_image, rightmost_white_pixel):
    name_x = 75
    name_y = 40
    name_h = 135

    title_x = 325
    title_y = 50
    title_w = 800
    title_h = 125

    name = ""
    title = ""

    name_find = pytesseract.image_to_data(cropped_image[name_y:name_h, name_x - 10:rightmost_white_pixel + 10], config='--psm 7 --oem 3 -c tessedit_char_whitelist="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.+"', output_type=Output.DICT)

    for i in range(len(name_find["level"])):
        if len(name_find["text"][i]) > 2:
            name = f'{name} {name_find["text"][i]}'.lstrip()

    if name not in ("ScreenTime", "", "SereenTime", "reel"):
        title_find = pytesseract.image_to_data(cropped_image[title_y:title_h, rightmost_white_pixel + 10:title_w], config='--psm 7 --oem 3 -c tessedit_char_whitelist="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.+"', output_type=Output.DICT)
        for i in range(len(title_find["level"])):
            if len(title_find["text"][i]) > 2:
                title = f'{title} {title_find["text"][i]}'.lstrip()
                title = "Total " if title == "" else f"{title} "
    return name, title

def remove_phi(cropped_image, rightmost_white_pixel, name):
    if name in ("ScreenTime", "", "SereenTime", "reel"):
        title_roi = cropped_image[50:125, rightmost_white_pixel + 10:800]
        title_replace_color = get_most_common_color(title_roi)
        image_with_title_removed = cv2.rectangle(
            cropped_image,
            [rightmost_white_pixel + 10, 50],
            [800, 125],
            title_replace_color,
            -1,
        )
        return draw_text_on_image(image_with_title_removed, "Daily Usage", [cropped_image.shape[1]//2-90, 140//2])
    else:
        name_roi = cropped_image[40:135, 75:rightmost_white_pixel]
        name_replace_color = get_most_common_color(name_roi)
        return cv2.rectangle(
            cropped_image,
            [75, 40],
            [rightmost_white_pixel, 135],
            name_replace_color,
            -1,
        )

def draw_text_on_image(image, text, location):

    # Convert the image to RGB (OpenCV uses BGR) 
    cv2_im_rgb = cv2.cvtColor(image,cv2.COLOR_BGR2RGB)  
    
    # Pass the image to PIL  
    pil_im = Image.fromarray(cv2_im_rgb)  
    
    draw = ImageDraw.Draw(pil_im)  
    # use a truetype font  
    font = ImageFont.truetype("SF-Pro-Display-Medium.otf", 40)
    
    x, y = location

    # Draw the text  
    draw.text((x, y), text, font=font, fill=(0,0,0,0))  
    
    # Get back the image to OpenCV  
    return cv2.cvtColor(np.array(pil_im), cv2.COLOR_RGB2BGR)

def get_most_common_color(title_roi):
    unq, count = np.unique(title_roi.reshape(-1, title_roi.shape[-1]), axis=0, return_counts=True)
    sort = np.argsort(count)
    return unq[sort][-1].tolist()

def do_crop():
    if not (home_dir := get_directory()):
        return
    folder_path = f"{home_dir}*/*"
    save_path = f"{home_dir}/Cropped Images/"
    image_types = ["PNG", "JPG", "png", "jpg"]

    folders = filter_folders(iglob(f"{folder_path}*/*", recursive=True))

    for folder in folders:
        if not os.path.isdir(save_path + folder.replace(home_dir, "")):
            os.makedirs(save_path + folder.replace(home_dir, ""))
        images = [f.replace("\\", "/") for f in iglob(folder + "**\\*", recursive=True) if os.path.isfile(f) and (f[-3:] in image_types)]
        for image_path in images:
            process_and_save_image(image_path, save_path)

    # Rest of your original code
    progress_bar.stop()
    root.deiconify()
    root.attributes('-topmost', 1)
    root.attributes('-topmost', 0)
    messagebox.showinfo('', 'Automatic cropping completed.\nYou must double-check to ensure that all PHI was removed.')
    run_button.config(state="normal")
    select_button.config(state="normal")

def select_directory():
    home_dir = filedialog.askdirectory().replace("\\","/")
    selected_directory.set(home_dir)
    directory_label.config(text=home_dir)  # Update the label text

def start_app():
    run_button.config(state="disabled")
    select_button.config(state="disabled")
    progress_bar.start(10)
    threading.Thread(target=do_crop).start()

root = ThemedTk(theme="arc")

root.title("Auto Crop for iPad Screenshots")

# Set the window size and position
window_width = 375
window_height = 275
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
x = (screen_width - window_width) // 2
y = (screen_height - window_height) // 2
root.geometry(f"{window_width}x{window_height}+{x}+{y}")

# Create a frame to hold the widgets
frame = tk.Frame(root, padx=20, pady=20)
frame.pack()

selected_directory = tk.StringVar()

s = ttk.Style()
s.configure('.',font=('Helvetica', 12))

sd = ttk.Style()
sd.configure('TButton', font=('Helvetica', 12, 'bold'), foreground='black')

sd = ttk.Style()
sd.configure('TLabel', font=('Helvetica', 10, 'bold'), background='white')

# Select Directory Button
select_button = ttk.Button(frame, text="Select Directory", command=select_directory, style='TButton')
select_button.pack(pady=10)

# Directory Label
directory_label = ttk.Label(frame, text="No directory selected", wraplength=325)
directory_label.pack(pady=10)

# Run App Button
run_button = ttk.Button(frame, text="Start Cropping", command=start_app, state="disabled")
run_button.pack(pady=20)

sp = ttk.Style()
sp.configure("TProgressbar", thickness=30)
progress_bar = ttk.Progressbar(frame, style="TProgressbar", mode="indeterminate", length="125")
progress_bar.pack(pady=10)

# Update the state of the Run App button when the directory selection changes
selected_directory.trace("w", lambda *args: run_button.config(state="normal") if selected_directory.get() else run_button.config(state="disabled"))

root.mainloop()

