document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const tabs = document.querySelectorAll('.tab');
    const tabContents = document.querySelectorAll('.tab-content');
    const cameraView = document.getElementById('camera-view');
    const cameraPreview = document.getElementById('camera-preview');
    const captureBtn = document.getElementById('capture-btn');
    const retakeBtn = document.getElementById('retake-btn');
    const processBtn = document.getElementById('process-btn');
    const fileInput = document.getElementById('file-input');
    const uploadPreview = document.getElementById('upload-preview');
    const uploadBtn = document.getElementById('upload-btn');
    const cameraResultContainer = document.getElementById('camera-result-container');
    const uploadResultContainer = document.getElementById('upload-result-container');
    const cameraLoading = document.getElementById('camera-loading');
    const uploadLoading = document.getElementById('upload-loading');
    
    // Variables for camera functionality
    let stream = null;
    let capturedImage = null;
    let uploadedFile = null;
    
    // Tab switching
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // Remove active class from all tabs and contents
            tabs.forEach(t => t.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            
            // Add active class to clicked tab and corresponding content
            tab.classList.add('active');
            const target = tab.getAttribute('data-target');
            document.getElementById(target).classList.add('active');
            
            // If switching to camera tab, initialize camera
            if (target === 'camera-tab-content') {
                initializeCamera();
            } else {
                // Stop camera if switching away
                stopCamera();
            }
        });
    });
    
    // Initialize camera
    function initializeCamera() {
        if (stream) return; // Camera already initialized
        
        if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
            navigator.mediaDevices.getUserMedia({ video: true })
                .then(function(mediaStream) {
                    stream = mediaStream;
                    cameraView.srcObject = mediaStream;
                    cameraView.style.display = 'block';
                    cameraPreview.style.display = 'none';
                    captureBtn.style.display = 'block';
                    retakeBtn.style.display = 'none';
                    processBtn.style.display = 'none';
                    cameraView.play();
                })
                .catch(function(error) {
                    console.error('Camera access error:', error);
                    alert('Could not access the camera. Please check permissions.');
                });
        } else {
            alert('Your browser does not support camera access.');
        }
    }
    
    // Stop camera stream
    function stopCamera() {
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
            stream = null;
        }
    }
    
    // Capture image from camera
    captureBtn.addEventListener('click', function() {
        if (!stream) return;
        
        // Create canvas and draw the current video frame
        const canvas = document.createElement('canvas');
        canvas.width = cameraView.videoWidth;
        canvas.height = cameraView.videoHeight;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(cameraView, 0, 0, canvas.width, canvas.height);
        
        // Get image as data URL
        capturedImage = canvas.toDataURL('image/jpeg');
        
        // Display the captured image
        cameraPreview.src = capturedImage;
        cameraView.style.display = 'none';
        cameraPreview.style.display = 'block';
        captureBtn.style.display = 'none';
        retakeBtn.style.display = 'inline-block';
        processBtn.style.display = 'inline-block';
    });
    
    // Retake photo
    retakeBtn.addEventListener('click', function() {
        capturedImage = null;
        cameraView.style.display = 'block';
        cameraPreview.style.display = 'none';
        captureBtn.style.display = 'block';
        retakeBtn.style.display = 'none';
        processBtn.style.display = 'none';
    });
    
    // Process captured image
    processBtn.addEventListener('click', function() {
        if (!capturedImage) return;
        
        // Show loading
        cameraLoading.style.display = 'block';
        cameraResultContainer.innerHTML = '';
        
        // Prepare request data
        const requestData = {
            image_data: capturedImage
        };
        
        // Send to API
        fetch('/ocr/camera', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        })
        .then(response => response.json())
        .then(data => {
            cameraLoading.style.display = 'none';
            displayResults(data, cameraResultContainer);
        })
        .catch(error => {
            cameraLoading.style.display = 'none';
            cameraResultContainer.innerHTML = `
                <div class="error-message">
                    Error processing image: ${error.message}
                </div>
            `;
            console.error('Error:', error);
        });
    });
    
    // File upload preview
    fileInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (!file) return;
        
        // Store the file for later upload
        uploadedFile = file;
        
        // Preview the selected file
        const reader = new FileReader();
        reader.onload = function(event) {
            uploadPreview.src = event.target.result;
            uploadPreview.style.display = 'block';
            uploadBtn.disabled = false;
        };
        reader.readAsDataURL(file);
    });
    
    // Upload and process file
    uploadBtn.addEventListener('click', function() {
        if (!uploadedFile) return;
        
        // Show loading
        uploadLoading.style.display = 'block';
        uploadResultContainer.innerHTML = '';
        
        // Create form data
        const formData = new FormData();
        formData.append('file', uploadedFile);
        
        // Send to API
        fetch('/ocr/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            uploadLoading.style.display = 'none';
            displayResults(data, uploadResultContainer);
        })
        .catch(error => {
            uploadLoading.style.display = 'none';
            uploadResultContainer.innerHTML = `
                <div class="error-message">
                    Error processing file: ${error.message}
                </div>
            `;
            console.error('Error:', error);
        });
    });
    
    // Display OCR results
    function displayResults(data, container) {
        container.innerHTML = '';
        
        if (data.status === 'error') {
            container.innerHTML = `
                <div class="error-message">
                    ${data.message || 'An error occurred during processing'}
                </div>
            `;
            return;
        }
        
        if (data.text && data.text.length > 0) {
            const resultHeader = document.createElement('h3');
            resultHeader.textContent = 'Extracted Text:';
            container.appendChild(resultHeader);
            
            data.text.forEach(text => {
                const textItem = document.createElement('div');
                textItem.className = 'result-item';
                textItem.textContent = text;
                container.appendChild(textItem);
            });
        } else {
            container.innerHTML = `
                <div class="error-message">
                    No text detected in the image
                </div>
            `;
        }
    }
    
    // Initialize camera tab by default
    document.querySelector('.tab[data-target="camera-tab-content"]').click();
});
