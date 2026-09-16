# Orbe — versão local

Abra `Abrir Orbe.command` e use sempre http://127.0.0.1:4173/ no mesmo navegador. O servidor serve somente a pasta `dist` e fica limitado ao próprio computador. Requer Python 3; não requer instalação de bibliotecas.

## Uso

Crie seu usuário com senha ou escolha **Experimentar com dados de exemplo**. Os exemplos são fictícios e temporários. Crie contas com saldo inicial antes de registrar as movimentações. Personalizar permite mudar categorias, campos extras, cor, densidade e blocos do painel.

Os dados reais não ficam nos arquivos do site. Cada usuário tem um registro independente no IndexedDB, criptografado com AES-GCM e uma chave derivada da senha via PBKDF2-SHA256 (310.000 iterações e salt aleatório). A chave fica na memória durante o uso. Se você marcar “Manter conectado neste navegador”, a sessão salva permite recarregar sem digitar a senha novamente. O nome do usuário é visível na seleção de entrada. Personalizar inclui a troca da senha atual.

Exporte um backup `.orbe` periodicamente. Ele é criptografado com a senha do cofre. Limpar os dados do navegador ou trocar de navegador/endereço cria um espaço diferente. **Não há recuperação de senha**. Restauração substitui os registros do usuário atual mediante confirmação; na tela de entrada, restaura como outro usuário.

## Regras da primeira versão

- Valores armazenados em centavos; parcelas conservam o valor total.
- Receitas e despesas à vista seguem a data; parcelas seguem o mês da fatura.
- Transferências não alteram receita/despesa nem patrimônio.
- Patrimônio líquido = saldos das contas menos toda a dívida de compras já feitas, inclusive parcelas futuras.
- Pagar fatura reduz saldo e dívida; não gera outra despesa. Pagamento integral, sem juros ou pagamento parcial nesta versão.
- Compras no fechamento entram no próximo ciclo. A primeira fatura pode ser ajustada. Edição de fechamento não remaneja compras existentes.
- Gastos fixos são previsões mensais; confirmar gera uma despesa. Excluir essa despesa torna a previsão pendente. Excluir a previsão preserva lançamentos passados.
- Objetivos não movimentam contas automaticamente. Valores planejados são acompanhamento, não reservas contabilizadas.
- Contas com vínculos não podem ser excluídas. Compras com faturas pagas exigem desfazer os pagamentos antes da edição/exclusão.
- O histórico e os saldos do Notion **não foram migrados**; a interface preserva seus módulos, não incorpora seus registros pessoais ao código.

## Limites e evolução

Esta versão é um site local com cofres de navegador, não um serviço publicado. Não contém backend multiusuário, sincronização, recuperação de senha, integrações bancárias ou controle de acesso de servidor. Para lançamento público: backend autenticado com autorização por usuário, banco persistente, HTTPS, recuperação de acesso e revisão de segurança. Os módulos `core.mjs` e `vault.mjs` separam regras e armazenamento para essa evolução.

## Validação

`node --test test-core.mjs test-vault.mjs` verifica dinheiro em centavos, transferências, parcelas, pagamentos sem duplicidade, datas, validação de backups, criptografia, isolamento dos registros e rejeição de gravações desatualizadas. O teste do cofre usa Web Crypto real e um adaptador de armazenamento em memória. Os fluxos visuais são verificados separadamente no navegador.
