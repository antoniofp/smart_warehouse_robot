import cv2
import socket
import os
import time
import torch
from ultralytics import YOLO

# =====================================================================
# 1. NETWORK CONFIGURATION (IP OF THE JETSON)
# =====================================================================
JETSON_IP = "100.106.92.18"  # Tailscale IP of your Jetson
UDP_PORT = 5005

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
JETSON_VIDEO_URL = f"http://{JETSON_IP}:8089/stream.mjpg"

# =====================================================================
# 2. MODEL CONFIGURATION (CUDA SUPPORT)
# =====================================================================
# --- OPCION 1: Buscar modelo en la carpeta 'models' (Descomentar para usar) ---
# ruta_actual = os.path.dirname(os.path.abspath(__file__))
# ruta_models = os.path.join(os.path.dirname(ruta_actual), 'models')
# model_file = 'best (1).pt'
# if not os.path.exists(os.path.join(ruta_models, model_file)):
#     model_file = 'best.pt'
# ruta_modelo = os.path.join(ruta_models, model_file)

# --- OPCION 2: Buscar modelo en la misma carpeta del script (Activa actualmente) ---
ruta_modelo = 'best.pt'

# Select GPU if CUDA is available, otherwise CPU
device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f"[INFO] Loading PyTorch model from: {ruta_modelo}")
print(f"[INFO] Running on device: {device}")

model = YOLO(ruta_modelo, task='detect')
UMBRAL_CERTEZA = 0.50  

# =====================================================================
# 3. PRINT CONTROL MEMORY (AVOIDS CONSOLE LOG SPAM)
# =====================================================================
clases_enviadas = {}      # Format: { "ClassName": frames_absent }
MAX_FRAMES_AUSENTE = 20   # Tolerance to camera flickering (~1 second)

# =====================================================================
# 4. CAPTURE VIDEO STREAM
# =====================================================================
print(f"[INFO] Connecting to ROS 2 video stream at: {JETSON_VIDEO_URL}")
cap = cv2.VideoCapture(JETSON_VIDEO_URL)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

print("\n----------------------------------------------------------------------")
print(" YOLOv8 Vision Node Active (Continuous Transmission)")
print("----------------------------------------------------------------------\n")

while True:
    if not cap.isOpened():
        print("[WARNING] Connection lost with Jetson. Retrying in 2 seconds...")
        time.sleep(2)
        cap = cv2.VideoCapture(JETSON_VIDEO_URL)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cv2.waitKey(1)
        continue

    ret, frame = cap.read()
    
    if not ret:
        print("[ERROR] Failed to read frame from stream. Reconnecting...")
        cap.release()
        cv2.waitKey(1)
        continue

    # Perform inference (imgsz=320 for performance)
    results = model.predict(frame, verbose=False, imgsz=320, device=device)
    
    clases_vistas_este_frame = set()

    for box in results[0].boxes:
        conf = float(box.conf)
        if conf >= UMBRAL_CERTEZA:
            cls_id = int(box.cls)
            label = model.names[cls_id]
            
            # Extract box geometry
            xywh = box.xywh[0]
            ancho_px = float(xywh[2])
            alto_px = float(xywh[3])
            # Define specific pixel thresholds per class
            thresholds = {
                "loading_zone": 70.0,
                "loading": 70.0,
                "pedestrian_zone": 80.0,
                "pedestrian": 80.0,
                "restricted_zone": 20.0,
                "restricted_area": 20.0,
                "restricted": 20.0,
                "stop_for_safety": 40.0,
                "stop": 40.0,
                "robot_only_zone": 50.0,
                "robot_only": 50.0,
                "agv": 50.0,
                "parking_zone": 80.0,
                "parking": 80.0
            }
            
            label_norm = label.strip().lower().replace(" ", "_").replace("-", "_")
            min_size = thresholds.get(label_norm, 35.0) # default to 35.0
            
            # Filter detections smaller than required pixels
            if ancho_px > min_size or alto_px > min_size:
                clases_vistas_este_frame.add(label)
                
                # Send UDP packet continuously
                mensaje = f"{label}:{conf:.2f}"
                sock.sendto(mensaje.encode(), (JETSON_IP, UDP_PORT))

                # Console log print control (only prints once per encounter)
                if label not in clases_enviadas:
                    print(f"[DETECTION: SENDING UDP] -> {mensaje} | Size: {ancho_px:.1f}x{alto_px:.1f} px")
                    clases_enviadas[label] = 0
                else:
                    clases_enviadas[label] = 0

    # Track absent classes to reset print control
    for clase in list(clases_enviadas.keys()):
        if clase not in clases_vistas_este_frame:
            clases_enviadas[clase] += 1
            if clases_enviadas[clase] > MAX_FRAMES_AUSENTE:
                print(f"[RESET] Sign '{clase}' is no longer visible.")
                del clases_enviadas[clase]

    # Show video stream on host laptop
    cv2.imshow('YOLOv8 - Offboard ROS2 Stream', results[0].plot())
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print("[INFO] Process finished successfully.")
