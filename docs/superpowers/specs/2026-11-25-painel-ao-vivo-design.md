# Painel ao vivo do PS5 — desenho

Data: 2026-11-25. Prazo: pronto e testado antes do congelamento (quinta 26/11 à noite).

## Por quê
Na Black Friday você vai estar no computador com a página aberta, além de esperar o Telegram. A página precisa mostrar as ofertas **de agora**, quase ao vivo, e deixar **clicar no link da promoção**. Hoje ela só mostra histórico, sem links, e pode ficar até ~10 min atrasada.

## Objetivos
- Visual novo: painel escuro (modelo "A" aprovado em `layout-v2.html`).
- Links clicáveis para cada oferta, abrindo em nova aba.
- Atualização quase ao vivo (~1 min após a checagem), sem recarregar a página.
- Ranking das ofertas de agora + ranking dos menores preços já vistos (top 10, com quando e quanto durou).

## Fora do escopo
- Mudar regras de alerta, limites, fontes ou o Telegram.
- Login, contas, notificações no navegador.

## Anti-objetivos
- A página mostrar preço velho como se fosse atual sem avisar (por isso o aviso de "vigia parado?").
- Qualquer mudança que possa derrubar o vigia na sexta.

## Abordagens consideradas
- **A. Página lê do GitHub pela API a cada ~30 s (escolhida).** Consultas sem mudança (resposta 304 com ETag) não contam no limite de 60/h do GitHub sem login. Atraso ~1 min. Se o limite estourar, cai para a cópia do Pages e avisa na barra.
- **B. Página lê só pelo Pages.** Mais simples, mas o Pages guarda cópia por até ~10 min e leva ~1 min para publicar: atraso de 1–10 min. Descartada, porque o motivo da página é clicar a tempo.

## Desenho

### Dados (vigia)
- **`offers.json`** novo na branch `data`: `checked_at` (última checagem) e a lista das ofertas atuais plausíveis (≥ piso de suspeita) de lojas aceitas: modelo, loja, preço, link, combo, título, cupom (`promo`), fonte e `since` (desde quando aquela loja está nesse preço, tirado do histórico).
- Gravado em toda checagem, mas só vira commit quando as ofertas mudam **ou** quando `checked_at` gravado tem mais de 5 min (batimento). Evita commit a cada 45 s.
- **Histórico com link:** cada ponto passa de `[hora, preço]` para `[hora, preço, link]`. Leitores atuais usam só as duas primeiras posições, então é compatível. Pontos antigos ficam sem link.

### Página (`site/index.html`, `site/app.js`)
1. Barra "Ao vivo": há quanto tempo foi a última checagem; vermelha com "vigia parado?" se passar de 10 min; mostra se está usando a cópia do Pages (modo lento).
2. Destaques: menor preço de agora por modelo, quanto falta para R$ 4.000 (ou "abaixo do alerta" / "ALERTA MÁXIMO"), botão "Abrir oferta →". Borda amarela perto do alerta, vermelha abaixo.
3. Ranking das ofertas de agora: tabela numerada do menor para o maior, com marcas de combo e cupom, "no ar desde", link. Filtros: Todos / Digital / Com leitor / Sem combos.
4. Menores preços já vistos: top 10 de "episódios" de preço (por modelo + loja, pontos seguidos com o mesmo preço juntados), com data/hora, quanto durou ou "ainda no ar", link (cinza se já saiu do ar; sem botão se não houver link).
5. Gráfico de histórico por modelo (Chart.js, como hoje, com linhas de R$ 4.000 e R$ 3.600), em tema escuro.
- Busca: `offers.json` pela API do GitHub (`/repos/jomasii/pswatch/contents/offers.json?ref=data`, formato raw, com ETag) a cada 30 s; `history.json` igual, a cada 5 min. Se a API responder 403/429 ou falhar, usa os arquivos do próprio Pages.
- Todo texto vindo dos dados entra na página como texto (nunca como HTML). Links só são clicáveis se começarem com `https://`.

## Ajustes após a revisão final (25/11)
- Sem login, o GitHub **conta** as respostas 304 no limite de 60/h (conferido no navegador). Por isso: ofertas pela API a cada **75 s**; histórico pelo `raw.githubusercontent.com` (sem gastar API); com ≤ 3 consultas restantes a página espera o reset e usa `raw.githubusercontent.com` (atraso até ~5 min) e, por último, a cópia do Pages.
- Batimento passou para **10 min** e o aviso "vigia parado?" para **15 min** (limite de ~10 publicações/h do Pages).
- Mudança só de link/título/cupom (mesmo preço) não grava na hora; vai no próximo commit ou batimento.
- Erro ao montar o retrato nunca impede salvar o estado do alerta.
- Ofertas iguais vindas do Zoom e do Buscapé viram uma linha só (Zoom primeiro); os links levam à página do Zoom/Buscapé com a oferta da loja destacada.

## Decisões do construtor (minhas)
- Batimento de 5 min e alerta de "parado" em 10 min.
- Só lojas aceitas aparecem nos rankings (as mesmas que valem para o alerta).
- O "durou" é calculado na página a partir do histórico; precisão limitada aos pontos gravados (mudança de preço ou a cada hora).
- Testes automáticos para o lado do vigia (`offers.json`, link no histórico, batimento). A página é conferida no navegador com dados reais antes de publicar.
