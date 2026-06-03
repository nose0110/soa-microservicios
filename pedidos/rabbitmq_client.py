import os
import json
import pika

#  URL desde variable de entorno (CloudAMQP o local)
RABBITMQ_URL = os.environ.get(
    "RABBITMQ_URL", 
    "amqp://guest:guest@localhost:5672/"
)

# Colas del sistema
QUEUES = {
    "pedidos": "pedidos.nuevos",
    "facturas": "facturas.pendientes",
    "notificaciones": "notificaciones.email"
}

def publicar_mensaje(queue_name: str, mensaje: dict):
    """Publicar mensaje en RabbitMQ de forma segura"""
    try:
        # Parsear URL (CloudAMQP usa amqps:// con SSL)
        params = pika.URLParameters(RABBITMQ_URL)
        connection = pika.BlockingConnection(params)
        channel = connection.channel()
        
        # Declarar cola (idempotente - no falla si ya existe)
        channel.queue_declare(queue=queue_name, durable=True)
        
        # Publicar mensaje
        channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=json.dumps(mensaje),
            properties=pika.BasicProperties(
                delivery_mode=2,  # Mensaje persistente
                content_type='application/json'
            )
        )
        
        connection.close()
        print(f"✅ Mensaje publicado en [{queue_name}]: {mensaje}")
        return True
        
    except Exception as e:
        print(f"❌ Error publicando en RabbitMQ: {e}")
        print(f"⚠️ El pedido ya está en BD, esto es solo para tareas secundarias")
        return False

def consumir_mensajes(queue_name: str, callback):
    """Consumir mensajes (para el worker que procesa facturas/notificaciones)"""
    try:
        params = pika.URLParameters(RABBITMQ_URL)
        connection = pika.BlockingConnection(params)
        channel = connection.channel()
        
        channel.queue_declare(queue=queue_name, durable=True)
        
        def on_message(ch, method, properties, body):
            mensaje = json.loads(body)
            print(f" Recibido en [{queue_name}]: {mensaje}")
            callback(mensaje)
            ch.basic_ack(delivery_tag=method.delivery_tag)
        
        channel.basic_consume(queue=queue_name, on_message_callback=on_message)
        print(f" Escuchando cola [{queue_name}]...")
        channel.start_consuming()
        
    except Exception as e:
        print(f" Error consumiendo: {e}")