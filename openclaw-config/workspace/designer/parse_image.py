import json
import base64

with open('image_response.json', 'r') as f:
    data = json.load(f)

image_data = data['predictions'][0]['bytesBase64Encoded']
with open('outputs/generated_robot.png', 'wb') as f:
    f.write(base64.b64decode(image_data))
print("Image saved to outputs/generated_robot.png")
