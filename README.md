Ligar o ambiente virtual do django e intalar o requirements.txt

Correr o servidor de urgências:

     python manage.py runurgencias --host 127.0.0.1 --port 9000 --salas (n_salas) --medicos (n_salas) (--help)

Correr o servidor de pacientes/clientes:

     python manage.py runcliente (verde/vermelho/amarelo --surto 10) (--help)
     
Realizar testes de surtos (não é preciso de ter o servidor de urgências ligado):

     python simulate_multi_salas.py --salas (n_salas e n_medicos)  --pacientes (n_pacientes) --surto (n_surtos)

Caso se correr o servidor de urgências e não for encerrado e depois realizar o teste de simulação de surtos ele irá aproveitar o servidor que já se
encontra conectado.


Cointers do docker para dar run ao server (cloudflare):
sempre dar este comando quando o crias um novo tunnel para conectar ao docker-compose:

     sudo docker network connect shared nome_do_container (friendly_engelbart)
     
friendly_engelbart

Dar build ao projeto online:

    sudo docker compose up --build
