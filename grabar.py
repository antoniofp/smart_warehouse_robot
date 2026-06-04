#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import os
import sys

class GrabadorVideoROS(Node):
    def __init__(self):
        super().__init__('grabador_dataset_node')
        
        # 1. CONFIGURACIÓN DEL ARCHIVO
        # Cambia este nombre para cada póster
        self.nombre_archivo = "stop_sign.avi"
        self.carpeta_salida = "temp_host-docker_files"
        self.ruta_final = os.path.join(self.carpeta_salida, self.nombre_archivo)
        
        if not os.path.exists(self.carpeta_salida):
            os.makedirs(self.carpeta_salida)

        # 2. CONFIGURACIÓN DE ROS 2
        # ⚠️ REVISA TU TÓPICO: Cambia '/camera/image_raw' por el tópico real de tu carro 
        # (puedes verificarlo corriendo 'ros2 topic list' en otra terminal)
        self.topico_camara = '/camera/image_raw' 
        
        self.bridge = CvBridge()
        self.out = None
        self.contador_frames = 0
        self.fps = 20.0 # Velocidad a la que configuraremos el contenedor del archivo .avi

        # Suscripción al tópico de la imagen de ROS
        self.subscription = self.create_subscription(
            Image,
            self.topico_camara,
            self.listener_callback,
            10)
        
        print("-" * 60)
        print("🤖 YAHBOOM R2 - GRABADOR DE DATASET VIA ROS 2 🤖")
        print(f"📡 Escuchando el tópico: '{self.topico_camara}'")
        print(f"📁 Guardando video en: '{self.ruta_final}'")
        print("Maneja el carrito hacia el póster...")
        print("🔥 ¡PRESIONA CTRL + C EN LA TERMINAL PARA DETENER Y GUARDAR!")
        print("-" * 60)

    def listener_callback(self, msg):
        try:
            # Convertir el mensaje de imagen de ROS a una matriz de OpenCV (BGR)
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as e:
            self.get_logger().error(f'No se pudo convertir la imagen: {e}')
            return

        # Inicializar el VideoWriter dinámicamente con la resolución real que envíe ROS
        if self.out == None:
            alto, ancho, _ = frame.shape
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            self.out = cv2.VideoWriter(self.ruta_final, fourcc, self.fps, (ancho, alto))
            print(f"📐 Resolución detectada desde ROS: {ancho}x{alto} a {self.fps} FPS")

        # Escribir el frame en el archivo .avi
        self.out.write(frame)
        self.contador_frames += 1

        # Feedback visual en la terminal cada segundo
        if self.contador_frames % int(self.fps) == 0:
            segundos = int(self.contador_frames / self.fps)
            print(f"-> Grabando desde ROS... {segundos} seg | {self.contador_frames} cuadros", end="\r")

    def destruir_grabador(self):
        # Asegurar el cierre correcto del archivo de video al salir
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
