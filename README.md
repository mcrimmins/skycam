# 🌵 Tucson SkyCam Prototype

An optimized, lightweight Flask web application and automated interval capture system designed specifically to run smoothly on low-resource hardware like the Raspberry Pi Zero W. 

This camera setup captures high-resolution horizon frames of the desert sky, organizes them dynamically by date and hour to save system resources, and allows for selective, threaded timelapse compilation using `ffmpeg`.

---

## 🚀 Current Features

* **Two-Tier Time Nesting:** Groups captured frames by Date $\rightarrow$ Hour using collapsible accordions, preventing browser layout crashes by loading images only when requested.
* **Lazy Loading:** Utilizes native `loading="lazy"` attributes so the Pi only transfers thumbnail data when an image is actively scrolled into view.
* **Threaded Video Compilation:** Stitches selected `.jpg` frames into a chronological `.mp4` video inside a detached background thread, keeping the web server fully responsive.
* **Automated Playback Loop:** Dynamically monitors background compilation progress, refreshes the dashboard, and automatically launches the finished timelapse in a new browser tab.
* **Smart Global Selection Filters:** Quick controls to toggle selections for the entire gallery, an entire day, or isolated hourly windows.

---

## 🛠️ Project Stack & Requirements

* **Hardware:** Raspberry Pi Zero W + Raspberry Pi Camera Module
* **Backend:** Python 3, Flask
* **Video Engine:** FFmpeg
* **Frontend:** Vanilla HTML5, CSS3, JavaScript

---

## 🗺️ Local Directory Structure

```text
~/skycam/
├── app.py                 # Core Flask Web Server & Threaded Compiler
├── README.md              # Project Documentation & Roadmap
├── .gitignore             # Excludes raw images/videos from cloud tracking
└── templates/
    └── index.html         # High-performance, low-RAM dashboard layout





