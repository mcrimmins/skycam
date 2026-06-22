import os
import time
import subprocess
import threading
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)
app.secret_key = 'super_secret_skycam_key_string'

# Core Folder Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(BASE_DIR, 'static', 'images')
os.makedirs(IMG_DIR, exist_ok=True)

# Safe Global thread trackers
is_compiling = False
video_ready_trigger = False

# Shared Runtime App State
app.config['INTERVAL'] = 30  # Default loop delay in seconds
app.config['AUTO_ON'] = True

def capture_frame():
    """Triggers hardware capture via rpicam-jpeg and uses Pillow to draw metadata text"""
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"frame_{timestamp}.jpg"
    filepath = os.path.join(IMG_DIR, filename)
    latest_path = os.path.join(IMG_DIR, 'latest.jpg')
                                                                                                                     
    # 1. Read the Pi's live internal thermal sensor                                                                  
    try:                                                                                                             
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:                                                
            temp_c = int(f.read()) / 1000.0                                                                          
            temp_f = (temp_c * 9/5) + 32                                                                             
            temp_string = f"CPU: {temp_c:.1f}°C / {temp_f:.1f}°F"                                                    
    except Exception:                                                                                                
        temp_string = "CPU: Unknown"                                                                                 
                                                                                                                     
    # 2. Capture a clean image using the correct rpicam-jpeg command
    cmd = f"rpicam-jpeg -o {filepath} --width 1920 --height 1080 --nopreview"                                        
    subprocess.run(cmd, shell=True)                                                                                  
                                                                                                                     
    # 3. Use Pillow to draw the custom status bar if the image saved successfully                                    
    if os.path.exists(filepath):                                                                                     
        from PIL import Image, ImageDraw, ImageFont                                                                  
                                                                                                                     
        try:                                                                                                         
            img = Image.open(filepath)                                                                               
            draw = ImageDraw.Draw(img)                                                                               
                                                                                                                     
            display_time = time.strftime("%Y-%m-%d %I:%M:%S %p")                                                     
            overlay_text = f"Tucson SkyCam  |  {display_time}  |  {temp_string}"                                     
                                                                                                                     
            font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"                                       
                                                                                                                     
            if os.path.exists(font_path):                                                                             
                font = ImageFont.truetype(font_path, 32)                                                             
                banner_height = 65                                                                                   
                text_y_position = 10                                                                                 
            else:                                                                                                    
                font = ImageFont.load_default()                                                                      
                banner_height = 45                                                                                   
                text_y_position = 12                                                                                 
                                                                                                                     
            draw.rectangle([0, 0, 1920, banner_height], fill=(0, 0, 0, 160))                                         
            draw.text((25, text_y_position), overlay_text, fill=(255, 255, 255), font=font)                          
            img.save(filepath, quality=90)                                                                           
                                                                                                                     
            # Mirror copy to the live view pointer
            subprocess.run(f"cp {filepath} {latest_path}", shell=True)                                               
            print(f"[SkyCam] Successfully captured stamped frame: {filename}")
        except Exception as e:                                                                                       
            print(f"Pillow drawing error: {e}")

def auto_capture_thread():
    """Background loop running autonomously through timed intervals"""
    print("[SkyCam Engine] Interval automation daemon initialized.")
    while True:                                                                                                      
        if app.config['AUTO_ON']:                                                                                    
            try:                                                                                                     
                capture_frame()                                                                                      
            except Exception as e:                                                                                   
                print(f"Loop Capture Error: {e}")                                                                    
                                                                                                                     
        time.sleep(app.config['INTERVAL'])

def background_stitch(selected, manifest_path, output_video):
    """Compiles video in a background thread, then trips the automatic popup flag"""
    global is_compiling, video_ready_trigger
    is_compiling = True
    try:
        with open(manifest_path, 'w') as f:
            for img in selected:
                img_path = os.path.join(IMG_DIR, img)
                f.write(f"file '{img_path}'\n")            
                f.write("duration 0.1\n") # 10 frames per second
        
        # Clean up existing video
        subprocess.run(f"rm -f {output_video}", shell=True)
        
        # Compile via FFmpeg
        ffmpeg_cmd = f"ffmpeg -y -f concat -safe 0 -i {manifest_path} -c:v libx264 -pix_fmt yuv420p {output_video}"
        subprocess.run(ffmpeg_cmd, shell=True)
    except Exception as e:
        print(f"Compilation error: {e}")
    finally:
        if os.path.exists(manifest_path):
            os.remove(manifest_path)
        is_compiling = False
        video_ready_trigger = True # Signal the frontend to pop open a new tab!

# Start the background capture clock immediately on script launch
threading.Thread(target=auto_capture_thread, daemon=True).start()

@app.route('/')                                                                                                      
def index():
    global is_compiling, video_ready_trigger
    all_files = os.listdir(IMG_DIR)                                                                                  
    raw_images = sorted([f for f in all_files if f.startswith('frame_') and f.endswith('.jpg')], reverse=True)       
                                                                                                                     
    grouped_images = {}                                                                                              
    for img in raw_images:                                                                                           
        try:                                                                                                         
            parts = img.split('_')                                                                                   
            date_part = parts[1]                                                                                     
            time_part = parts[2]                                                                                     
                                                                                                                     
            formatted_date = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"                                    
                                                                                                                     
            raw_hour = int(time_part[:2])                                                                            
            if raw_hour == 0:
                formatted_hour = "12:00 AM"                                                                          
            elif raw_hour == 12:                                                                                     
                formatted_hour = "12:00 PM"                                                                          
            elif raw_hour > 12:                                                                                      
                formatted_hour = f"{raw_hour - 12:02d}:00 PM"                                                        
            else:                                                                                                    
                formatted_hour = f"{raw_hour:02d}:00 AM"                                                             
        except Exception:                                                                                            
            formatted_date = "Unknown Date"                                                                          
            formatted_hour = "Unknown Hour"                                                                          
                                                                                                                     
        if formatted_date not in grouped_images:                                                                     
            grouped_images[formatted_date] = {}                                                                      
        if formatted_hour not in grouped_images[formatted_date]:                                                     
            grouped_images[formatted_date][formatted_hour] = []                                                      
                                                                                                                     
        grouped_images[formatted_date][formatted_hour].append(img)                                                   
                                                                                                                     
    pop_video = video_ready_trigger
    if pop_video:
        video_ready_trigger = False

    timelapse_exists = os.path.exists(os.path.join(IMG_DIR, 'timelapse.mp4'))                                        
                                                                                                                     
    return render_template('index.html',                                                                             
                           grouped_images=grouped_images,                                                            
                           config=app.config,                                                                        
                           timelapse_exists=timelapse_exists,
                           is_compiling=is_compiling,
                           pop_video=pop_video,
                           cache_buster=time.time())                                                                 
                                                                                                                     
@app.route('/snap')                                                                                                  
def snap():                                                                                                          
    capture_frame()                                                                                                  
    return redirect(url_for('index'))                                                                                
                                                                                                                     
@app.route('/update_settings', methods=['POST'])                                                                     
def update_settings():                                                                                               
    action = request.form.get('action')                                                                              
    try:                                                                                                             
        app.config['INTERVAL'] = int(request.form.get('interval', 30))                                               
    except ValueError:                                                                                               
        app.config['INTERVAL'] = 30                                                                                  
                                                                                                                     
    if action == 'start':                                                                                            
        app.config['AUTO_ON'] = True                                                                                 
    elif action == 'stop':                                                                                           
        app.config['AUTO_ON'] = False                                                                                
                                                                                                                     
    return redirect(url_for('index'))                                                                                
                                                                                                                     
@app.route('/compile_selected', methods=['POST'])                                                                    
def compile_selected():                                                                                              
    global is_compiling
    if is_compiling:
        return redirect(url_for('index'))

    selected = request.form.getlist('selected_images')                                                               
    if not selected:                                                                                                 
        return redirect(url_for('index'))                                                                            
                                                                                                                     
    selected.sort()                                                                                                  
    manifest_path = os.path.join(BASE_DIR, 'sequence.txt')                                                           
    output_video = os.path.join(IMG_DIR, 'timelapse.mp4')                                                            
                                                                                                                     
    # Run the compilation completely out of the main thread to protect web response times
    threading.Thread(target=background_stitch, args=(selected, manifest_path, output_video)).start()
    return redirect(url_for('index'))                                                                                
                                                                                                                     
@app.route('/delete_selected', methods=['POST'])                                                                     
def delete_selected():                                                                                               
    selected = request.form.getlist('selected_images')                                                               
    for img in selected:                                                                                             
        if img.startswith('frame_') and img.endswith('.jpg'):                                                        
            img_path = os.path.join(IMG_DIR, img)                                                                    
            if os.path.exists(img_path):                                                                             
                try: os.remove(img_path)                                                                              
                except Exception: pass                                                              
    return redirect(url_for('index'))                                                                                

if __name__ == '__main__':                                                                                           
    app.run(host='0.0.0.0', port=5000, debug=True)
