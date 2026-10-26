"""FW01: pronta para integracao; nenhuma corrida e iniciada automaticamente."""

from robo.inicializacao import iniciar

app = iniciar()
app.motores.stop()
print('Firmware inicializado; motores desabilitados.')
