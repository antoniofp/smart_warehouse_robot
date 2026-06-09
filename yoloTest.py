from ultralytics import YOLO

# Cargas tu modelo entrenado con tus señales personalizadas
model = YOLO('/home/mojarras/smart_warehouse_robot/best.pt')

# Ejecutar la predicción directo sobre el flujo de la cámara
results = model.predict(source=0, conf=0.6, show=True)