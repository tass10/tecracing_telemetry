# TR08 Telemetry System
Telemetry and DAQ System for FSAE BR Team TEC Racing

# Resultados da Pesquisa:

## Desempenho da Comunicação a Distância:
<p align="justify"> Para avaliar a performance do sistema, foi construído um protótipo com os componentes principais e foi realizado um teste de comunicação, consistindo no envio de 1.000 mensagens para o Sistema Receptor em distâncias predefinidas, variando de 50 m a 250 m, com incrementos regulares de 50 metros. O Sistema Receptor identifica quantas mensagens foram recebidas e informa a potência do sinal recebido para cada mensagem e porcentagem de erro total.</p>


![Desempenho da Comunicação a Distância.](Imagens/grafico_telemetria_tcc.png)

A análise da métrica do Indicador de Potência do Sinal Recebido, RSSI, demonstra que o sinal médio atenuou de -46,4 dBm, a 50 metros, para -56,7 dBm, a 250 metros. Esses valores encontram-se em uma zona extremamente segura de recepção. De acordo com a literatura técnica e as especificações da fabricante do transceiver, a modulação LoRa apresenta uma sensibilidade de recepção que pode atingir o limite de até -148 dBm, dependendo dos parâmetros configurados. Como resultado direto da robustez da modulação LoRa, a taxa de erro manteve-se estritamente nula até os 200 metros de distância, registrando uma taxa ínfima de descarte de apenas 0,9% ao atingir o limite de 250 metros. Esses dados validam a arquitetura de comunicação escolhida, comprovando sua capacidade técnica de manter a telemetria do protótipo funcional nas maiores distâncias encontradas entre os boxes e a pista do autódromo ECPA.

## Modelagem de Filtros:
Foram modelados filtros FIR e IIR através do software MATLAB para os sensores conectados ao Sistema Transmissor, sendo eles: temperatura da água do radiador e pressão da linha de freio. Para o primeiro sensor, após análise espectral do sinal bruto, através da Transformada Rápida de Fourier (FFT), foi identificado que a potência do sinal está concentrada em frequência abaixo de 0,3 Hz, logo, foi definida uma frequência de passagem de 0,5 Hz e frequência de rejeição de 2 Hz. A modelagem resultou num filtro IIR de 5ª ordem e num filtro FIR de 14ª ordem. Na modelagem dos filtros para a pressão da linha de freio, após análise via FFT, foi escolhida uma frequência de passagem de 1,5 Hz e frequência de rejeição de 4 Hz. Ambos os filtros obtidos, IIR e FIR, resultaram em 3ª ordem.



Testou-se computacionalmente a aplicação dos filtros FIR e IIR modelados no MATLAB. Verificou-se que os filtros IIR atingiram um desempenho de atenuação de ruído de alta frequência estatisticamente semelhante aos filtros FIR de maior ordem. Devido a essa similaridade de eficiência atrelada a uma considerável redução da complexidade algorítmica e custo computacional, a topologia IIR foi selecionada e implementada de forma definitiva no código receptor.

## PCB:



## Dashboard:
