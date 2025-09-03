.PHONY: create-env activate install test coverage report report-html


# Crear entorno virtual
create-venv:
	python -m venv venv
	@echo "No olvides activar el entorno virtual ejecutando 'source venv/bin/activate'"

# Instalar dependencias
install:
	pip install -r requirements.txt

# AWS codeartifact
codeartifact:
	aws codeartifact login --tool pip --repository copan-repository --domain copanit --domain-owner 169123383732 --region us-east-1



# Ejecutar tests
test:
	export PYTHONPATH=./src:$$PYTHONPATH; pytest tests/

# Ejecutar tests con cobertura de código
coverage:
	export PYTHONPATH=./src:$$PYTHONPATH; coverage run -m pytest

# Reporte de cobertura de código
report:
	coverage report -m

# Reporte de cobertura de código en html
report-html:
	coverage html