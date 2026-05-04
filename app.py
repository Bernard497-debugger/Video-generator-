import os
import cv2
import numpy as np
from flask import Flask, render_template, request, send_file, jsonify, url_for
from werkzeug.utils import secure_filename
from datetime import datetime
import base64
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import traceback
import sys

app = Flask(__name__)

# Configuration for Render
BASE_DIR = '/tmp' if os.environ.get('RENDER') else '.'
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
app.config['VIDEO_FOLDER'] = os.path.join(BASE_DIR, 'videos')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg'}

# Create folders
os.makedirs(app.config['VIDEO_FOLDER'], exist_ok=True)
os.makedirs('templates', exist_ok=True)

# Video settings
DEFAULT_FPS = 30
DEFAULT_WIDTH = 640
DEFAULT_HEIGHT = 480

class VideoGenerator:
    def __init__(self, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT, fps=DEFAULT_FPS):
        self.width = width
        self.height = height
        self.fps = fps
        self.fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    
    def create_text_animation(self, text, duration=3, output_path='output.mp4'):
        """Create video with animated text"""
        total_frames = duration * self.fps
        video_writer = cv2.VideoWriter(output_path, self.fourcc, self.fps, (self.width, self.height))
        
        # Create font
        font_scale = 1.5
        thickness = 2
        text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)[0]
        text_x = (self.width - text_size[0]) // 2
        
        for i in range(total_frames):
            # Create frame
            frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
            
            # Gradient background
            for y in range(self.height):
                color_value = int(128 + 127 * np.sin(y / 50 + i / 30))
                frame[y, :] = [color_value // 2, color_value // 3, color_value]
            
            # Animate text position
            y_offset = int(self.height // 3 + np.sin(i / 20) * 30)
            text_y = y_offset
            
            # Change color over time
            color = (
                128 + int(127 * np.sin(i / 30)),
                128 + int(127 * np.sin(i / 30 + 2)),
                128 + int(127 * np.sin(i / 30 + 4))
            )
            
            # Add shadow for better visibility
            cv2.putText(frame, text, (text_x + 2, text_y + 2), 
                       cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), thickness + 1)
            cv2.putText(frame, text, (text_x, text_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness)
            
            video_writer.write(frame)
        
        video_writer.release()
        return output_path
    
    def create_zoom_effect(self, image_path, duration=3, output_path='output.mp4'):
        """Create zoom effect on an image"""
        total_frames = duration * self.fps
        video_writer = cv2.VideoWriter(output_path, self.fourcc, self.fps, (self.width, self.height))
        
        # Load and resize image
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Cannot load image: {image_path}")
        
        img = cv2.resize(img, (self.width, self.height))
        
        for i in range(total_frames):
            # Calculate zoom scale
            progress = i / total_frames
            scale = 1 + progress * 0.5  # Zoom in by 50%
            
            # Calculate crop area
            new_w = int(self.width / scale)
            new_h = int(self.height / scale)
            x1 = (self.width - new_w) // 2
            y1 = (self.height - new_h) // 2
            x2 = x1 + new_w
            y2 = y1 + new_h
            
            # Crop and resize
            cropped = img[y1:y2, x1:x2]
            frame = cv2.resize(cropped, (self.width, self.height))
            
            video_writer.write(frame)
        
        video_writer.release()
        return output_path
    
    def create_pan_effect(self, image_path, duration=3, direction='horizontal', output_path='output.mp4'):
        """Create pan effect on an image"""
        total_frames = duration * self.fps
        video_writer = cv2.VideoWriter(output_path, self.fourcc, self.fps, (self.width, self.height))
        
        # Load image
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Cannot load image: {image_path}")
        
        img = cv2.resize(img, (self.width * 2, self.height))
        
        for i in range(total_frames):
            progress = i / total_frames
            
            if direction == 'horizontal':
                x_offset = int(progress * self.width)
                frame = img[:, x_offset:x_offset + self.width]
            elif direction == 'vertical':
                img_vert = cv2.resize(img, (self.width, self.height * 2))
                y_offset = int(progress * self.height)
                frame = img_vert[y_offset:y_offset + self.height, :]
            else:
                frame = cv2.resize(img, (self.width, self.height))
            
            video_writer.write(frame)
        
        video_writer.release()
        return output_path
    
    def create_fade_transition(self, image_path1, image_path2, duration=3, output_path='output.mp4'):
        """Create fade transition between two images"""
        total_frames = duration * self.fps
        video_writer = cv2.VideoWriter(output_path, self.fourcc, self.fps, (self.width, self.height))
        
        # Load images
        img1 = cv2.imread(image_path1)
        img2 = cv2.imread(image_path2)
        
        if img1 is None or img2 is None:
            raise ValueError("Cannot load one or both images")
        
        img1 = cv2.resize(img1, (self.width, self.height))
        img2 = cv2.resize(img2, (self.width, self.height))
        
        for i in range(total_frames):
            alpha = i / total_frames
            frame = cv2.addWeighted(img1, 1 - alpha, img2, alpha, 0)
            video_writer.write(frame)
        
        video_writer.release()
        return output_path
    
    def create_text_slideshow(self, texts, duration_per_text=2, output_path='output.mp4'):
        """Create slideshow with different text animations"""
        temp_videos = []
        
        for idx, text in enumerate(texts):
            temp_path = f'{os.path.dirname(output_path)}/temp_{idx}_{datetime.now().timestamp()}.mp4'
            self.create_text_animation(text, duration_per_text, temp_path)
            temp_videos.append(temp_path)
        
        # Combine videos
        return self._combine_videos(temp_videos, output_path)
    
    def _combine_videos(self, video_paths, output_path):
        """Combine multiple videos"""
        if not video_paths:
            return None
        
        # Use the first video to get properties
        cap = cv2.VideoCapture(video_paths[0])
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        
        video_writer = cv2.VideoWriter(output_path, self.fourcc, fps, (width, height))
        
        for video_path in video_paths:
            cap = cv2.VideoCapture(video_path)
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                video_writer.write(frame)
            cap.release()
            # Cleanup temp file
            if os.path.exists(video_path):
                os.remove(video_path)
        
        video_writer.release()
        return output_path

# HTML Templates (embedded as strings)
INDEX_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Flask Video Generator - Render Edition</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .header p {
            opacity: 0.9;
        }
        
        .content {
            padding: 40px;
        }
        
        .generator-section {
            margin-bottom: 40px;
            padding: 25px;
            background: #f8f9fa;
            border-radius: 10px;
            transition: transform 0.2s;
        }
        
        .generator-section:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        
        .generator-section h2 {
            color: #667eea;
            margin-bottom: 20px;
            font-size: 1.5em;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: bold;
            color: #333;
        }
        
        input, select, textarea {
            width: 100%;
            padding: 10px;
            border: 2px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
            transition: border-color 0.3s;
        }
        
        input:focus, select:focus, textarea:focus {
            outline: none;
            border-color: #667eea;
        }
        
        button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            font-weight: bold;
            transition: transform 0.2s;
        }
        
        button:hover {
            transform: translateY(-2px);
        }
        
        .video-preview {
            margin-top: 20px;
            text-align: center;
        }
        
        video {
            max-width: 100%;
            border-radius: 10px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.2);
        }
        
        .alert {
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            animation: slideIn 0.3s ease;
        }
        
        @keyframes slideIn {
            from {
                transform: translateY(-20px);
                opacity: 0;
            }
            to {
                transform: translateY(0);
                opacity: 1;
            }
        }
        
        .alert-success {
            background-color: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        
        .alert-error {
            background-color: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        
        .loading {
            display: none;
            text-align: center;
            margin-top: 20px;
        }
        
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .btn-download {
            display: inline-block;
            margin-top: 15px;
            background: #28a745;
            text-decoration: none;
        }
        
        .btn-download:hover {
            background: #218838;
        }
        
        @media (max-width: 768px) {
            .content {
                padding: 20px;
            }
            
            .header h1 {
                font-size: 1.8em;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎬 Flask Video Generator</h1>
            <p>Create amazing videos with text animations, effects, and transitions</p>
            <p style="font-size: 0.9em; margin-top: 10px;">🚀 Deployed on Render</p>
        </div>
        
        <div class="content">
            <div id="alert-container"></div>
            
            <!-- Text Animation Generator -->
            <div class="generator-section">
                <h2>📝 Text Animation Video</h2>
                <form id="text-form">
                    <div class="form-group">
                        <label>Text to animate:</label>
                        <textarea name="text" rows="3" required placeholder="Enter your text here..." style="resize: vertical;"></textarea>
                    </div>
                    <div class="form-group">
                        <label>Duration (seconds):</label>
                        <input type="number" name="duration" value="3" min="1" max="10">
                    </div>
                    <button type="submit">🎬 Generate Text Video</button>
                </form>
            </div>
            
            <!-- Image Effects Generator -->
            <div class="generator-section">
                <h2>🖼️ Image Effects Video</h2>
                <form id="image-effect-form" enctype="multipart/form-data">
                    <div class="form-group">
                        <label>Upload Image:</label>
                        <input type="file" name="image" accept="image/*" required>
                    </div>
                    <div class="form-group">
                        <label>Effect Type:</label>
                        <select name="effect">
                            <option value="zoom">Zoom In</option>
                            <option value="pan_h">Pan Horizontal</option>
                            <option value="pan_v">Pan Vertical</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Duration (seconds):</label>
                        <input type="number" name="duration" value="3" min="1" max="10">
                    </div>
                    <button type="submit">✨ Generate Effect Video</button>
                </form>
            </div>
            
            <!-- Transition Video Generator -->
            <div class="generator-section">
                <h2>🔄 Image Transition Video</h2>
                <form id="transition-form" enctype="multipart/form-data">
                    <div class="form-group">
                        <label>First Image:</label>
                        <input type="file" name="image1" accept="image/*" required>
                    </div>
                    <div class="form-group">
                        <label>Second Image:</label>
                        <input type="file" name="image2" accept="image/*" required>
                    </div>
                    <div class="form-group">
                        <label>Transition Duration (seconds):</label>
                        <input type="number" name="duration" value="3" min="1" max="5">
                    </div>
                    <button type="submit">🔄 Generate Transition Video</button>
                </form>
            </div>
            
            <!-- Text Slideshow -->
            <div class="generator-section">
                <h2>📋 Text Slideshow</h2>
                <form id="slideshow-form">
                    <div class="form-group">
                        <label>Texts (one per line):</label>
                        <textarea name="texts" rows="5" required placeholder="Enter multiple lines of text...&#10;Line 1&#10;Line 2&#10;Line 3" style="resize: vertical;"></textarea>
                    </div>
                    <div class="form-group">
                        <label>Duration per text (seconds):</label>
                        <input type="number" name="duration" value="2" min="1" max="5">
                    </div>
                    <button type="submit">📺 Generate Slideshow</button>
                </form>
            </div>
            
            <div class="loading" id="loading">
                <div class="spinner"></div>
                <p style="margin-top: 10px;">🎥 Generating your video... Please wait</p>
            </div>
            
            <div id="video-container" class="video-preview"></div>
        </div>
    </div>
    
    <script>
        async function submitForm(formData, endpoint) {
            const loading = document.getElementById('loading');
            const alertContainer = document.getElementById('alert-container');
            const videoContainer = document.getElementById('video-container');
            
            loading.style.display = 'block';
            videoContainer.innerHTML = '';
            alertContainer.innerHTML = '';
            
            try {
                const response = await fetch(endpoint, {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                if (data.success) {
                    alertContainer.innerHTML = '<div class="alert alert-success">✅ ' + data.message + '</div>';
                    videoContainer.innerHTML = `
                        <video controls autoplay>
                            <source src="${data.video_url}" type="video/mp4">
                            Your browser does not support the video tag.
                        </video>
                        <br>
                        <a href="${data.video_url}" download class="btn-download" style="display: inline-block; padding: 10px 20px; background: #28a745; color: white; text-decoration: none; border-radius: 5px; margin-top: 10px;">📥 Download Video</a>
                    `;
                } else {
                    alertContainer.innerHTML = '<div class="alert alert-error">❌ Error: ' + data.error + '</div>';
                }
            } catch (error) {
                alertContainer.innerHTML = '<div class="alert alert-error">❌ Error: ' + error.message + '</div>';
            } finally {
                loading.style.display = 'none';
            }
        }
        
        document.getElementById('text-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            await submitForm(formData, '/generate/text');
        });
        
        document.getElementById('image-effect-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            await submitForm(formData, '/generate/effect');
        });
        
        document.getElementById('transition-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            await submitForm(formData, '/generate/transition');
        });
        
        document.getElementById('slideshow-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            await submitForm(formData, '/generate/slideshow');
        });
    </script>
</body>
</html>
'''

# Create template files
with open('templates/index.html', 'w') as f:
    f.write(INDEX_TEMPLATE)

# Flask Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate/text', methods=['POST'])
def generate_text_video():
    try:
        text = request.form.get('text')
        duration = int(request.form.get('duration', 3))
        
        if not text:
            return jsonify({'success': False, 'error': 'Text is required'})
        
        # Limit duration for Render free tier
        duration = min(duration, 10)
        
        # Generate unique filename
        filename = f'text_video_{datetime.now().strftime("%Y%m%d_%H%M%S")}.mp4'
        filepath = os.path.join(app.config['VIDEO_FOLDER'], filename)
        
        # Create video
        generator = VideoGenerator()
        generator.create_text_animation(text, duration, filepath)
        
        # Check if file exists and is not empty
        if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
            raise ValueError("Video file was not created properly")
        
        video_url = url_for('static', filename=f'videos/{filename}', _external=True)
        
        return jsonify({
            'success': True,
            'message': 'Text animation video created successfully!',
            'video_url': video_url,
            'filename': filename
        })
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/generate/effect', methods=['POST'])
def generate_effect_video():
    try:
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': 'No image uploaded'})
        
        image = request.files['image']
        effect = request.form.get('effect')
        duration = int(request.form.get('duration', 3))
        
        if image.filename == '':
            return jsonify({'success': False, 'error': 'No image selected'})
        
        # Limit duration for Render free tier
        duration = min(duration, 10)
        
        # Save uploaded image temporarily
        img_filename = f'temp_img_{datetime.now().strftime("%Y%m%d_%H%M%S")}.jpg'
        img_path = os.path.join(app.config['VIDEO_FOLDER'], img_filename)
        image.save(img_path)
        
        # Generate video
        filename = f'effect_video_{datetime.now().strftime("%Y%m%d_%H%M%S")}.mp4'
        filepath = os.path.join(app.config['VIDEO_FOLDER'], filename)
        
        generator = VideoGenerator()
        
        if effect == 'zoom':
            generator.create_zoom_effect(img_path, duration, filepath)
        elif effect == 'pan_h':
            generator.create_pan_effect(img_path, duration, 'horizontal', filepath)
        elif effect == 'pan_v':
            generator.create_pan_effect(img_path, duration, 'vertical', filepath)
        else:
            generator.create_zoom_effect(img_path, duration, filepath)
        
        # Cleanup temp image
        if os.path.exists(img_path):
            os.remove(img_path)
        
        video_url = url_for('static', filename=f'videos/{filename}', _external=True)
        
        return jsonify({
            'success': True,
            'message': 'Effect video created successfully!',
            'video_url': video_url,
            'filename': filename
        })
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/generate/transition', methods=['POST'])
def generate_transition_video():
    try:
        if 'image1' not in request.files or 'image2' not in request.files:
            return jsonify({'success': False, 'error': 'Two images are required'})
        
        image1 = request.files['image1']
        image2 = request.files['image2']
        duration = int(request.form.get('duration', 3))
        
        # Limit duration for Render free tier
        duration = min(duration, 5)
        
        # Save images temporarily
        img1_path = os.path.join(app.config['VIDEO_FOLDER'], f'temp1_{datetime.now().strftime("%Y%m%d_%H%M%S")}.jpg')
        img2_path = os.path.join(app.config['VIDEO_FOLDER'], f'temp2_{datetime.now().strftime("%Y%m%d_%H%M%S")}.jpg')
        image1.save(img1_path)
        image2.save(img2_path)
        
        # Generate video
        filename = f'transition_{datetime.now().strftime("%Y%m%d_%H%M%S")}.mp4'
        filepath = os.path.join(app.config['VIDEO_FOLDER'], filename)
        
        generator = VideoGenerator()
        generator.create_fade_transition(img1_path, img2_path, duration, filepath)
        
        # Cleanup temp images
        if os.path.exists(img1_path):
            os.remove(img1_path)
        if os.path.exists(img2_path):
            os.remove(img2_path)
        
        video_url = url_for('static', filename=f'videos/{filename}', _external=True)
        
        return jsonify({
            'success': True,
            'message': 'Transition video created successfully!',
            'video_url': video_url,
            'filename': filename
        })
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/generate/slideshow', methods=['POST'])
def generate_slideshow():
    try:
        texts = request.form.get('texts')
        duration = int(request.form.get('duration', 2))
        
        if not texts:
            return jsonify({'success': False, 'error': 'Texts are required'})
        
        text_list = [t.strip() for t in texts.split('\n') if t.strip()]
        
        if not text_list:
            return jsonify({'success': False, 'error': 'At least one text is required'})
        
        # Limit for Render free tier
        text_list = text_list[:5]  # Max 5 slides
        duration = min(duration, 3)
        
        # Generate video
        filename = f'slideshow_{datetime.now().strftime("%Y%m%d_%H%M%S")}.mp4'
        filepath = os.path.join(app.config['VIDEO_FOLDER'], filename)
        
        generator = VideoGenerator()
        generator.create_text_slideshow(text_list, duration, filepath)
        
        video_url = url_for('static', filename=f'videos/{filename}', _external=True)
        
        return jsonify({
            'success': True,
            'message': 'Slideshow created successfully!',
            'video_url': video_url,
            'filename': filename
        })
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

# Clean up old videos periodically (for Render)
@app.route('/cleanup', methods=['POST'])
def cleanup_videos():
    """Delete videos older than 1 hour to save space"""
    try:
        import time
        current_time = time.time()
        for filename in os.listdir(app.config['VIDEO_FOLDER']):
            filepath = os.path.join(app.config['VIDEO_FOLDER'], filename)
            if os.path.isfile(filepath):
                # Delete files older than 1 hour
                if current_time - os.path.getmtime(filepath) > 3600:
                    os.remove(filepath)
        return jsonify({'success': True, 'message': 'Cleanup completed'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("🎬 Flask Video Generator Started!")
    print(f"📱 Open your browser and go to: http://0.0.0.0:{port}")
    print("✨ Create amazing videos with text animations, effects, and transitions!")
    app.run(host='0.0.0.0', port=port, debug=False)
