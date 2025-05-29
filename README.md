````markdown
# Simulação de Urgências

Uma solução de simulação de atendimento de urgências médicas em múltiplas salas, com geração de clientes (pacientes) e lógica de desistência, filas de prioridade e monitorização via API REST.

## Pré-requisitos

- Python 3.12+
- (Opcional) Docker & Docker Compose (para deployment)
- (Opcional) Cloudflare Tunnel configurado

## Instalação

1. Clone este repositório e entre na pasta do projeto:
   ```bash
   git clone https://github.com/seu-usuario/simulacao-urgencias.git
   cd simulacao-urgencias
````

2. Crie e ative o ambiente virtual, depois instale as dependências:

   ```bash
   python -m venv .venv
   source .venv/bin/activate     # Linux/macOS
   .venv\Scripts\activate        # Windows
   pip install --no-cache-dir -r requirements.txt
   ```

## Como usar

### 1. Servidor de Urgências

Inicia o serviço TCP que aceita conexões de pacientes, criando `n_salas` e `n_medicos` threads:

```bash
python manage.py runurgencias \
  --host 127.0.0.1 \
  --port 9000 \
  --salas <n_salas> \
  --medicos <n_salas>
```

Para ver todas as opções:

```bash
python manage.py runurgencias --help
```

### 2. Servidor de Pacientes / Clientes

Dispara um “surto” de clientes para testar o servidor de urgências:

```bash
python manage.py runcliente \
  <verde|amarelo|vermelho> \
  --surto 10
```

Para ajuda:

```bash
python manage.py runcliente --help
```

### 3. Simulação Multi-Salas (Standalone)

Cria surtos e, se o servidor de urgências já estiver a correr, reutiliza-o; caso contrário, inicia um novo:

```bash
python simulate_multi_salas.py \
  --salas <n_salas> \
  --pacientes <n_pacientes> \
  --surto <tamanho_do_surto>
```

### 4. Deployment com Docker & Cloudflare

1. **Conectar o container ao network partilhada**
   Sempre que criar um novo tunnel Cloudflare, ligue o container ao network `shared`:

   ```bash
   sudo docker network connect shared <nome_do_container>
   ```

   Exemplo:

   ```bash
   sudo docker network connect shared friendly_engelbart
   ```

2. **Build e arranque**

   ```bash
   sudo docker compose up --build
   ```

---

## Observações

* Os ficheiros de log (`logs.json`, `med_status.json`) são recriados a cada arranque do servidor de urgências.
* A aplicação inclui uma API REST para monitorização e controlo remoto de simulações.
* Para testes rápidos de API, consulte também a rota `/api/docs/` (depois de criar as credenciais).
