import requests
import time
from rabbitmq_client import consumir_mensajes, QUEUES

# URLs de servicios externos
SERVICIOS = {
    "clientes": "http://localhost:8000/v2/clientes",
    "productos": "http://localhost:8001/v2/productos",  # O 8011/v3 si usas Node.js
    "inventario": "http://localhost:8003/v2/inventario"
}

def validar_cliente_async(mensaje: dict) -> bool:
    """Valida cliente consultando el servicio (con reintentos)."""
    id_cliente = mensaje.get("id_cliente")
    pedido_id = mensaje.get("pedido_id")
    
    max_retries = 3
    for intento in range(max_retries):
        try:
            response = requests.get(f"{SERVICIOS['clientes']}/{id_cliente}", timeout=10)
            if response.status_code == 200:
                print(f"✅ Cliente {id_cliente} validado para pedido {pedido_id}")
                return True
            elif response.status_code == 404:
                print(f"❌ Cliente {id_cliente} NO existe")
                return False
        except requests.exceptions.ConnectionError:
            print(f"⚠️ Servicio Clientes caído (intento {intento + 1}/{max_retries})")
            if intento < max_retries - 1:
                time.sleep(2 ** intento)
            else:
                print(f"❌ Cliente {id_cliente} no validado: servicio indisponible")
                return False
    return False

def validar_producto_async(mensaje: dict) -> dict:
    """Valida producto y retorna sus datos."""
    id_producto = mensaje.get("id_producto")
    pedido_id = mensaje.get("pedido_id")
    
    max_retries = 3
    for intento in range(max_retries):
        try:
            response = requests.get(f"{SERVICIOS['productos']}/{id_producto}", timeout=10)
            if response.status_code == 200:
                producto = response.json()
                print(f"✅ Producto {id_producto} validado para pedido {pedido_id}")
                return producto
            elif response.status_code == 404:
                print(f"❌ Producto {id_producto} NO existe")
                return None
        except requests.exceptions.ConnectionError:
            print(f"⚠️ Servicio Productos caído (intento {intento + 1}/{max_retries})")
            if intento < max_retries - 1:
                time.sleep(2 ** intento)
            else:
                print(f"❌ Producto {id_producto} no validado: servicio indisponible")
                return None
    return None

def validar_stock_async(mensaje: dict) -> bool:
    """Valida stock disponible."""
    id_producto = mensaje.get("id_producto")
    cantidad = mensaje.get("cantidad")
    pedido_id = mensaje.get("pedido_id")
    
    max_retries = 3
    for intento in range(max_retries):
        try:
            response = requests.get(f"{SERVICIOS['inventario']}/{id_producto}", timeout=10)
            if response.status_code == 200:
                inventario = response.json()
                stock_disponible = int(inventario.get("cantidad", 0))
                if stock_disponible >= cantidad:
                    print(f"✅ Stock suficiente: {stock_disponible} >= {cantidad}")
                    return True
                else:
                    print(f"❌ Stock insuficiente: {stock_disponible} < {cantidad}")
                    return False
            elif response.status_code == 404:
                print(f"❌ Producto {id_producto} no está en inventario")
                return False
        except requests.exceptions.ConnectionError:
            print(f"⚠️ Servicio Inventario caído (intento {intento + 1}/{max_retries})")
            if intento < max_retries - 1:
                time.sleep(2 ** intento)
            else:
                print(f"❌ Stock no validado: servicio indisponible")
                return False
    return False

def actualizar_stock_async(mensaje: dict) -> bool:
    """Actualiza el stock después de un pedido exitoso."""
    id_producto = mensaje.get("id_producto")
    cantidad = mensaje.get("cantidad")
    
    try:
        # Obtener stock actual
        response = requests.get(f"{SERVICIOS['inventario']}/{id_producto}", timeout=10)
        if response.status_code == 200:
            stock_actual = int(response.json().get("cantidad", 0))
            nuevo_stock = stock_actual - cantidad
            
            # Actualizar
            update_resp = requests.patch(
                f"{SERVICIOS['inventario']}/{id_producto}",
                json={"cantidad": nuevo_stock},
                timeout=10
            )
            if update_resp.status_code == 200:
                print(f"✅ Stock actualizado: {id_producto} = {nuevo_stock}")
                return True
    except Exception as e:
        print(f"❌ Error actualizando stock: {e}")
    return False

if __name__ == "__main__":
    print("🚀 Iniciando Worker de Pedidos - RabbitMQ Consumer")
    
    # Consumir de cada cola con su callback correspondiente
    import threading
    
    threads = []
    
    # Thread para validar clientes
    t1 = threading.Thread(
        target=consumir_mensajes,
        args=(QUEUES["clientes"], validar_cliente_async),
        daemon=True
    )
    threads.append(t1)
    
    # Thread para validar productos
    t2 = threading.Thread(
        target=consumir_mensajes,
        args=(QUEUES["productos"], validar_producto_async),
        daemon=True
    )
    threads.append(t2)
    
    # Thread para validar stock
    t3 = threading.Thread(
        target=consumir_mensajes,
        args=(QUEUES["inventario"], validar_stock_async),
        daemon=True
    )
    threads.append(t3)
    
    # Iniciar todos los consumidores
    for t in threads:
        t.start()
    
    # Mantener el proceso vivo
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n⏹️ Deteniendo worker...")