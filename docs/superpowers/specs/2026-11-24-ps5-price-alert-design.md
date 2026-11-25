# Monitor de preço do PS5 para a Black Friday — Design

Data: 2026-11-24. Black Friday: 2026-11-27 (prazo de ~3 dias).

## Intenção e porquê
João quer comprar um PlayStation 5 na Black Friday sem pagar caro nem cair em "falso desconto". Precisa de uma aplicação web que mostre a variação de preço do console nos principais marketplaces confiáveis do Brasil e o avise, o mais rápido possível, quando o preço cair.

## Objetivos
- Acompanhar **dois modelos**, cada um com seu histórico: PS5 Slim com leitor de disco e PS5 Slim Digital (sem disco).
- Alerta no **Telegram** em dois níveis, valendo para qualquer um dos modelos:
  - **Alerta normal:** preço abaixo de R$ 4.000.
  - **Alerta máximo:** preço abaixo de R$ 3.600.
- **Latência mínima** entre a queda do preço na loja e a mensagem no Telegram (meta: 1 a 2 minutos).
- Mostrar a variação de preço (histórico por modelo e por loja) numa página web simples.
- Custo zero.

## Não objetivos
- Comprar automaticamente.
- Outros produtos além dos dois PS5 Slim (PS5 Pro e bundles ficam de fora).
- Contas de usuário, painel para outras pessoas, app mobile.

## Anti-objetivos (seria fracasso mesmo funcionando)
- Silêncio enganoso: se a fonte de dados falhar ou for bloqueada, o João não pode achar que "não caiu nada". O app avisa quando está cego.
- Alertar sobre anúncio errado (acessório, console usado, PS5 Pro, bundle com jogo contado como preço do console, vendedor desconhecido).
- Spam: repetir o mesmo alerta normal a cada checagem.

## Restrições
- Prazo de ~3 dias; precisa estar funcionando antes de sexta, 27/11.
- Hospedagem gratuita, na nuvem (não depende do computador do João).
- Repositório **público** no GitHub (minutos de Actions gratuitos). Token do Telegram e chat id ficam nos "segredos" do GitHub, nunca no código.
- Ler páginas pode ir contra termos de uso e pode ser bloqueado; a fonte de dados deve ser trocável.

## Abordagens consideradas
- **A. Zoom/Buscapé como base + API oficial do Mercado Livre (escolhida).** Um agregador cobre várias lojas e traz histórico pronto. Menos trabalho. Risco: atraso do agregador em relação à loja e quebra se o layout mudar.
- **B. Direto em cada loja** (API do ML, Keepa pago para a Amazon, leitura das páginas de Magalu, Kabum, Americanas). Mais exato e rápido, mas muito mais frágil e trabalhoso para 3 dias, e o histórico começa do zero.
- **C. Híbrido** (A mais fontes diretas nas lojas principais). Melhor latência, mais trabalho. Fica como evolução: o código deve permitir somar fontes diretas depois.

O João escolheu a A.

## Decisões do João
- Telegram, alerta abaixo de R$ 4.000; alerta máximo abaixo de R$ 3.600, para qualquer um dos modelos.
- Monitorar os dois modelos (com leitor e digital).
- Hospedar na nuvem, de graça ou o mais barato possível; usar **GitHub Actions**, mas **trocar o agendador** nativo por um com a menor latência possível.

## Desenho

### Execução e agendamento (decisão minha, a confirmar)
O agendador nativo do GitHub é no mínimo de 5 minutos e atrasa 5 a 30 minutos ou mais. Para reduzir a latência:
1. Um agendador externo gratuito (cron-job.org, sem código) chama a API do GitHub a cada **1 minuto** para disparar o workflow (`workflow_dispatch`), usando um token do GitHub de escopo mínimo guardado no cron-job.org.
2. Cada execução do workflow fica rodando por alguns minutos e **verifica os preços em laço (a cada 30 a 60 s)**, em vez de uma checagem só; execuções sobrepostas são evitadas (`concurrency`). Assim, mesmo se o disparo atrasar, a verificação continua.
3. O agendador nativo do GitHub fica também ativo como reserva.
Mais frequente que 1 minuto não é desejável: aumenta muito o risco de bloqueio pela fonte.

### Fontes de dados
- Principal: páginas de produto do Zoom (com o Buscapé como fonte reserva) para cada modelo, trazendo preço por loja.
- Mercado Livre: API oficial de busca/preço (atenção: os campos de preço do `/items` estão migrando para endpoints próprios; confirmar o formato atual).
- Cada fonte fica atrás de uma interface comum, para trocar ou somar fontes sem mexer no resto.
- **Lojas aceitas (lista permitida):** lojas grandes e confiáveis (por exemplo Amazon, Mercado Livre com loja oficial/vendedor reputado, Magazine Luiza, Kabum, Americanas, Casas Bahia, Fast Shop, Carrefour). A lista final é decisão do construtor, em arquivo de configuração, e deve ser fácil de editar.
- **Casamento de produto:** só entram anúncios do modelo exato (Slim com leitor ou Slim Digital), novos, sem bundle atribuído ao preço do console; ambíguos são ignorados e registrados.

### Histórico e página web
- Cada checagem grava preço por modelo, loja e horário num arquivo de dados no repositório (ex.: JSON/CSV), com histórico recente trazido da fonte quando disponível.
- Uma página estática (GitHub Pages) mostra, por modelo, o gráfico de variação, o menor preço atual por loja e o menor preço do período. Decisão minha: o João pediu uma "aplicação web com variação de preços", e uma página estática cobre isso sem custo.

### Regras de alerta
- Alerta normal: o menor preço aceito do modelo fica abaixo de R$ 4.000 e é **diferente do último alertado** (novo mínimo, nova loja mais barata ou volta a ficar abaixo depois de ter subido). Não repete o mesmo preço.
- Alerta máximo: abaixo de R$ 3.600. Mensagem destacada ("ALERTA MÁXIMO"), reenviada **a cada minuto, até 5 vezes** (ou até o preço sair da faixa), com link direto da oferta. O Telegram não toca como ligação; a repetição serve para chamar a atenção. (Decisão minha.)
- Toda mensagem traz: modelo, loja, preço, menor preço dos últimos 30 dias e variação em relação a ele, link direto. Isso ajuda a perceber falso desconto.
- **Alerta de saúde:** se uma fonte falhar ou for bloqueada por mais de ~10 minutos, ou o preço ficar sem atualizar, manda mensagem avisando; avisa de novo quando voltar.

### Segurança
- Token do bot e chat id nos segredos do GitHub. Token de disparo do cron-job.org com escopo mínimo (só acionar este workflow). Nada disso aparece no repositório público.

## Riscos
- Bloqueio de IP de nuvem pelo Zoom/Buscapé (pode afetar o GitHub Actions). Mitigação: fonte reserva, alerta de saúde, interface de fontes trocável.
- Atraso do agregador em relação à loja; o app não pode prometer o preço "ao vivo".
- Mudança de layout quebra a leitura; testes com páginas salvas.

## O que fica para o construtor
Linguagem e bibliotecas; formato do arquivo de dados; lista final de lojas; formato exato das mensagens; como casar títulos de anúncios com os dois modelos; organização dos testes (usando páginas salvas das fontes).

## Respostas do João à revisão
- **Preço que vale para os limites:** preço **à vista/Pix**. A mensagem mostra também o parcelado. Frete não entra no cálculo; a mensagem avisa quando o frete não está incluído. Quando uma loja só mostra preço parcelado ou único, vale o preço único mostrado.
- **Se o Zoom/Buscapé bloquear o GitHub Actions:** começar pelo **escopo menor e grátis**, isto é, API oficial do Mercado Livre mais as lojas que for possível ler direto. Só considerar pago (Keepa, serviço de leitura de páginas) se faltar loja importante, e **só com nova autorização do João**. Custo continua zero por padrão.

## Cupons de desconto (adicionado depois da aprovação)
- **Decisão do João:** só **avisar** que existe cupom ativo; o cupom **não muda** o preço usado nos limites de R$ 4.000 e R$ 3.600.
- Cupons vêm de páginas de agregadores de cupons (por exemplo Promobit, Pelando, Cuponomia), sem API pública conhecida; leitura de página, com o mesmo risco de bloqueio. Falha ao ler cupons **nunca** atrapalha os alertas de preço.
- Decisão minha: o cupom ativo da loja aparece como observação na mensagem de alerta daquela loja ("Cupom ativo: CODIGO — descrição; confira as condições") e na página web. Não há mensagem só de cupom.

## Calls minhas depois da revisão do construtor (para o João conferir)
- **Primeiro passo é um teste rápido** (dia 1): ler as páginas do Zoom/Buscapé a partir do GitHub Actions. O resultado define se seguimos na abordagem A. Os endereços das páginas dos dois modelos eu mesmo procuro.
- **Execuções:** cada execução dura cerca de 5 minutos, sem cancelar a anterior (`cancel-in-progress: false`), e a próxima entra na fila, evitando buracos. O disparo de 1 minuto cobre sobreposições.
- **Estado dos alertas** (último preço alertado, contagem do alerta máximo, saúde das fontes) fica fora do histórico principal, numa branch separada de dados; grava no repositório **só quando algo muda**, não a cada checagem, para evitar milhares de commits e conflitos. A contagem das 5 repetições é guardada nesse estado, então sobrevive ao fim de uma execução.
- **Histórico:** grava só mudanças de preço (mais um ponto de controle a cada hora). O gráfico usa também o histórico recente que o agregador mostrar; se não for possível ler, as mensagens dizem "sem histórico ainda" nos primeiros dias.
- **Alerta de saúde:** avisa se uma fonte falhar por 10 minutos, mesmo que as outras funcionem. "Preço sem mudar" não é falha, porque agregador atrasa.
- **Mercado Livre:** pode exigir registrar um aplicativo e usar um token; isso entra no "o que o João precisa fazer" e vira outro segredo. Se atrasar, o Mercado Livre sai do primeiro dia e entra depois.
- Mensagens em português; casamento de modelo por palavras do título e regras de exclusão (usado, Pro, bundle).

## O que o João precisa fazer
Criar o bot no Telegram (@BotFather) e passar o token e o chat id apenas como segredo do GitHub (nunca no chat); criar o repositório público e o token de disparo; criar a conta no cron-job.org.
