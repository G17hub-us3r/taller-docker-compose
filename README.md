# Bitácora de Notas — Flask + PostgreSQL con Docker Compose

Proyecto ligero de dos servicios (`app` + `db`) conectados mediante una red privada (`alvaro_net`) y persistencia de base de datos con volumen nombrado (`alvaro_pgdata`), todo integrado en [compose.yaml](compose.yaml).

## Estructura

- `compose.yaml`: Define los servicios `db` (`postgres:16-alpine`) y `app` (`alvaro-notas-app:1.0.0`), la red `alvaro_net` y el volumen `alvaro_pgdata`.
- `Dockerfile`: Empaqueta la aplicación Flask con Gunicorn sobre `python:3.12-slim`.
- `app.py` y `templates/index.html`: Interfaz web CRUD y endpoint de salud `/health`.
- `.env.example`: Plantilla opcional de variables de entorno (si no existe `.env`, `compose.yaml` usa valores por defecto).

## Prueba local

```bash
docker compose up -d --build
```

Abrir en el navegador: `http://localhost:5089`  
Comprobar salud de conexión: `curl http://localhost:5089/health`

### Comprobar red, volumen y persistencia

```bash
# Ver contenedores, red y volumen
docker compose ps
docker network inspect alvaro_net
docker volume inspect alvaro_pgdata

# Probar persistencia (crear una nota en la web antes de bajar)
docker compose down
docker compose up -d
```

*(Nota: `docker compose down` elimina contenedores y red, pero mantiene intacto el volumen `alvaro_pgdata`.)*

## Despliegue en el servidor (`161.97.140.245`)

1. Subir el proyecto a GitHub (o transferirlo por `scp -P 1001 -r`).
2. Conectarse por SSH:
   ```bash
   ssh -p 1001 1729330785@161.97.140.245
   ```
3. Verificar que el puerto `5089` no esté ocupado en el host ni en contenedores detenidos:
   ```bash
   ss -tuln | grep 5089 || echo "Puerto 5089 libre"
   docker ps -a | grep 5089 || echo "Sin contenedores en 5089"
   ```
4. Clonar/entrar a la carpeta y levantar con Compose:
   ```bash
   git clone https://github.com/G17hub-us3r/taller-docker-compose.git
   cd taller-docker-compose
   docker compose up -d --build
   ```
5. Verificar en el navegador o terminal:
   ```bash
   curl http://161.97.140.245:5089/health
   docker compose ps
   ```
