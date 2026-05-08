# PL (Processamento de Linguagens) (Português)
Projeto de grupo desenvolvido no âmbito da UC de Processamento de Linguagens. O projeto consiste no desenvolvimento de um compilador para a linguagem `Fortran 77` (standard ANSI X3.9-1978) para [EWVM](https://ewvm.epl.di.uminho.pt/).

## Membros do grupo:

* [darteescar](https://github.com/darteescar)
* [luis7788](https://github.com/luis7788)
* [tiagofigueiredo7](https://github.com/tiagofigueiredo7)

---

### Ficheiros relevantes

- [Enunciado](enunciado.pdf)
- [Relatório](relatorio.pdf)

> [!WARNING]
> **Dependências:** Para correr o projeto é necessário ter instaladas as bibliotecas `ply` e `pytest`. Para isso, basta correr o seguinte comando:
 
```bash
pip install ply pytest
```

## Setup
Depois de fazer clone do repositório, é necessário criar um ambiente virtual de Python e instalar as dependências.

```bash
cd fortran77-compiler/
python -m venv .venv
source .venv/bin/activate
pip install ply pytest
```

## Run
Para correr o projeto basta correr os comandos conforme são apresentados abaixo:

```bash
cd fortran77-compiler/src/

usage: python __main__.py [-h] [-pp | -l | -p | -s | -t] file

Compilador de Fortran 77

positional arguments:
  file             Path para o ficheiro Fortran 77

options:
  -h, --help       show this help message and exit
  -pp, --preprocess  Executa apenas o pré-processamento
  -l, --lexer      Executa o lexer
  -p, --parser     Executa o lexer e o parser
  -s, --semantic   Executa o lexer, parser e a análise semântica
  -t, --translate  Executa a tradução completa
```

## Testes
Para correr os tests basta fazer:

```bash
cd fortran77-compiler/test/
pytest <test_file>.py
```

# PL (Language Processing) (English)
Group project developed for the Language Processing course. The project consists of developing a compiler for the `Fortran 77` language (ANSI X3.9-1978 standard) for [EWVM](https://ewvm.epl.di.uminho.pt/).

## Group members:

* [darteescar](https://github.com/darteescar)
* [luis7788](https://github.com/luis7788)
* [tiagofigueiredo7](https://github.com/tiagofigueiredo7)

---

### Relevant files

- [Assignment](enunciado.pdf)
- [Report](relatorio.pdf)

> [!WARNING]
> **Dependencies:** To run the project it is necessary to have the `ply` and `pytest` libraries installed. To do this, simply run the following command:
 
```bash
pip install ply pytest
```

## Setup
After cloning the repository, you need to create a Python virtual environment and install the dependencies.

```bash
cd fortran77-compiler/
python -m venv .venv
source .venv/bin/activate
pip install ply pytest
```

## Run
To run the project just run the commands as shown below:

```bash
cd fortran77-compiler/src/

usage: python __main__.py [-h] [-pp | -l | -p | -s | -t] file

Fortran 77 Compiler

positional arguments:
  file             Path to the Fortran 77 file

options:
  -h, --help       show this help message and exit
  -pp, --preprocess  Executes only the preprocessing
  -l, --lexer      Executes the lexer
  -p, --parser     Executes the lexer and the parser
  -s, --semantic   Executes the lexer, parser and semantic analysis
  -t, --translate  Executes the full translation
```

## Tests
To run the tests simply do:

```bash
cd fortran77-compiler/test/
pytest <test_file>.py
```
