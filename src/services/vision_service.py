"""Vision service for processing images and extracting information."""
import os
import cv2
import numpy as np
from PIL import Image
from typing import Optional, Dict, List, Tuple, Union
import math
from scipy.stats import skew
import re
from sklearn.cluster import KMeans
import torch
from transformers import (
    AutoProcessor, 
    AutoModelForCausalLM, 
    pipeline,
    ViTImageProcessor, 
    ViTForImageClassification,
    DetrImageProcessor, 
    DetrForObjectDetection
)

class VisionService:
    def __init__(self):
        """Initialize the vision service."""
        # Initialize models as None - will load on demand
        self.caption_pipeline = None
        self.classifier_processor = None
        self.classifier = None
        self.object_detector_processor = None
        self.object_detector = None
        self._tesseract_available = False
        
        # Try to import pytesseract, but don't fail if not available
        try:
            import pytesseract
            self._tesseract = pytesseract
            self._tesseract_available = True
            pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        except ImportError:
            self._tesseract = None
        
        # Set device
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"PyTorch device: {self.device}")
        if self.device == "cuda":
            print(f"CUDA device: {torch.cuda.get_device_name()}")
            print(f"CUDA memory allocated: {torch.cuda.memory_allocated()/1024**2:.2f} MB")

    def load_caption_model(self):
        """Load the image captioning model on demand."""
        if self.caption_pipeline is None:
            try:
                self.caption_pipeline = pipeline(
                    "image-to-text",
                    model="nlpconnect/vit-gpt2-image-captioning",
                    device=self.device
                )
            except Exception as e:
                print(f"Error loading caption model: {e}")
                return False
        return True

    def load_classifier_model(self):
        """Load the image classification model on demand."""
        if self.classifier_processor is None or self.classifier is None:
            try:
                self.classifier_processor = ViTImageProcessor.from_pretrained('google/vit-base-patch16-224')
                self.classifier = ViTForImageClassification.from_pretrained('google/vit-base-patch16-224')
                self.classifier.to(self.device)
            except Exception as e:
                print(f"Error loading classifier model: {e}")
                return False
        return True

    def load_object_detector(self):
        """Load the object detection model on demand."""
        if self.object_detector_processor is None or self.object_detector is None:
            try:
                self.object_detector_processor = DetrImageProcessor.from_pretrained('facebook/detr-resnet-50')
                self.object_detector = DetrForObjectDetection.from_pretrained('facebook/detr-resnet-50')
                self.object_detector.to(self.device)
            except Exception as e:
                print(f"Error loading object detector: {e}")
                return False
        return True

    def preprocess_for_ocr(self, image):
        """Advanced preprocessing for better OCR accuracy."""
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Remove noise with bilateral filter
        denoised = cv2.bilateralFilter(gray, 9, 75, 75)
        
        # Check if image needs deskewing
        angle = self.get_skew_angle(denoised)
        if abs(angle) > 0.5:
            denoised = self.deskew(denoised, angle)
        
        # Enhance contrast using CLAHE
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        enhanced = clahe.apply(denoised)
        
        # Increase image size for better OCR
        scale_factor = 2
        enhanced = cv2.resize(enhanced, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_CUBIC)
        
        # Adaptive thresholding with optimized parameters
        block_size = 19  # Must be odd
        c = 9
        threshold = cv2.adaptiveThreshold(
            enhanced,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            block_size,
            c
        )
        
        # Remove noise and smooth edges
        kernel = np.ones((2, 2), np.uint8)
        threshold = cv2.morphologyEx(threshold, cv2.MORPH_CLOSE, kernel)
        threshold = cv2.morphologyEx(threshold, cv2.MORPH_OPEN, kernel)
        
        return threshold

    def get_skew_angle(self, image):
        """Calculate skew angle of text in image."""
        # Detect edges
        edges = cv2.Canny(image, 50, 150, apertureSize=3)
        
        # Use Hough transform to detect lines
        lines = cv2.HoughLines(edges, 1, np.pi/180, 100)
        
        if lines is not None:
            angles = []
            for rho, theta in lines[:, 0]:
                angle = np.degrees(theta) - 90
                if -45 <= angle <= 45:
                    angles.append(angle)
            
            if angles:
                return np.median(angles)
        
        return 0

    def deskew(self, image, angle):
        """Rotate image to correct skew."""
        (h, w) = image.shape
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        return rotated

    def extract_text(self, image_path):
        """Extract text from image with advanced preprocessing."""
        if not self._tesseract_available:
            return {"success": False, "error": "OCR is not available - Tesseract not installed"}
        
        try:
            # Read image
            image = cv2.imread(image_path)
            if image is None:
                return {"success": False, "error": "Failed to load image"}
            
            # Create multiple processed versions for better OCR
            processed_images = []
            
            # Original resized
            processed_images.append(cv2.resize(image, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC))
            
            # Grayscale with contrast enhancement
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(gray)
            processed_images.append(cv2.resize(enhanced, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC))
            
            # Thresholded version
            _, thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            processed_images.append(cv2.resize(thresh, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC))
            
            # Denoised version
            denoised = cv2.fastNlMeansDenoisingColored(image)
            processed_images.append(cv2.resize(denoised, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC))
            
            # Extract text from each processed image
            text_results = []
            for processed in processed_images:
                # Try different PSM modes
                for psm in [3, 6, 11]:  # 3=auto, 6=uniform block, 11=sparse text
                    config = f'--oem 3 --psm {psm}'
                    try:
                        text = self._tesseract.image_to_string(
                            processed,
                            config=config,
                            lang='eng+fra+deu+spa'
                        )
                        if text.strip():
                            text_results.append(text.strip())
                    except Exception as e:
                        continue
            
            # Combine and clean results
            if text_results:
                # Take the longest result as it's likely the most complete
                text = max(text_results, key=len)
                
                # Clean up text
                text = ' '.join(text.split())  # Normalize whitespace
                text = re.sub(r'[^\w\s.,!?@#$%&*()-]', '', text)  # Keep common punctuation
                text = re.sub(r'\s+', ' ', text).strip()  # Remove extra spaces
                
                return {"success": True, "text": text}
            else:
                return {"success": True, "text": ""}
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    def analyze_colors(self, image):
        """Analyze dominant colors in image."""
        try:
            # Convert image to RGB array
            img = Image.open(image).convert('RGB')
            img_array = np.array(img)
            
            # Reshape for KMeans
            pixels = img_array.reshape(-1, 3)
            
            # Use KMeans to find dominant colors
            n_colors = 5
            kmeans = KMeans(n_clusters=n_colors, n_init=10)
            kmeans.fit(pixels)
            
            # Get color counts
            labels = kmeans.labels_
            counts = np.bincount(labels)
            total_pixels = sum(counts)
            
            # Get colors and percentages
            colors = []
            for i in range(n_colors):
                rgb = kmeans.cluster_centers_[i].astype(int)
                percentage = (counts[i] / total_pixels) * 100
                colors.append({
                    "rgb": {
                        "red": int(rgb[0]),
                        "green": int(rgb[1]),
                        "blue": int(rgb[2])
                    },
                    "percentage": percentage
                })
            
            # Sort by percentage
            colors.sort(key=lambda x: x['percentage'], reverse=True)
            
            return {"success": True, "dominant_colors": colors}
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    def detect_objects(self, image_path):
        """Detect objects in image using DETR."""
        try:
            if not self.load_object_detector():
                return {"success": False, "error": "Failed to load object detector"}
            
            # Load and process image
            image = Image.open(image_path)
            inputs = self.object_detector_processor(images=image, return_tensors="pt")
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Get predictions
            outputs = self.object_detector(**inputs)
            
            # Convert outputs to probabilities
            probs = outputs.logits.softmax(-1)[0, :, :-1]
            keep = probs.max(-1).values > 0.7
            
            # Convert boxes to image coordinates
            target_sizes = torch.tensor([image.size[::-1]]).to(self.device)
            postprocessed_outputs = self.object_detector_processor.post_process_object_detection(
                outputs, target_sizes=target_sizes, threshold=0.7
            )[0]
            
            # Format results
            objects = []
            for score, label, box in zip(
                postprocessed_outputs['scores'],
                postprocessed_outputs['labels'],
                postprocessed_outputs['boxes']
            ):
                if score >= 0.7:  # High confidence threshold
                    objects.append({
                        "label": self.object_detector.config.id2label[label.item()],
                        "confidence": score.item(),
                        "box": box.tolist()
                    })
            
            return {"success": True, "objects": objects}
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    def analyze_image(self, image_path):
        """Comprehensive image analysis."""
        try:
            # Load models
            if not self.load_caption_model() or not self.load_classifier_model():
                return {"success": False, "error": "Failed to load models"}
            
            # Get image caption
            image = Image.open(image_path)
            captions = self.caption_pipeline(image)
            description = captions[0]['generated_text'] if captions else ""
            
            # Extract text
            text_result = self.extract_text(image_path)
            extracted_text = text_result.get('text', '') if text_result['success'] else ''
            
            # Analyze colors
            color_result = self.analyze_colors(image_path)
            
            # Detect objects
            object_result = self.detect_objects(image_path)
            
            # Detect shapes using OpenCV
            shapes_result = self.detect_shapes(cv2.imread(image_path))
            
            # Get image quality metrics
            quality_metrics = self.analyze_quality(image)
            
            return {
                "success": True,
                "description": description,
                "extracted_text": extracted_text,
                "color_analysis": color_result if color_result['success'] else {"dominant_colors": []},
                "detected_objects": object_result['objects'] if object_result['success'] else [],
                "shapes_detected": shapes_result['shapes'] if shapes_result['success'] else [],
                "quality_metrics": quality_metrics,
                "error": None
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    def detect_shapes(self, image):
        """Detect basic shapes in image using OpenCV."""
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Blur to reduce noise
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Find edges with optimized parameters
            edges = cv2.Canny(blurred, 30, 100)  # Lower threshold to detect more edges
            
            # Find contours with hierarchy to filter nested shapes
            contours, hierarchy = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            
            # Filter out small contours and nested shapes
            min_area = image.shape[0] * image.shape[1] * 0.001  # Minimum 0.1% of image area
            shapes = []
            
            for i, contour in enumerate(contours):
                # Skip if contour is too small
                area = cv2.contourArea(contour)
                if area < min_area:
                    continue
                
                # Skip if this is a child contour (likely noise or internal detail)
                if hierarchy[0][i][3] != -1:  # Has parent
                    continue
                
                # Get perimeter and approximate shape
                peri = cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, 0.02 * peri, True)  # More precise approximation
                
                # Calculate shape metrics
                x, y, w, h = cv2.boundingRect(approx)
                aspect_ratio = float(w) / h
                extent = float(area) / (w * h)
                hull = cv2.convexHull(contour)
                hull_area = cv2.contourArea(hull)
                solidity = float(area) / hull_area if hull_area > 0 else 0
                
                # Identify shape based on vertices and metrics
                vertices = len(approx)
                shape_type = ""
                confidence = 0.0
                
                if vertices == 3 and solidity > 0.9:
                    shape_type = "triangle"
                    confidence = solidity
                elif vertices == 4:
                    # Square vs rectangle detection
                    if 0.95 <= aspect_ratio <= 1.05 and extent > 0.8:
                        shape_type = "square"
                        confidence = min(solidity, extent)
                    else:
                        shape_type = "rectangle"
                        confidence = extent
                elif vertices == 5 and solidity > 0.8:
                    shape_type = "pentagon"
                    confidence = solidity
                elif vertices == 6 and solidity > 0.8:
                    shape_type = "hexagon"
                    confidence = solidity
                elif vertices > 6:
                    # Circle detection
                    circularity = 4 * math.pi * area / (peri * peri)
                    if circularity > 0.85 and 0.95 <= aspect_ratio <= 1.05:
                        shape_type = "circle"
                        confidence = circularity
                    else:
                        shape_type = "polygon"
                        confidence = solidity
                
                # Only add shapes with good confidence
                if shape_type and confidence > 0.7:
                    shapes.append({
                        "type": shape_type,
                        "confidence": confidence,
                        "vertices": vertices,
                        "area": area,
                        "metrics": {
                            "solidity": solidity,
                            "extent": extent,
                            "aspect_ratio": aspect_ratio
                        }
                    })
            
            # Remove duplicate detections
            filtered_shapes = []
            for shape in shapes:
                # Check if similar shape already exists
                is_duplicate = False
                for existing in filtered_shapes:
                    if (existing["type"] == shape["type"] and
                        abs(existing["area"] - shape["area"]) < min_area):
                        is_duplicate = True
                        break
                if not is_duplicate:
                    filtered_shapes.append(shape)
            
            return {"success": True, "shapes": filtered_shapes}
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    def analyze_quality(self, image):
        """Analyze image quality metrics."""
        try:
            # Convert to grayscale for certain metrics
            gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
            
            # Calculate blur score using Laplacian variance
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            blur_score = min(laplacian_var / 500 * 100, 100)  # Normalize to 0-100
            
            # Calculate brightness
            brightness = np.mean(gray)
            brightness_score = brightness / 255 * 100
            
            # Calculate contrast using standard deviation
            contrast = np.std(gray)
            contrast_score = min(contrast / 128 * 100, 100)
            
            return {
                "blur_score": blur_score,
                "brightness_score": brightness_score,
                "contrast_score": contrast_score,
                "resolution": image.size
            }
            
        except Exception as e:
            print(f"Error analyzing quality: {e}")
            return {
                "blur_score": 0,
                "brightness_score": 0,
                "contrast_score": 0,
                "resolution": (0, 0)
            }

    def enhance_image(self, image_path, output_path):
        """Enhance image quality by adjusting contrast, brightness, and sharpness."""
        try:
            # Open image
            image = Image.open(image_path)
            
            # Enhance contrast
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.5)
            
            # Enhance brightness
            enhancer = ImageEnhance.Brightness(image)
            image = enhancer.enhance(1.2)
            
            # Enhance sharpness
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.5)
            
            # Save enhanced image
            image.save(output_path)
            
            return {"success": True, "path": output_path}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
