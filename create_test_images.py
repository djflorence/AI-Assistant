from PIL import Image, ImageDraw, ImageFont
import os

def create_test_images():
    # Create test_images directory if it doesn't exist
    test_dir = "test_images"
    if not os.path.exists(test_dir):
        os.makedirs(test_dir)
    
    # Create text sample image
    text_image = Image.new('RGB', (800, 400), color='white')
    draw = ImageDraw.Draw(text_image)
    
    # Add some text at different angles and sizes
    text_content = [
        ("Hello World!", (50, 50), 40, 0),
        ("Testing OCR", (50, 150), 60, 0),
        ("Rotated Text", (400, 200), 30, 45),
        ("Small text sample", (50, 300), 20, 0),
    ]
    
    for text, pos, size, angle in text_content:
        # Create font (using default font since custom fonts might not be available)
        font = ImageFont.load_default()
        
        # Create temporary image for rotated text
        if angle != 0:
            temp_img = Image.new('RGBA', (400, 100), (255, 255, 255, 0))
            temp_draw = ImageDraw.Draw(temp_img)
            temp_draw.text((0, 0), text, font=font, fill='black')
            rotated = temp_img.rotate(angle, expand=True)
            text_image.paste(rotated, pos, rotated)
        else:
            draw.text(pos, text, font=font, fill='black')
    
    text_image.save(os.path.join(test_dir, "text_sample.png"))
    
    # Create technical drawing sample
    tech_image = Image.new('RGB', (600, 400), color='white')
    draw = ImageDraw.Draw(tech_image)
    
    # Draw some geometric shapes
    draw.line([(50, 50), (550, 50)], fill='black', width=2)
    draw.line([(50, 50), (50, 350)], fill='black', width=2)
    draw.rectangle([(100, 100), (200, 200)], outline='black', width=2)
    draw.ellipse([(300, 100), (400, 200)], outline='black', width=2)
    draw.polygon([(450, 100), (500, 200), (400, 200)], outline='black', width=2)
    
    tech_image.save(os.path.join(test_dir, "technical_sample.png"))
    
    # Create photo-like sample
    photo_image = Image.new('RGB', (800, 600), color='white')
    draw = ImageDraw.Draw(photo_image)
    
    # Create a simple gradient background
    for y in range(600):
        for x in range(800):
            r = int(255 * (x / 800))
            g = int(255 * (y / 600))
            b = int(127 + 128 * ((x + y) / (800 + 600)))
            photo_image.putpixel((x, y), (r, g, b))
    
    # Add some shapes for testing
    draw.ellipse([(300, 200), (500, 400)], fill='red')
    draw.rectangle([(100, 100), (200, 200)], fill='blue')
    draw.polygon([(600, 300), (700, 400), (500, 400)], fill='green')
    
    photo_image.save(os.path.join(test_dir, "photo_sample.jpg"))
    
    print("Test images created successfully!")

if __name__ == "__main__":
    create_test_images()
