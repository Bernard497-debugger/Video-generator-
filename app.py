import os
import tempfile
import torch
from flask import Flask, render_template, request, jsonify, url_for, send_file
from datetime import datetime
import traceback
import shutil
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

# Create templates folder
os.makedirs('templates', exist_ok=True)

# Global variable to cache the model
model_pipe = None

def get_model():
    """Load model once and cache it"""
    global model_pipe
    if model_pipe is None:
        try:
            from diffusers import DiffusionPipeline
            from diffusers.utils import export_to_video
            
            print("🔄 Loading Zeroscope model... This may take 2-3 minutes on first load")
            
            # Use CPU - works on Render free tier
            model_pipe = DiffusionPipeline.from_pretrained(
                "cerspense/zeroscope_v2_576w",
                torch_dtype=torch.float32
            ).to("cpu")
            
            print("✅ Model loaded successfully!")
            
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            raise
    
    return model_pipe

# HTML Template
INDEX_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Video Generator - Free & Local</title>
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
            max-width: 900px;
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
            font-size: 2.2em;
            margin-bottom: 10px;
        }
        
        .header p {
            opacity: 0.9;
        }
        
        .badge {
            display: inline-block;
            background: rgba(255,255,255,0.2);
            padding: 5px 10px;
            border-radius: 20px;
            font-size: 12px;
            margin-top: 10px;
        }
        
        .content {
            padding: 40px;
        }
        
        .info-box {
            background: #e7f3ff;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 25px;
            border-left: 4px solid #667eea;
        }
        
        .info-box h3 {
            color: #667eea;
            margin-bottom: 10px;
        }
        
        .info-box ul {
            margin-left: 20px;
            color: #555;
        }
        
        .info-box li {
            margin: 5px 0;
        }
        
        .form-group {
            margin-bottom: 25px;
        }
        
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: bold;
            color: #333;
        }
        
        input, select, textarea {
            width: 100%;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 14px;
            transition: all 0.3s;
        }
        
        input:focus, select:focus, textarea:focus {
            outline: none;
            border-color: #667eea;
        }
        
        textarea {
            resize: vertical;
            min-height: 100px;
        }
        
        button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 14px 40px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            font-weight: bold;
            width: 100%;
            transition: transform 0.2s;
        }
        
        button:hover {
            transform: translateY(-2px);
        }
        
        button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        
        .loading {
            display: none;
            text-align: center;
            padding: 30px;
        }
        
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            animation: spin 1s linear infinite;
            margin: 0 auto 15px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .result {
            margin-top: 30px;
            display: none;
        }
        
        video {
            width: 100%;
            border-radius: 10px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.2);
            margin-top: 20px;
        }
        
        .alert {
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        
        .alert-success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        
        .alert-error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        
        .alert-warning {
            background: #fff3cd;
            color: #856404;
            border: 1px solid #ffeeba;
        }
        
        .download-btn {
            display: inline-block;
            background: #28a745;
            color: white;
            text-decoration: none;
            padding: 10px 20px;
            border-radius: 5px;
            margin-top: 15px;
            text-align: center;
        }
        
        .example-prompts {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin-top: 10px;
        }
        
        .example-prompt {
            background: #f0f0f0;
            padding: 5px 12px;
            border-radius: 20px;
            cursor: pointer;
            font-size: 12px;
            transition: background 0.2s;
        }
        
        .example-prompt:hover {
            background: #e0e0e0;
        }
        
        @media (max-width: 768px) {
            .content {
                padding: 20px;
            }
            
            .header h1 {
                font-size: 1.5em;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎬 AI Video Generator</h1>
            <p>Powered by Zeroscope v2 - Runs entirely on CPU</p>
            <div class="badge">✨ No API Keys Required | Free & Open Source</div>
        </div>
        
        <div class="content">
            <div id="alertContainer"></div>
            
            <div class="info-box">
                <h3>ℹ️ How it works</h3>
                <ul>
                    <li>✓ Uses Zeroscope v2 AI model running locally on CPU</li>
                    <li>✓ No API keys or external services needed</li>
                    <li>✓ First generation takes 2-3 minutes (model loading)</li>
                    <li>✓ Subsequent generations take 30-60 seconds</li>
                    <li>✓ Videos are 576p resolution, 16 frames</li>
                </ul>
            </div>
            
            <form id="videoForm">
                <div class="form-group">
                    <label>📝 Enter your prompt:</label>
                    <textarea name="prompt" id="prompt" required placeholder="Describe the video you want to generate...&#10;&#10;Example: 'A beautiful sunset over mountains with birds flying'"></textarea>
                    <div class="example-prompts">
                        <span class="example-prompt" onclick="setPrompt('A dog running on a sunny beach')">🐕 Dog on beach</span>
                        <span class="example-prompt" onclick="setPrompt('A cat playing with a ball of yarn')">🐱 Cat playing</span>
                        <span class="example-prompt" onclick="setPrompt('A car driving through a rainy city street')">🚗 Rainy city</span>
                        <span class="example-prompt" onclick="setPrompt('A spaceship flying through colorful nebula')">🚀 Spaceship</span>
                        <span class="example-prompt" onclick="setPrompt('A butterfly flying over a flower garden')">🦋 Butterfly</span>
                    </div>
                </div>
                
                <div class="form-group">
                    <label>🎬 Number of frames (4-24, more frames = longer but slower):</label>
                    <input type="range" name="num_frames" id="num_frames" min="8" max="24" step="4" value="16">
                    <span id="framesValue" style="display: inline-block; margin-left: 10px;">16 frames (~1.5 seconds)</span>
                </div>
                
                <div class="form-group">
                    <label>⚙️ Inference steps (15-50, more steps = better quality but slower):</label>
                    <input type="range" name="num_steps" id="num_steps" min="15" max="50" step="5" value="25">
                    <span id="stepsValue" style="display: inline-block; margin-left: 10px;">25 steps</span>
                </div>
                
                <button type="submit" id="generateBtn">🚀 Generate Video</button>
            </form>
            
            <div class="loading" id="loading">
                <div class="spinner"></div>
                <p id="loadingText">🎥 Generating your video with AI...</p>
                <p style="font-size: 12px; margin-top: 10px; color: #666;">First generation loads the model (2-3 min). Please be patient!</p>
            </div>
            
            <div class="result" id="result">
                <h3>✨ Your Generated Video:</h3>
                <video id="videoPlayer" controls>
                    Your browser does not support the video tag.
                </video>
                <div style="text-align: center;">
                    <a id="downloadLink" class="download-btn">📥 Download Video</a>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Update slider values
        document.getElementById('num_frames').addEventListener('input', function() {
            document.getElementById('framesValue').textContent = this.value + ' frames (~' + (this.value / 10.7).toFixed(1) + ' seconds)';
        });
        
        document.getElementById('num_steps').addEventListener('input', function() {
            document.getElementById('stepsValue').textContent = this.value + ' steps';
        });
        
        function setPrompt(text) {
            document.getElementById('prompt').value = text;
        }
        
        function showAlert(message, type) {
            const alertContainer = document.getElementById('alertContainer');
            alertContainer.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
            setTimeout(() => {
                alertContainer.innerHTML = '';
            }, 5000);
        }
        
        const form = document.getElementById('videoForm');
        const loading = document.getElementById('loading');
        const result = document.getElementById('result');
        const videoPlayer = document.getElementById('videoPlayer');
        const downloadLink = document.getElementById('downloadLink');
        const generateBtn = document.getElementById('generateBtn');
        const loadingText = document.getElementById('loadingText');
        
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            result.style.display = 'none';
            loading.style.display = 'block';
            generateBtn.disabled = true;
            loadingText.textContent = '🎥 Generating your video with AI... This may take 30-60 seconds';
            
            const formData = new FormData(form);
            const startTime = Date.now();
            
            try {
                const response = await fetch('/generate_video', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                const elapsedTime = ((Date.now() - startTime) / 1000).toFixed(1);
                
                if (data.success) {
                    showAlert(`✅ Video generated in ${elapsedTime} seconds!`, 'success');
                    videoPlayer.src = data.video_url;
                    downloadLink.href = data.video_url;
                    result.style.display = 'block';
                    result.scrollIntoView({ behavior: 'smooth' });
                } else {
                    showAlert('❌ Error: ' + data.error, 'error');
                }
            } catch (error) {
                showAlert('❌ Network error: ' + error.message, 'error');
            } finally {
                loading.style.display = 'none';
                generateBtn.disabled = false;
            }
        });
        
        // Check if model is loaded on page load
        async function checkStatus() {
            const response = await fetch('/model_status');
            const data = await response.json();
            if (data.loaded) {
                showAlert('✅ Model is loaded and ready!', 'success');
            } else {
                showAlert('⏳ Model will load on first video generation', 'warning');
            }
        }
        
        checkStatus();
    </script>
</body>
</html>
'''

# Save template
with open('templates/index.html', 'w') as f:
    f.write(INDEX_TEMPLATE)

# Flask Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/model_status')
def model_status():
    """Check if model is loaded"""
    return jsonify({'loaded': model_pipe is not None})

@app.route('/generate_video', methods=['POST'])
def generate_video():
    """Generate video using Zeroscope model"""
    try:
        prompt = request.form.get('prompt')
        if not prompt:
            return jsonify({'success': False, 'error': 'Prompt is required'})
        
        num_frames = int(request.form.get('num_frames', 16))
        num_steps = int(request.form.get('num_steps', 25))
        
        # Limits for CPU performance
        num_frames = min(max(num_frames, 8), 24)
        num_steps = min(max(num_steps, 15), 40)
        
        print(f"🎬 Generating: '{prompt}' | Frames: {num_frames} | Steps: {num_steps}")
        
        # Get the model (loads if not already loaded)
        try:
            pipe = get_model()
        except Exception as e:
            return jsonify({'success': False, 'error': f'Failed to load model: {str(e)}'})
        
        # Generate video
        from diffusers.utils import export_to_video
        
        print("🔄 Running inference...")
        result = pipe(
            prompt,
            num_frames=num_frames,
            num_inference_steps=num_steps,
            height=320,  # Smaller for faster generation on CPU
            width=576
        )
        
        video_frames = result.frames[0]
        
        # Save video
        temp_dir = tempfile.gettempdir()
        filename = f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        filepath = os.path.join(temp_dir, filename)
        
        export_to_video(video_frames, filepath, fps=8)
        
        # Check if file was created
        if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
            return jsonify({'success': False, 'error': 'Video file is empty'})
        
        video_url = url_for('download_video', filename=filename, _external=True)
        
        print(f"✅ Video saved: {filepath} ({os.path.getsize(filepath)} bytes)")
        
        return jsonify({
            'success': True,
            'video_url': video_url,
            'filename': filename,
            'frames': num_frames,
            'steps': num_steps
        })
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/download/<filename>')
def download_video(filename):
    """Download generated video"""
    filepath = os.path.join(tempfile.gettempdir(), filename)
    if os.path.exists(filepath):
        return send_file(filepath, mimetype='video/mp4', as_attachment=True)
    return jsonify({'error': 'File not found'}), 404

@app.route('/cleanup', methods=['POST'])
def cleanup():
    """Clean up old video files"""
    try:
        temp_dir = tempfile.gettempdir()
        current_time = datetime.now().timestamp()
        deleted = 0
        
        for filename in os.listdir(temp_dir):
            if filename.startswith('video_') and filename.endswith('.mp4'):
                filepath = os.path.join(temp_dir, filename)
                if current_time - os.path.getmtime(filepath) > 3600:
                    os.remove(filepath)
                    deleted += 1
        
        return jsonify({'success': True, 'deleted': deleted})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    
    print("\n" + "="*60)
    print("🎬 AI Video Generator - Zeroscope v2")
    print("="*60)
    print("\n📝 Features:")
    print("   • No API keys required")
    print("   • Runs entirely on CPU")
    print("   • First load takes 2-3 minutes")
    print("   • Each video: 30-60 seconds generation time")
    print(f"\n🌐 Open: http://0.0.0.0:{port}")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=port, debug=False)
