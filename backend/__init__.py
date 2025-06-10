# Este archivo hace que el directorio backend sea un paquete Python
import os
import sys

# Asegurar que el directorio actual esté en el path de Python
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Importar db para que esté disponible al importar el paquete
from db import get_db_config, get_bucket_name, test_connection