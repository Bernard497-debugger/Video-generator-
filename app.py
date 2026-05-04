import os
import requests
import json
import time
import base64
from flask import Flask, render_template, request, jsonify, url_for, send_file
from datetime import datetime
from io import BytesIO
import tempfile
import traceback

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

# Hugging Face API Configuration
HF_API_TOKEN = os.environ.get('HF_API_TOKEN')  # Get token from https://huggingface.co/settings/tokens
if not HF_API_TOKEN:
    print("⚠️ WARNING: HF_API_TOKEN not set! Please set it in Render environment variables.")

# Available free models on Hugging Face
MODELS = {
    'text_to_video': 'damo-vilab/text-to-video-ms-1.7b',
    'image_to_video': 'ali-vilab/modelscope-damo-text-to-video-synthesis',
    'zero_scope': 'cerspense/zeroscope_v2_576w',
    'animatediff': 'wyw3d/AnimateDiff'
}

# Create templates folder
os.makedirs('templates', exist_ok=True)

# HTML Template
INDEX_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Video Generator - Hugging Face API</title>
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
        
        .content {
            padding: 40px;
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
            padding: 20px;
        }
        
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            animation: spin 1s linear infinite;
            margin: 0 auto 10px;
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
        
        .alert-info {
            background: #d1ecf1;
            color: #0c5460;
            border: 1px solid #bee5eb;
        }
        
        .download-btn {
            display: inline-block;
            background: #28a745;
            color: white;
            text-decoration: none;
            padding: 10px 20px;
            border-radius: 5px;
            margin-top: 10px;
            text-align: center;
        }
        
        .info-box {
            background: #e7f3ff;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 14px;
        }
        
        .info-box code {
            background: #fff;
            padding: 2px 5px;
            border-radius: 3px;
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
            <p>Powered by Hugging Face AI Models</p>
        </div>
        
        <div class="content">
            <div id="alertContainer"></div>
            
            <div class="info-box">
                ℹ️ <strong>Free API Info:</strong> Using Hugging Face's free inference API. 
                First request may take 30-60 seconds as models load. 
                <strong>Get your free token:</strong> <a href="https://huggingface.co/settings/tokens" target="_blank">huggingface.co/settings/tokens</a>
            </div>
            
            <form id="videoForm">
                <div class="form-group">
                    <label>🤖 Select AI Model:</label>
                    <select name="model" id="modelSelect">
                        <option value="text_to_video">Text to Video (Damo-Vilab)</option>
                        <option value="zero_scope">ZeroScope v2 (576p)</option>
                        <option value="animatediff">AnimateDiff</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label>📝 Enter your prompt:</label>
                    <textarea name="prompt" required placeholder="Describe the video you want to generate...&#10;&#10;Example: 'A beautiful sunset over mountains with birds flying'"></textarea>
                </div>
                
                <div class="form-group">
                    <label>🎨 Negative prompt (optional):</label>
                    <textarea name="negative_prompt" placeholder="What to avoid...&#10;&#10;Example: 'low quality, blurry, distorted'"></textarea>
                </div>
                
                <div class="form-group">
                    <label>⏱️ Number of frames (optional):</label>
                    <input type="number" name="num_frames" placeholder="16 or 24" min="8" max="48" step="8">
                </div>
                
                <button type="submit" id="generateBtn">🚀 Generate Video</button>
            </form>
            
            <div class="loading" id="loading">
                <div class="spinner"></div>
                <p>🎥 Generating your video with AI... This may take 30-60 seconds</p>
                <p style="font-size: 12px; margin-top: 10px;">Models are loading on first request</p>
            </div>
            
            <div class="result" id="result">
                <h3>✨ Your Generated Video:</h3>
                <video id="videoPlayer" controls>
                    Your browser does not support the video tag.
                </video>
                <div style="text-align: center; margin-top: 15px;">
                    <a id="downloadLink" class="download-btn">📥 Download Video</a>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        const form = document.getElementById('videoForm');
        const loading = document.getElementById('loading');
        const result = document.getElementById('result');
        const videoPlayer = document.getElementById('videoPlayer');
        const downloadLink = document.getElementById('downloadLink');
        const alertContainer = document.getElementById('alertContainer');
        const generateBtn = document.getElementById('generateBtn');
        
        function showAlert(message, type) {
            alertContainer.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
            setTimeout(() => {
                alertContainer.innerHTML = '';
            }, 5000);
        }
        
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            // Hide previous result
            result.style.display = 'none';
            loading.style.display = 'block';
            generateBtn.disabled = true;
            
            // Collect form data
            const formData = new FormData(form);
            
            try {
                const response = await fetch('/generate_video', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                if (data.success) {
                    showAlert('✅ Video generated successfully!', 'success');
                    videoPlayer.src = data.video_url;
                    downloadLink.href = data.video_url;
                    result.style.display = 'block';
                    
                    // Scroll to video
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
        
        // Check API status on load
        async function checkAPI() {
            const response = await fetch('/api_status');
            const data = await response.json();
            if (!data.has_token) {
                showAlert('⚠️ API token not configured. Please set HF_API_TOKEN in environment variables.', 'info');
            }
        }
        
        checkAPI();
    </script>
</body>
</html>
'''

# Create template
with open('templates/index.html', 'w') as f:
    f.write(INDEX_TEMPLATE)

class HuggingFaceVideoGenerator:
    def __init__(self, api_token):
        self.api_token = api_token
        self.headers = {"Authorization": f"Bearer {api_token}"}
    
    def query(self, model_id, payload):
        """Query Hugging Face API"""
        api_url = f"https://api-inference.huggingface.co/models/{model_id}"
        
        try:
            response = requests.post(api_url, headers=self.headers, json=payload, timeout=120)
            
            # Handle model loading
            if response.status_code == 503:
                # Model is loading, wait and retry
                wait_time = 20
                return {
                    'status': 'loading',
                    'message': f"Model is loading. Please wait {wait_time} seconds...",
                    'wait_time': wait_time
                }
            
            if response.status_code == 200:
                return {
                    'status': 'success',
                    'content': response.content
                }
            else:
                return {
                    'status': 'error',
                    'message': f"API Error {response.status_code}: {response.text}"
                }
        except requests.exceptions.Timeout:
            return {
                'status': 'error',
                'message': "Request timed out. The model might be slow. Try again."
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def generate_text_video(self, prompt, negative_prompt=None, num_frames=None):
        """Generate video from text prompt"""
        # Prepare payload based on model
        payload = {
            "inputs": prompt,
            "parameters": {}
        }
        
        if negative_prompt:
            payload["parameters"]["negative_prompt"] = negative_prompt
        
        if num_frames:
            payload["parameters"]["num_frames"] = num_frames
        
        # Use different models based on what's available
        models_to_try = [
            "damo-vilab/text-to-video-ms-1.7b",
            "cerspense/zeroscope_v2_576w",
            "ali-vilab/modelscope-damo-text-to-video-synthesis"
        ]
        
        for model in models_to_try:
            result = self.query(model, payload)
            if result['status'] == 'success':
                return result
            elif result['status'] == 'loading':
                return result
        
        return {
            'status': 'error',
            'message': "All models failed. Please try again later."
        }
    
    def generate_with_model(self, model_name, prompt, negative_prompt=None, num_frames=None):
        """Generate with specific model"""
        model_path = MODELS.get(model_name, MODELS['text_to_video'])
        
        payload = {
            "inputs": prompt,
            "parameters": {}
        }
        
        if negative_prompt:
            payload["parameters"]["negative_prompt"] = negative_prompt
        
        if num_frames:
            payload["parameters"]["num_frames"] = num_frames
        
        result = self.query(model_path, payload)
        
        # Handle model loading - wait and retry
        if result['status'] == 'loading' and result.get('wait_time'):
            # Wait for model to load
            time.sleep(result['wait_time'])
            # Retry once
            result = self.query(model_path, payload)
        
        return result

# Flask Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api_status')
def api_status():
    return jsonify({
        'has_token': bool(HF_API_TOKEN),
        'models_available': list(MODELS.keys())
    })

@app.route('/generate_video', methods=['POST'])
def generate_video():
    if not HF_API_TOKEN:
        return jsonify({
            'success': False,
            'error': 'Hugging Face API token not configured. Please set HF_API_TOKEN environment variable.'
        })
    
    try:
        prompt = request.form.get('prompt')
        if not prompt:
            return jsonify({'success': False, 'error': 'Prompt is required'})
        
        negative_prompt = request.form.get('negative_prompt')
        num_frames = request.form.get('num_frames')
        model_name = request.form.get('model', 'text_to_video')
        
        if num_frames:
            num_frames = int(num_frames)
        
        # Initialize generator
        generator = HuggingFaceVideoGenerator(HF_API_TOKEN)
        
        # Generate video
        result = generator.generate_with_model(model_name, prompt, negative_prompt, num_frames)
        
        if result['status'] == 'success':
            # Save video to temp file
            temp_dir = tempfile.gettempdir()
            filename = f"ai_video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
            filepath = os.path.join(temp_dir, filename)
            
            with open(filepath, 'wb') as f:
                f.write(result['content'])
            
            # Create download URL
            video_url = url_for('download_video', filename=filename, _external=True)
            
            return jsonify({
                'success': True,
                'video_url': video_url,
                'filename': filename,
                'file_size': len(result['content']),
                'message': 'Video generated successfully!'
            })
        
        elif result['status'] == 'loading':
            return jsonify({
                'success': False,
                'error': f"Model is loading. Please wait 30 seconds and try again. {result.get('message', '')}"
            })
        
        else:
            return jsonify({
                'success': False,
                'error': result.get('message', 'Unknown error occurred')
            })
            
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Error: {str(e)}'
        })

@app.route('/download/<filename>')
def download_video(filename):
    """Download generated video"""
    filepath = os.path.join(tempfile.gettempdir(), filename)
    if os.path.exists(filepath):
        return send_file(filepath, mimetype='video/mp4', as_attachment=True)
    return jsonify({'error': 'File not found'}), 404

@app.route('/cleanup', methods=['POST'])
def cleanup():
    """Clean up old video files (older than 1 hour)"""
    try:
        temp_dir = tempfile.gettempdir()
        current_time = time.time()
        deleted = 0
        
        for filename in os.listdir(temp_dir):
            if filename.startswith('ai_video_') and filename.endswith('.mp4'):
                filepath = os.path.join(temp_dir, filename)
                if current_time - os.path.getmtime(filepath) > 3600:
                    os.remove(filepath)
                    deleted += 1
        
        return jsonify({'success': True, 'deleted': deleted})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Test endpoint to check if API is working
@app.route('/test_model')
def test_model():
    """Test if Hugging Face API is accessible"""
    if not HF_API_TOKEN:
        return jsonify({'error': 'No API token configured'})
    
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
    api_url = "https://api-inference.huggingface.co/models/damo-vilab/text-to-video-ms-1.7b"
    
    try:
        # Test with a simple request
        response = requests.get(api_url, headers=headers)
        return jsonify({
            'status': 'connected',
            'response_code': response.status_code,
            'model_status': 'loading' if response.status_code == 503 else 'ready'
        })
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    
    if not HF_API_TOKEN:
        print("\n" + "="*50)
        print("⚠️  WARNING: HF_API_TOKEN not set!")
        print("To use this app, you need a Hugging Face API token:")
        print("1. Sign up at https://huggingface.co/join")
        print("2. Get your token at https://huggingface.co/settings/tokens")
        print("3. Set it as environment variable: export HF_API_TOKEN='your_token_here'")
        print("="*50 + "\n")
    
    print("🎬 AI Video Generator Started!")
    print(f"📱 Open your browser and go to: http://0.0.0.0:{port}")
    print("✨ Generating videos with Hugging Face AI")
    app.run(host='0.0.0.0', port=port, debug=False)
