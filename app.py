import os
import time
import subprocess
import threading
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)
app.secret_key = 'super_secret_skycam_key_string'

IMG_DIR = os.path.expanduser('~/skycam/static/images')
if not os.path.exists(IMG_DIR):
    os.makedirs(IMG_DIR)

# Safe Global thread trackers
is_compiling = False
video_ready_trigger = False  # Fixed: Standard global variable instead of app.config

app.config['INTERVAL'] = 30
app.config['AUTO_ON'] = False

def background_stitch(selected_paths, output_path):
    """Worker function that runs invisibly in a separate thread to stitch video"""
    global is_compiling, video_ready_trigger
    is_compiling = True
    
    txt_list_path = os.path.join(IMG_DIR, 'images_to_stitch.txt')
    try:
        with open(txt_list_path, 'w') as f:
            for path in selected_paths:
                f.write(f"file '{path}'\n")
                
        # -y forces overwrite, r=10 sets playback speed to 10 frames per second
        cmd = f"ffmpeg -y -f concat -safe 0 -r 10 -i {txt_list_path} -c:v libx264 -pix_fmt yuv420p {output_path}"
        subprocess.run(cmd, shell=True)
        
    except Exception as e:
        print(f"Compilation background engine error: {e}")
        
    finally:
        if os.path.exists(txt_list_path):
            os.remove(txt_list_path)
        is_compiling = False
        video_ready_trigger = True  # Fixed: Safe variable flipping outside of app context

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
        
    # Read the pop trigger and reset it right away if true
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

@app.route('/compile_selected', methods=['POST'])
def compile_selected():
    global is_compiling
    if is_compiling:
        return redirect(url_for('index'))
        
    selected_filenames = request.form.getlist('selected_images')
    if not selected_filenames:
        return redirect(url_for('index'))
        
    selected_filenames = sorted(selected_filenames)
    selected_paths = [os.path.join(IMG_DIR, name) for name in selected_filenames]
    output_path = os.path.join(IMG_DIR, 'timelapse.mp4')
    
    if os.path.exists(output_path):
        try:
            os.remove(output_path)
        except Exception:
            pass

    threading.Thread(target=background_stitch, args=(selected_paths, output_path)).start()
    return redirect(url_for('index'))

@app.route('/delete_selected', methods=['POST'])
def delete_selected():
    selected = request.form.getlist('selected_images')
    for img in selected:
        if img.startswith('frame_') and img.endswith('.jpg'):
            img_path = os.path.join(IMG_DIR, img)
            if os.path.exists(img_path):
                try:
                    os.remove(img_path)
                except Exception:
                    pass
    return redirect(url_for('index'))

@app.route('/update_settings', methods=['POST'])
def update_settings():
    action = request.form.get('action')
    interval = request.form.get('interval')
    if interval:
        app.config['INTERVAL'] = int(interval)
    if action == 'start':
        app.config['AUTO_ON'] = True
    elif action == 'stop':
        app.config['AUTO_ON'] = False
    return redirect(url_for('index'))

@app.route('/snap')
def snap():
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"frame_{timestamp}.jpg"
    filepath = os.path.join(IMG_DIR, filename)
    subprocess.run(f"touch {filepath}", shell=True)
    subprocess.run(f"cp {filepath} {os.path.join(IMG_DIR, 'latest.jpg')}", shell=True)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
