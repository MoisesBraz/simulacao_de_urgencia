Ligar o ambiente virtual do django e intalar o requirements.txt

Correr o servidor de urgencias:
python manage.py runurgencias --host 127.0.0.1 --port 9000 --salas (n_salas) --medicos (n_salas) (--help)
Correr o servidor de pacientes/clientes:
python manage.py runcliente (verde/vermelho/amarelo --surto 10) (--help)
Realizar testes com multi quartos:
python simulate_multi_salas.py --salas (n_salas e n_medicos)  --pacientes (n_pacientes) --surto (n_surtos)


**O número de salas deve ser igual no simulate_multi_salas e runurgenciars**, existe um erro lógico de implementação que 
deve ser resolvido no futuro


Cointers do docker para dar run ao server (cloudflare):
sempre dar este comando quando o crias um novo tunnel para conectar ao docker-compose:
     sudo docker network connect shared nome_do_container (friendly_engelbart)
friendly_engelbart

Dar build ao projeto online:
    sudo docker compose up --build