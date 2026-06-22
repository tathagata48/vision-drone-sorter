import cv2
import numpy as np
import socket
import time

# 1. Load the captured image
image_path = r"C:\Unity\card_screenshot.png"
image = cv2.imread(image_path)

if image is None:
    print(f"Error: Could not look up or open image at {image_path}")
    exit()

# Convert BGR image to HSV
hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

# 2. Define color ranges
lower_green = np.array([35, 100, 100])
upper_green = np.array([85, 255, 255])

lower_blue = np.array([100, 100, 100])
upper_blue = np.array([130, 255, 255])

# Red wraps around 0 and 180 in HSV, so we use two distinct ranges
lower_red1 = np.array([0, 100, 100])
upper_red1 = np.array([10, 255, 255])
lower_red2 = np.array([170, 100, 100])
upper_red2 = np.array([180, 255, 255])

# 3. Create and combine masks
mask_green = cv2.inRange(hsv_image, lower_green, upper_green)
mask_blue = cv2.inRange(hsv_image, lower_blue, upper_blue)

mask_red1 = cv2.inRange(hsv_image, lower_red1, upper_red1)
mask_red2 = cv2.inRange(hsv_image, lower_red2, upper_red2)
mask_red = mask_red1 + mask_red2  # Combines both ends of the red spectrum

# Combine all masks together to find all contours at once
combined_mask = mask_red + mask_green + mask_blue

# 4. Find contours in the combined mask
contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

# Initialize counters and sequence array
red_count = 0
green_count = 0
blue_count = 0
colors = []

# 5. Process contours and identify colors
for contour in contours:
    x, y, w, h = cv2.boundingRect(contour)
    area = cv2.contourArea(contour)
    
    if area > 100:  # Adjust threshold based on item size
        # Check coordinates against individual masks to classify color
        if np.any(mask_red[contour[0][0][1], contour[0][0][0]]):
            cv2.rectangle(image, (x, y), (x + w, y + h), (0, 0, 255), 2)  # Draw Red
            red_count += 1
            colors.append('red')
        elif np.any(mask_green[contour[0][0][1], contour[0][0][0]]):
            cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)  # Draw Green
            green_count += 1
            colors.append('green')
        elif np.any(mask_blue[contour[0][0][1], contour[0][0][0]]):
            cv2.rectangle(image, (x, y), (x + w, y + h), (255, 0, 0), 2)  # Draw Blue
            blue_count += 1
            colors.append('blue')

# Save the diagnostic image
cv2.imwrite("detected_cards_colored.png", image)

print("--- Image Processing Results ---")
print(f"Red items found:   {red_count}")
print(f"Green items found: {green_count}")
print(f"Blue items found:  {blue_count}")
print(f"Execution order:   {colors}\n")


# 6. Network Drone Controller Function
def move_drone(color_command):
    """
    Sends a color command to Unity and blocks execution until Unity 
    reports back that the drone has finished its sequence and returned to 'idle'.
    """
    host = 'localhost'
    port = 65431
    
    while True:  # Keep retrying until accepted
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((host, port))
                
                # Send command
                s.sendall(color_command.encode())
                print(f"[*] Sent '{color_command}' command to Unity. Awaiting drone execution...")
                
                # Listening loop waiting for Unity status updates
                while True:
                    data = s.recv(1024)
                    if not data:
                        print("[!] Connection closed unexpectedly by Unity.")
                        break
                        
                    response = data.decode().strip().lower()
                    
                    if 'idle' in response:
                        print(f"[+] Unity reported: Drone is IDLE. Task completed successfully.")
                        return  # Success, exit the retry loop
                    elif 'busy' in response:
                        print(f"[!] Unity reported: Drone is BUSY. Retrying in 1 second...")
                        time.sleep(1)
                        break  # Break inner loop to retry
                    else:
                        print(f"[-] Received unexpected response from Unity: {response}")
                        
        except ConnectionRefusedError:
            print("[!] Could not connect to Unity. Retrying in 1 second...")
            time.sleep(1)
        except Exception as e:
            print(f"[!] Network Error: {e}")
            return


# 7. Main Loop
if __name__ == "__main__":
    if not colors:
        print("No items detected to process.")
    else:
        print("Starting drone delivery routine...")
        for color in colors:
            move_drone(color)
            # The script naturally pauses on move_drone until Unity confirms it finished.
            # No hardcoded sleep required here anymore!
        print("All detected items processed.")
