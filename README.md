Correr o servidor de urgencias:
python manage.py runurgencias --host 127.0.0.1 --port 9000 (--help)
Correr o servidor de pacientes/clientes:
python manage.py runcliente (verde/vermelho/amarelo --surto 10) (--help)
Realizar testes com multi quartos:
python simulate_multi_salas.py --salas (n_salas e n_medicos)  --pacientes (n_pacientes) --surto (n_surtos)

