Na aba **Reajuste de preço** do contrato:

1. **Índice de reajuste**: por exemplo IPCA (com o *monetary_index_update_bacen*
   instalado, as taxas são buscadas no Banco Central).
2. **Intervalo**: meses entre dois reajustes, padrão 12.
3. **Defasagem**: meses entre o fim do período acumulado e o mês do
   reajuste, padrão 1 (reajuste em dezembro usa até novembro).
4. **Data-base**: data do último preço; o próximo reajuste é a data-base
   mais o intervalo.
5. **Variação negativa**: não reduzir (padrão) ou aplicar.
6. **Teto**: percentual máximo por reajuste; zero é sem teto.
7. **Modo**: atividade para aprovação (padrão) ou aplicação automática.
