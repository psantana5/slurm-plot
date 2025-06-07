# SLURM Plot

Una herramienta de línea de comandos (CLI) para extraer, procesar y visualizar datos de trabajos SLURM.

## Características

- **Extracción de datos**: Conecta con SLURM usando `sacct` o archivos de log
- **Métricas completas**: CPU, memoria, GPU, tiempos de cola y ejecución
- **Agregación flexible**: Por hora, día o semana
- **Filtros avanzados**: Por fechas, cuenta, partición, estado y usuario
- **Visualizaciones**: Gráficos estáticos (PNG/SVG) e interactivos (HTML)
- **Configuración**: Archivo de configuración personalizable
- **Exportación**: Múltiples formatos de salida

## Instalación

### Desde PyPI (recomendado)

```bash
pip install slurm-plot
```

### Desde código fuente

```bash
git clone https://github.com/psantana5/slurm-plot.git
cd slurm-plot
pip install -e .
```

### Dependencias

- Python 3.10+
- pandas >= 2.0.0
- matplotlib >= 3.6.0
- click >= 8.1.0
- plotly >= 5.15.0 (opcional, para gráficos interactivos)

## Uso básico

### Comando simple

```bash
# Generar gráfico de métricas de CPU y memoria de la última semana
slurm-plot --metrics req_cpus alloc_cpus req_mem max_rss
```

### Ejemplos avanzados

```bash
# Análisis de una cuenta específica con gráfico interactivo
slurm-plot --account myproject --interactive --format html

# Análisis de trabajos fallidos en el último mes
slurm-plot --start 2024-01-01 --state FAILED --interval week

# Métricas de GPU por partición
slurm-plot --partition gpu_partition --metrics alloc_gpus used_gpus

# Análisis detallado con configuración personalizada
slurm-plot --config /path/to/config.ini --verbose --output detailed_analysis

# Usar archivo de log en lugar de sacct
slurm-plot --log-file /var/log/slurm/slurm.log --start 2024-01-01
```

## Opciones de línea de comandos

### Filtros de datos

- `--start, -s`: Fecha de inicio (YYYY-MM-DD)
- `--end, -e`: Fecha de fin (YYYY-MM-DD)
- `--account, -A`: Filtrar por cuenta SLURM
- `--partition, -p`: Filtrar por partición
- `--state`: Filtrar por estado del trabajo
- `--user, -u`: Filtrar por usuario

### Configuración de procesamiento

- `--interval, -i`: Intervalo de agregación (`hour`, `day`, `week`)
- `--metrics, -m`: Métricas a graficar (ver lista completa abajo)

### Opciones de salida

- `--output, -o`: Nombre del archivo de salida
- `--format, -f`: Formato de salida (`png`, `svg`, `html`)
- `--interactive`: Generar gráfico interactivo con Plotly

### Otras opciones

- `--config, -c`: Archivo de configuración personalizado
- `--log-file`: Usar archivo de log en lugar de sacct
- `--verbose, -v`: Salida detallada
- `--dry-run`: Mostrar qué se haría sin ejecutar

## Métricas disponibles

### CPU
- `req_cpus`: CPUs solicitadas
- `alloc_cpus`: CPUs asignadas
- `used_cpus`: Horas de CPU utilizadas

### Memoria
- `req_mem`: Memoria solicitada (GB)
- `max_rss`: Memoria máxima utilizada (GB)
- `used_mem`: Memoria utilizada (alias de max_rss)

### GPU
- `alloc_gpus`: GPUs asignadas
- `used_gpus`: Horas de GPU utilizadas

### Tiempos
- `queue_time`: Tiempo medio en cola (horas)
- `run_time`: Tiempo medio de ejecución (horas)

### Otros
- `job_count`: Número de trabajos

## Configuración

### Archivo de configuración

Crea un archivo de configuración personalizado:

```bash
# Generar archivo de configuración por defecto
cp config.ini ~/.config/slurm-plot/config.ini
```

Ubicaciones de configuración (en orden de prioridad):
1. `./slurm-plot.ini` (directorio actual)
2. `~/.config/slurm-plot/config.ini` (usuario)
3. `/etc/slurm-plot/config.ini` (sistema)

### Ejemplo de configuración

```ini
[slurm]
sacct_command = sacct
timeout = 30

[processing]
memory_unit = GB
time_unit = hours

[plotting]
figure_width = 12
figure_height = 8
dpi = 300
style = seaborn-v0_8

[output]
default_format = png
quality = 95
```

## Ejemplos de uso

### 1. Análisis básico de recursos

```bash
# Métricas de CPU y memoria de la última semana
slurm-plot --metrics req_cpus alloc_cpus used_cpus req_mem max_rss
```

### 2. Análisis de eficiencia por proyecto

```bash
# Comparar eficiencia entre diferentes cuentas
for account in project1 project2 project3; do
    slurm-plot --account $account --output efficiency_$account --verbose
done
```

### 3. Monitoreo de colas

```bash
# Análisis de tiempos de cola por partición
slurm-plot --partition gpu --metrics queue_time run_time job_count --interval hour
```

### 4. Análisis de fallos

```bash
# Trabajos fallidos en el último mes
slurm-plot --start 2024-01-01 --state FAILED --metrics job_count queue_time run_time
```

### 5. Dashboard interactivo

```bash
# Crear dashboard HTML interactivo
slurm-plot --interactive --metrics req_cpus alloc_cpus used_cpus req_mem max_rss alloc_gpus used_gpus queue_time run_time job_count
```

### 6. Análisis histórico

```bash
# Tendencias mensuales del último año
slurm-plot --start 2023-01-01 --end 2023-12-31 --interval week --output yearly_trends
```

## Desarrollo

### Estructura del proyecto

```
slurm-plot/
├── slurm_plot/
│   ├── __init__.py
│   ├── __main__.py      # Punto de entrada
│   ├── cli.py           # Interfaz de línea de comandos
│   ├── config.py        # Gestión de configuración
│   ├── fetcher.py       # Extracción de datos SLURM
│   ├── processor.py     # Procesamiento y agregación
│   └── plotter.py       # Generación de gráficos
├── tests/
│   ├── test_config.py
│   ├── test_fetcher.py
│   └── test_processor.py
├── config.ini           # Configuración de ejemplo
├── requirements.txt
├── setup.py
└── README.md
```

### Instalación para desarrollo

```bash
git clone https://github.com/slurmplot/slurm-plot.git
cd slurm-plot
pip install -e ".[dev]"
```

### Ejecutar tests

```bash
# Todos los tests
pytest

# Tests con cobertura
pytest --cov=slurm_plot

# Tests específicos
pytest tests/test_fetcher.py
```

### Formateo de código

```bash
# Formatear código
black slurm_plot/ tests/

# Verificar estilo
flake8 slurm_plot/ tests/

# Verificar tipos
mypy slurm_plot/
```

## Solución de problemas

### Error: "sacct command not found"

```bash
# Verificar que SLURM esté instalado
which sacct

# Usar archivo de log alternativo
slurm-plot --log-file /var/log/slurm/slurm.log
```

### Error: "No data found"

```bash
# Verificar rango de fechas
slurm-plot --start 2024-01-01 --end 2024-01-31 --verbose

# Verificar filtros
slurm-plot --account myaccount --verbose
```

### Error: "Permission denied"

```bash
# Verificar permisos de sacct
sacct --help

# Usar configuración alternativa
slurm-plot --config /path/to/config.ini
```

### Gráficos interactivos no funcionan

```bash
# Instalar Plotly
pip install plotly

# Verificar instalación
python -c "import plotly; print(plotly.__version__)"
```

## Contribuir

1. Fork el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -am 'Añadir nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crea un Pull Request

### Guías de contribución

- Seguir PEP 8 para el estilo de código
- Añadir tests para nuevas funcionalidades
- Actualizar documentación cuando sea necesario
- Usar mensajes de commit descriptivos

## Licencia

MIT License - ver archivo [LICENSE](LICENSE) para detalles.

## Soporte

- **Issues**: [GitHub Issues](https://github.com/slurmplot/slurm-plot/issues)
- **Documentación**: [Wiki](https://github.com/slurmplot/slurm-plot/wiki)
- **Email**: contact@slurmplot.com

## Changelog

### v1.0.0
- Lanzamiento inicial
- Soporte para extracción de datos con sacct
- Agregación por hora/día/semana
- Gráficos estáticos e interactivos
- Sistema de configuración
- Tests unitarios completos

## Agradecimientos

- Comunidad SLURM por la documentación
- Contribuidores del proyecto
- Usuarios que reportan bugs y sugieren mejoras
