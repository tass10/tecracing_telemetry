# TR08 Telemetry System
Telemetry and DAQ System for FSAE BR Team TEC Racing

# Resultados da Pesquisa:

## Materiais de Apoio:

### Esquemas Elétricos
- [Sistema Receptor](Schematics/20260430_Telemetry_Schematic_Receiver_Tassio.PDF)
- [Sistema Transmissor](Schematics/20260430_Telemetry_Schematic_Transmitter_Tassio.PDF)
- [Sistema Transmissor Simplificado](Schematics/20260429_Telemetry_Simplified_Schematic_Transmitter_Leonardo.pdf)

### Arquivos Gerber:
- [Gerbers.zip](Gerbers/Gerbers.zip)

### Modelos 3D:
- [PCB.step](CAD/telemetry_board_3dmodel.step)
- [PCB.stl](CAD/telemetry_board_3dmodel.stl)

## Desempenho da Comunicação a Distância:
<p align="justify"> Para avaliar a performance do sistema, foi construído um protótipo com os componentes principais e foi realizado um teste de comunicação, consistindo no envio de 1.000 mensagens para o Sistema Receptor em distâncias predefinidas, variando de 50 m a 250 m, com incrementos regulares de 50 metros. O Sistema Receptor identifica quantas mensagens foram recebidas e informa a potência do sinal recebido para cada mensagem e porcentagem de erro total.</p>

![Desempenho da Comunicação a Distância.](Imagens/grafico_telemetria_tcc.png)

<p align="justify"> A análise da métrica do Indicador de Potência do Sinal Recebido, RSSI, demonstra que o sinal médio atenuou de -46,4 dBm, a 50 metros, para -56,7 dBm, a 250 metros. Esses valores encontram-se em uma zona extremamente segura de recepção. De acordo com a literatura técnica e as especificações da fabricante do transceiver, a modulação LoRa apresenta uma sensibilidade de recepção que pode atingir o limite de até -148 dBm, dependendo dos parâmetros configurados. Como resultado direto da robustez da modulação LoRa, a taxa de erro manteve-se estritamente nula até os 200 metros de distância, registrando uma taxa ínfima de descarte de apenas 0,9% ao atingir o limite de 250 metros. Esses dados validam a arquitetura de comunicação escolhida, comprovando sua capacidade técnica de manter a telemetria do protótipo funcional nas maiores distâncias encontradas entre os boxes e a pista do autódromo ECPA. </p>

## Modelagem de Filtros:
<p align="justify"> A modelagem dos filtros digitais, FIR e IIR, para os sensores do Sistema Transmissor, compreendendo a temperatura da água do radiador (entrada e saída) e a pressão da linha de freio traseira, foi realizada no ambiente MATLAB. Como os referidos instrumentos ainda não haviam sido instalados, a análise espectral utilizou dados de telemetria pregressos, capturados pela ECU a uma taxa de amostragem de 18,81 Hz. Dessa forma, assumiu-se o comportamento térmico da água do motor como referência para o radiador, e a dinâmica da linha de freio dianteira para parametrizar o circuito traseiro. Através da Transformada Rápida de Fourier (FFT), constatou-se que a energia do sinal de temperatura concentra-se predominantemente abaixo de 0,3 Hz. Diante disso, estabeleceu-se uma frequência de passagem de 0,5 Hz e uma frequência de rejeição de 2 Hz, o que resultou na síntese de um filtro IIR de 5ª ordem e um FIR de 13ª ordem. De maneira análoga, a FFT do sinal de pressão de freio fundamentou a escolha de 1,5 Hz para a banda de passagem e 4 Hz para a banda de rejeição, gerando filtros IIR de 4ª ordem e FIR 6ª ordem. </p>

### Espectro de Frequência - Temperatura da Água:

![Desempenho da Comunicação a Distância.](Imagens/FFT_Temperatura_da_agua_do_motor.png)

### Espectro de Frequência - Pressão de Freio:

![Desempenho da Comunicação a Distância.](Imagens/FFT_Pressao_da_Linha_de_Freio.png)

<p align="justify">Testou-se computacionalmente a aplicação dos filtros FIR e IIR modelados no MATLAB. Verificou-se que os filtros IIR atingiram um desempenho de atenuação de ruído de alta frequência estatisticamente semelhante aos filtros FIR de maior ordem. Devido a essa similaridade de eficiência atrelada a uma considerável redução da complexidade algorítmica e custo computacional, a topologia IIR foi selecionada e implementada de forma definitiva no código receptor. </p>

### Simulação Filtros FIR e IIR - Temperatura da Água:

![Desempenho da Comunicação a Distância.](Imagens/Temperatura_da_Agua_Comparação_de_Filtros_10_Hz.png)

### Simulação Filtros FIR e IIR - Pressão de Freio:

![Desempenho da Comunicação a Distância.](Imagens/Pressao_de_Freio_Comparação_de_Filtros_10_Hz.png)

### Atraso de Grupo (Group Delay)
<p align="justify"> Para avaliar o impacto temporal do processamento digital nos sinais adquiridos, procedeu-se à análise do Atraso de Grupo (Group Delay) das topologias modeladas. Os filtros FIR apresentaram a característica inerente de fase linear, resultando em um retardo constante para todas as frequências: 300 ms para a pressão de freio (6ª ordem) e 650 ms para a temperatura da água (13ª ordem). Em contrapartida, os filtros IIR do tipo Butterworth evidenciaram uma resposta de fase não-linear, onde a defasagem atinge seu valor máximo próximo à frequência de corte. Contudo, ao analisar especificamente a banda de passagem nominal frequência de 0 Hz, onde se concentra a energia útil de ambos os fenômenos físicos, o filtro IIR de freio introduziu um atraso de aproximadamente 134 ms, enquanto o IIR de temperatura inseriu um retardo de cerca de 560 ms. Essa análise temporal ratifica a escolha pela implementação em IIR, visto que, além de demandar um menor custo de processamento devido à baixa ordem, os filtros proporcionam tempos de resposta compatíveis com a dinâmica exigida para a atualização da telemetria em tempo real, mitigando atrasos excessivos que comprometeriam a visualização na interface gráfica. </p>

### Atraso de Grupo - Temperatura da Água:

![Desempenho da Comunicação a Distância.](Imagens/Atraso_de_Grupo_Agua.png)

### Atraso de Grupo - Pressão de Freio:

![Desempenho da Comunicação a Distância.](Imagens/Atraso_de_Grupo_Freio.png)

## PCB:
<p align="justify">A etapa de desenvolvimento de hardware culminou na confecção física de uma PCB Sistema Transmissor, possuindo duas camadas e tamanho de 191,3 mm x 117,3 mm.</p>

<p align="center">
  <img src="https://github.com/tass10/tecracing_telemetry/blob/main/Imagens/PCB_Sistema_Transmissor.png" alt="PCB Sistema Transmissor" />
</p>

<p align="center">
  <img src="https://github.com/tass10/tecracing_telemetry/blob/main/Imagens/pcb3d.png" alt="PCB Sistema Transmissor" />
</p>

## Dashboard:
<p align="justify">No escopo de software, a Interface Homem-Máquina foi implementada com sucesso em Python, via PyQt5, demonstrando estabilidade na leitura assíncrona da porta serial.</p>

### Dashboard Teste Telemetria:
Dashboard usado no teste de distância:
<p align="center">
  <img src="https://github.com/tass10/tecracing_telemetry/blob/main/Imagens/Exemplo_Teste_Telemetria.png" alt="PCB Sistema Transmissor" />
</p>

Dashboard Demonstração:
<p align="center">
  <img src="https://github.com/tass10/tecracing_telemetry/blob/main/Imagens/dashboard_demo.png" alt="PCB Sistema Transmissor" />
</p>
