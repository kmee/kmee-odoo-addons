1. Em *Faturamento / Configuração / Templates Contábeis*, crie um template e
   adicione itens: cada item liga um **campo fiscal** (ICMS, IPI, ST, retenções,
   frete, valor da operação etc.) a uma conta de **débito** e uma de **crédito**.
2. Itens sem conta explícita usam a cascata de resolução: conta do produto ou
   da categoria (para campos de item), conta do parceiro (para campos de
   documento) e, por fim, a conta padrão do diário.
3. Para reaproveitar configurações, use a hierarquia: um template pai com os
   impostos comuns da empresa e filhos por operação, sobrescrevendo apenas o
   que muda. O item do filho tem precedência sobre o do pai no mesmo campo.
4. Vincule o template à **operação fiscal** (aba Contabilidade da operação).
   O vínculo é por empresa.
5. Em compras, o item pode exigir **direito a crédito**: com a opção marcada, a
   linha só é gerada quando o CST da linha fiscal dá direito ao crédito.
