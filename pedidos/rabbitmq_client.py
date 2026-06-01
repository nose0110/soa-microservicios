import pika
import json
import time
from typing import Callable, Optional

RABBITMQ_HOST = "localhost"
RABBITMQ_PORT = 5672
RABBITMQ_USER = "guest"
RABBITMQ_PASS = "guest"

# Colas para cada servicio externo
QUEUES = {
    "clientes": "pedidos.validar_cliente",
    "productos": "pedidos.validar_producto", 
    "inventario": "pedidos.validar_stock"
}

def get_connection():
    """Establece conexión con RabbitMQ con reintentos."""
    max_retries = 5
    for attempt in range(max_retries):
        try:
            credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
            parameters = pika.ConnectionParameters(
                host=RABBITMQ_HOST,
                port=RABBITMQ_PORT,
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300
            )
            connection = pika.BlockingConnection(parameters)
            print(f"✅ Conectado a RabbitMQ (intento {attempt + 1})")
            return connection
        except Exception as e:
            print(f"⚠️ Intento {attempt + 1} fallido: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                raise

def publicar_mensaje(queue_name: str, mensaje: dict, durable: bool = True):
    """Publica un mensaje en la cola especificada."""
    try:
        connection = get_connection()
        channel = connection.channel()
        
        # Declarar cola durable (sobrevive reinicios de RabbitMQ)
        channel.queue_declare(queue=queue_name, durable=durable)
        
        # Publicar mensaje persistente
        channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=json.dumps(mensaje),
            properties=pika.BasicProperties(
                delivery_mode=2,  # Mensaje persistente
                content_type='application/json'
            )
        )
        print(f"📤 Mensaje publicado en {queue_name}: {mensaje}")
        return True
        
    except Exception as e:
        print(f"❌ Error publicando en {queue_name}: {e}")
        return False
    finally:
        if 'connection' in locals() and connection.is_open:
            connection.close()

def consumir_mensajes(queue_name: str, callback: Callable, auto_ack: bool = False):
    """Consume mensajes de una cola y ejecuta el callback."""
    try:
        connection = get_connection()
        channel = connection.channel()
        
        channel.queue_declare(queue=queue_name, durable=True)
        channel.basic_qos(prefetch_count=1)  # Procesar 1 mensaje a la vez
        
        def on_message(ch, method, properties, body):
            try:
                mensaje = json.loads(body)
                print(f"📥 Procesando de {queue_name}: {mensaje}")
                
                # Ejecutar callback (lógica de validación)
                resultado = callback(mensaje)
                
                if not auto_ack:
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    print(f"✅ Mensaje procesado: {queue_name}")
                    
            except Exception as e:
                print(f"❌ Error procesando mensaje: {e}")
                if not auto_ack:
                    # Re-encolar para reintentar después
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        
        channel.basic_consume(queue=queue_name, on_message_callback=on_message)
        print(f"🔄 Esperando mensajes en {queue_name}... (Ctrl+C para salir)")
        channel.start_consuming()
        
    except KeyboardInterrupt:
        print("⏹️ Deteniendo consumidor...")
    except Exception as e:
        print(f"❌ Error en consumidor {queue_name}: {e}")
    finally:
        if 'connection' in locals() and connection.is_open:
            connection.close()