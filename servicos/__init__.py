from .clientes_service import ClientesService
from .gerador_clientes import gerar_clientes
from .integracao import consulta_integrada
from .paises_service import ESTADOS, TECNOLOGIAS, PaisesService

__all__ = ["ClientesService", "PaisesService", "TECNOLOGIAS", "ESTADOS",
           "consulta_integrada", "gerar_clientes"]
