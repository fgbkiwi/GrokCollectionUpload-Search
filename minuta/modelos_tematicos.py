"""
Biblioteca de Modelos Temáticos.

Gerencia templates de texto com variáveis para temas recorrentes
(juros, FGTS, honorários, etc.).
"""

import json
from pathlib import Path
from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from datetime import datetime


class ModeloTematico(BaseModel):
    """Modelo temático com variáveis."""
    id: str = Field(..., description="ID único do modelo")
    nome: str = Field(..., description="Nome do modelo")
    tema: str = Field(..., description="Tema/categoria (ex: juros, FGTS, honorários)")
    texto: str = Field(..., description="Texto com variáveis (ex: {{valor}}, {{periodo}})")
    variaveis: List[str] = Field(default_factory=list, description="Lista de variáveis disponíveis")
    data_criacao: datetime = Field(default_factory=datetime.now, description="Data de criação")
    data_modificacao: datetime = Field(default_factory=datetime.now, description="Data de modificação")


class BibliotecaModelos:
    """Gerencia biblioteca de modelos temáticos."""
    
    def __init__(self, diretorio_base: Optional[Path] = None):
        if diretorio_base is None:
            diretorio_base = Path.home() / ".indexador_sentencas" / "modelos"
        
        self.diretorio_base = Path(diretorio_base)
        self.diretorio_base.mkdir(parents=True, exist_ok=True)
        self.arquivo_modelos = self.diretorio_base / "modelos_tematicos.json"
        
        if not self.arquivo_modelos.exists():
            self._criar_modelos_iniciais()
    
    def _criar_modelos_iniciais(self):
        """Cria conjunto inicial de modelos (opcional, editável pelo juiz)."""
        modelos_iniciais = [
            ModeloTematico(
                id="juros_1",
                nome="Juros e Correção Monetária - Lei 14.905/2024",
                tema="juros",
                texto="""## Juros e Correção Monetária

Sobre os valores deferidos, incidem juros de mora e correção monetária conforme Lei 14.905/2024.

A correção monetária observará o IPCA-E acumulado mensalmente, conforme determina o art. 879, §7º, da CLT, com a redação dada pela Lei 14.905/2024.

Os juros de mora, à razão de 1% ao mês, incidirão a partir do ajuizamento da ação, nos termos do art. 883 da CLT.""",
                variaveis=[]
            ),
            ModeloTematico(
                id="fgts_1",
                nome="FGTS com Multa de 40%",
                tema="fgts",
                texto="""## FGTS e Multa de 40%

Defiro o depósito do FGTS sobre as parcelas deferidas, com incidência da multa de 40% prevista no art. 18, §1º, da Lei 8.036/90.

O recolhimento deverá observar a remuneração variável e as parcelas de natureza salarial reconhecidas nesta sentença, nos períodos {{periodo}}.""",
                variaveis=["periodo"]
            ),
            ModeloTematico(
                id="honorarios_1",
                nome="Honorários Advocatícios Sucumbenciais",
                tema="honorarios",
                texto="""## Honorários Advocatícios

Condeno a parte reclamada ao pagamento de honorários advocatícios sucumbenciais, arbitrados em {{percentual}}% sobre o valor da condenação, nos termos do art. 791-A da CLT.

A fixação observa o grau de zelo profissional, o trabalho realizado e o tempo exigido para a prestação do serviço.""",
                variaveis=["percentual"]
            ),
            ModeloTematico(
                id="recolhimentos_1",
                nome="Recolhimentos Fiscais e Previdenciários",
                tema="recolhimentos",
                texto="""## Recolhimentos Fiscais e Previdenciários

A reclamada é responsável pelo recolhimento das contribuições fiscais e previdenciárias incidentes sobre os valores deferidos nesta sentença.

A contribuição previdenciária observará a alíquota devida, limitada ao teto do salário de contribuição, conforme legislação de regência.

O imposto de renda seguirá a tabela progressiva vigente à época do pagamento.""",
                variaveis=[]
            ),
        ]
        
        self.salvar_todos(modelos_iniciais)
    
    def criar(self, modelo: ModeloTematico) -> bool:
        """Cria um novo modelo."""
        modelos = self.listar()
        
        if any(m.id == modelo.id for m in modelos):
            return False
        
        modelos.append(modelo)
        self.salvar_todos(modelos)
        return True
    
    def obter(self, id_modelo: str) -> Optional[ModeloTematico]:
        """Obtém um modelo por ID."""
        modelos = self.listar()
        
        for modelo in modelos:
            if modelo.id == id_modelo:
                return modelo
        
        return None
    
    def atualizar(self, modelo: ModeloTematico) -> bool:
        """Atualiza um modelo existente."""
        modelos = self.listar()
        
        for i, m in enumerate(modelos):
            if m.id == modelo.id:
                modelo.data_modificacao = datetime.now()
                modelos[i] = modelo
                self.salvar_todos(modelos)
                return True
        
        return False
    
    def excluir(self, id_modelo: str) -> bool:
        """Exclui um modelo."""
        modelos = self.listar()
        modelos_filtrados = [m for m in modelos if m.id != id_modelo]
        
        if len(modelos_filtrados) < len(modelos):
            self.salvar_todos(modelos_filtrados)
            return True
        
        return False
    
    def listar(self) -> List[ModeloTematico]:
        """Lista todos os modelos."""
        if not self.arquivo_modelos.exists():
            return []
        
        with open(self.arquivo_modelos, "r", encoding="utf-8") as f:
            dados = json.load(f)
        
        return [ModeloTematico(**m) for m in dados]
    
    def buscar_por_tema(self, tema: str) -> List[ModeloTematico]:
        """Busca modelos por tema."""
        modelos = self.listar()
        return [m for m in modelos if m.tema.lower() == tema.lower()]
    
    def salvar_todos(self, modelos: List[ModeloTematico]):
        """Salva todos os modelos."""
        dados = [m.model_dump(mode="json") for m in modelos]
        
        with open(self.arquivo_modelos, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2, default=str)
    
    def aplicar_variaveis(
        self,
        id_modelo: str,
        variaveis: Dict[str, str]
    ) -> Optional[str]:
        """
        Aplica valores às variáveis de um modelo.
        
        Args:
            id_modelo: ID do modelo
            variaveis: Dicionário de variáveis e valores
            
        Returns:
            Texto com variáveis substituídas ou None se modelo não encontrado
        """
        modelo = self.obter(id_modelo)
        
        if modelo is None:
            return None
        
        texto = modelo.texto
        
        for var, valor in variaveis.items():
            placeholder = f"{{{{{var}}}}}"
            texto = texto.replace(placeholder, valor)
        
        return texto
