#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage  # <--- Cambiado a CompressedImage
from cv_bridge import CvBridge
import cv2
import os
import time

class GrabadorVideoROS(Node):
    def __init__(self):
        super().__init__('grabador_dataset_node')
        
        # 1. CONFIGURACIÓN DEL ARCHIVO CON TIEMPO AUTOMÁTICO
        self.clase_poster = "stop_sign"  # Cambia esto para cada póster
        timestamp = time.strftime("%H%M%S")
        self.nombre_archivo = f"{self.clase_poster}_{timestamp}.avi"
        
        self.carpeta_salida = "temp_host-docker_files"
        self.ruta_final = os.path.join(self.carpeta_salida, self.nombre_archivo)
        
        if not os.path.exists(self.carpeta_salida):
            os.makedirs(self.carpeta_salida)

        # 2. CONFIGURACIÓN DE ROS 2 (TÓPICO COMPRIMIDO)
        self.topico_camara = '/image_raw/compressed'  # <--- Cambiado al bueno
        
        self.bridge = CvBridge()
        self.out = None
        self.contador_frames = 0
        self.fps = 5.0

        # Suscripción usando CompressedImage
        self.subscription = self.create_subscription(
            CompressedImage,
            self.topico_camara,
            self.listener_callback,
            10)
        
        print("-" * 60)
        print("🤖 YAHBOOM R2 - GRABADOR COMPRIMIDO (MÁXIMO RENDIMIENTO) 🤖")
        print(f"📡 Escuchando el tópico: '{self.topico_camara}'")
        print(f"📁 Creando archivo: '{self.ruta_final}'")
        print("Maneja el carrito hacia el póster...")
        print("🔥 ¡PRESIONA CTRL + C EN LA TERMINAL PARA DETENER Y GUARDAR!")
        print("-" * 60)

    def listener_callback(self, msg):
        try:
            # Truco: Usamos 'compressed_imgmsg_to_cv2' para desempaquetar el JPEG
            frame = self.bridge.compressed_imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as e:
            self.get_logger().error(f'No se pudo descomprimir la imagen: {e}')
            return

        # Inicializar el VideoWriter con la resolución real de la imagen descomprimida
        if self.out == None:
            alto, ancho, _ = frame.shape
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            self.out = cv2.VideoWriter(self.ruta_final, fourcc, self.fps, (ancho, alto))
            print(f"📐 Resolución detectada (Descomprimida): {ancho}x{alto} a {self.fps} FPS")

        # Escribir frame en el video
        self.out.write(frame)
        self.contador_frames += 1

        # Feedback en la terminal cada segundo
        if self.contador_frames % int(self.fps) == 0:
            segundos = int(self.contador_frames / self.fps)
            print(f"-> Grabando comprimido... {segundos} seg | {self.contador_frames} cuadros", end="\r")

    def destruir_grabador(self):
        if self.out is not None:
            self.out.release()
            print("\n" + "-" * 60)
            print(f"¡Éxito! Archivo '{self.nombre_archivo}' guardado correctamente.")
            print(f"Total de cuadros capturados: {self.contador_frames}")
            print("-" * 60)

def main(args=None):
    rclpy.init(args=args)
    grabador = GrabadorVideoROS()
    try:
        rclpy.spin(grabador)
    except KeyboardInterrupt:
        print("\n[INFO] Deteniendo nodo por teclado...")
    finally:
        grabador.destruir_grabador()
        grabador.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
