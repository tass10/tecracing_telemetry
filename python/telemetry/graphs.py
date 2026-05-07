import matplotlib.pyplot as plt

# ==========================================================
# CONFIGURAÇÃO GLOBAL DE FONTE (Padrão TCC/ABNT)
plt.rcParams['font.family'] = 'Arial'  # Ou 'Times New Roman'
plt.rcParams['font.size'] = 11         # Tamanho base para os números dos eixos
# ==========================================================

# 1. COLOQUE AQUI OS SEUS DADOS REAIS
distancias = [50, 100, 150, 200, 250]
erro_pct = [0.0, 0.0, 0.0, 0.0, 0.9] 
rssi_avg = [-46.4,  -33.7,  -38.5,  -38,    -56.7]
rssi_min = [-53,    -37,    -42,    -40,    -77]
rssi_max = [-42,    -32,    -36,    -36,    -51]

# 2. CRIAÇÃO DO GRÁFICO
fig, ax1 = plt.subplots(figsize=(10, 5))

# Configuração do Eixo Esquerdo (Sinal RSSI)
cor_rssi = '#1f77b4'
ax1.set_xlabel('Distância (metros)', fontsize=12, fontweight='bold')
ax1.set_ylabel('RSSI Médio e Variação (dBm)', color=cor_rssi, fontsize=12, fontweight='bold')
ax1.plot(distancias, rssi_avg, color=cor_rssi, marker='o', label='RSSI Médio', linewidth=2.5)
ax1.fill_between(distancias, rssi_min, rssi_max, color=cor_rssi, alpha=0.2, label='Variação RSSI (Min - Máx)')
ax1.tick_params(axis='y', labelcolor=cor_rssi)
ax1.grid(True, linestyle='--', alpha=0.6)
ax1.set_xticks(distancias)

# ==========================================================
# ADICIONANDO OS LIMITES DO EIXO Y ESQUERDO (RSSI)
ax1.set_ylim(-100, -20)
# ==========================================================

# Configuração do Eixo Direito (Taxa de Erro)
ax2 = ax1.twinx()
cor_erro = '#d62728' 
ax2.set_ylabel('Perda de Pacotes (%)', color=cor_erro, fontsize=12, fontweight='bold')
ax2.plot(distancias, erro_pct, color=cor_erro, marker='s', linestyle='--', label='Taxa de Erro (%)', linewidth=2.5)
ax2.tick_params(axis='y', labelcolor=cor_erro)

# ==========================================================
# ADICIONANDO OS LIMITES DO EIXO Y DIREITO (ERRO)
ax2.set_ylim(0, 5)
# ==========================================================

# Unificando as legendas no mesmo quadro
linhas1, labels1 = ax1.get_legend_handles_labels()
linhas2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(linhas1 + linhas2, labels1 + labels2, loc='upper center', bbox_to_anchor=(0.5, 1.15), ncol=3, fontsize=12)

# Título e ajustes finais
# plt.title('Desempenho da Comunicação à Distância', fontsize=14, fontweight='bold', pad=60)

# ==========================================================
# RÓTULOS DE DADOS PARA O SINAL RSSI (Azul)
for i in range(len(distancias)):
    # O "+ 2" empurra o texto um pouco para cima da linha para não amassar
    ax1.text(distancias[i], rssi_avg[i] + 4, f'{rssi_avg[i]} dBm', 
             color=cor_rssi, fontweight='normal', ha='center', va='bottom', fontsize=12)

# RÓTULOS DE DADOS PARA A TAXA DE ERRO (Vermelho)
for i in range(len(distancias)):
    # O "+ 0.3" empurra o texto um pouco para cima da linha vermelha
    ax2.text(distancias[i], erro_pct[i] + 0.3, f'{erro_pct[i]}%', 
             color=cor_erro, fontweight='normal', ha='center', va='bottom', fontsize=12)
# ==========================================================

fig.tight_layout()

# Salvar
plt.savefig('grafico_telemetria_tcc.png', dpi=300, bbox_inches='tight')
plt.show()