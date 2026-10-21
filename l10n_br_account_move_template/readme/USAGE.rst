Ao **postar** uma fatura cuja operação fiscal tem template vinculado, as linhas
de partida dobrada são geradas automaticamente, uma dupla débito/crédito por
campo fiscal com valor, identificadas pelo marcador *Template Double Entry*.

As linhas geradas não aparecem entre as linhas da fatura (são lançamento
contábil puro) e são removidas ao **voltar a fatura para rascunho**, o que
torna o ciclo postar/corrigir/repostar seguro.

Campos com valor zero não geram linhas.
